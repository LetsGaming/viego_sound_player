"""Thread-safe, non-blocking audio playback via sounddevice + soundfile.

Each sound is decoded to a float32 numpy array once, and a PortAudio stream
callback renders it. Because we fill the buffers ourselves:

- Looping is sample-accurate and truly gapless: when the read position hits
  the end and loop is on, it wraps *within the same callback buffer*.
- Toggling loop mid-play is just a flag the callback reads -- playback is
  never interrupted (loop-off finishes the current pass, then stops).
- The reported position is exact (frames rendered / sample rate), not a
  wall-clock estimate.
- Fade-in, fade-out and volume are per-sample envelopes.

Concurrency model: control methods take a lock; the realtime callback never
takes the lock -- it only reads plain attributes (atomic under the GIL).
Each stream's callback is bound to its own _Playback, so a superseded stream
can never render the sound that replaced it. Stream teardown always happens
outside the lock, because PortAudio may invoke finished_callback from within
abort()/close().
"""
from __future__ import annotations

import logging
import threading

import numpy as np
import soundfile as sf

from soundboard_framework.library import Sound

log = logging.getLogger(__name__)

try:
    import sounddevice as sd
    _SD_ERROR: str | None = None
except OSError as exc:  # PortAudio library missing on the host
    sd = None
    _SD_ERROR = str(exc)


class _Playback:
    """State of one playing sound, owned by its stream's render callback."""

    __slots__ = (
        "sound", "data", "samplerate", "stream", "pos", "frames_done",
        "fade_in_frames", "fade_out_frames", "fadeout_at", "finished",
    )

    def __init__(
        self,
        sound: Sound,
        data: np.ndarray,
        samplerate: int,
        fade_in_ms: int,
        fade_out_ms: int,
    ) -> None:
        self.sound = sound
        self.data = data                     # float32, shape (frames, channels)
        self.samplerate = samplerate
        self.stream = None
        self.pos = 0                         # read position within data
        self.frames_done = 0                 # total frames rendered (monotonic)
        self.fade_in_frames = int(fade_in_ms / 1000 * samplerate)
        self.fade_out_frames = int(fade_out_ms / 1000 * samplerate)
        self.fadeout_at: int | None = None   # frames_done at which fade-out began
        self.finished = False


class Player:
    def __init__(self, fade_in_ms: int, fade_out_ms: int) -> None:
        self._fade_in_ms = fade_in_ms
        self._fade_out_ms = fade_out_ms
        self._lock = threading.Lock()
        self._pb: _Playback | None = None
        self._loop: bool = False
        self._volume: float = 1.0
        self._available = False

    def init(self) -> None:
        """Check that an output device exists. Streams are opened per play so
        they can match each file's sample rate and channel count exactly."""
        if sd is None:
            log.error("PortAudio not available: %s", _SD_ERROR)
            return
        try:
            sd.check_output_settings()
            self._available = True
            device = sd.query_devices(kind="output")
            log.info("Audio output ready: %s", device["name"])
        except Exception as exc:
            self._available = False
            log.error("No usable audio output device: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    # -- controls -----------------------------------------------------------

    def play(self, sound: Sound, loop: bool) -> None:
        if not self._available:
            raise RuntimeError("No audio output device is available on the server.")
        data, samplerate = sf.read(sound.path, dtype="float32", always_2d=True)
        pb = _Playback(sound, data, samplerate, self._fade_in_ms, self._fade_out_ms)
        pb.stream = sd.OutputStream(
            samplerate=samplerate,
            channels=data.shape[1],
            dtype="float32",
            callback=lambda out, fr, t, s, _pb=pb: self._render(_pb, out, fr),
            finished_callback=lambda _pb=pb: self._on_finished(_pb),
        )

        with self._lock:
            old = self._pb
            self._pb = pb
            self._loop = loop
        self._teardown(old)  # outside the lock
        pb.stream.start()

    def stop(self) -> None:
        """Request a fade-out; the callback ends the stream at silence."""
        with self._lock:
            pb = self._pb
            if pb is not None and pb.fadeout_at is None:
                pb.fadeout_at = pb.frames_done

    def set_volume(self, volume: float) -> float:
        volume = max(0.0, min(1.0, volume))
        with self._lock:
            self._volume = volume
        return volume

    def set_loop(self, loop: bool) -> bool:
        """Flip the loop flag without interrupting playback. Loop-on repeats
        seamlessly after the current pass; loop-off finishes the current pass
        and then stops."""
        with self._lock:
            self._loop = loop
        return loop

    # -- status ---------------------------------------------------------------

    def status(self) -> dict:
        with self._lock:
            pb = self._pb
            playing = pb is not None and not pb.finished
            if not playing:
                return {
                    "playing": False,
                    "sound": None,
                    "position": 0.0,
                    "loop": False,
                    "volume": self._volume,
                    "audio_available": self._available,
                }
            return {
                "playing": True,
                "sound": pb.sound.to_dict(),
                "position": round(pb.pos / pb.samplerate, 2),
                "loop": self._loop,
                "volume": self._volume,
                "audio_available": self._available,
            }

    # -- realtime callback (never blocks, never takes the lock) ----------------

    def _render(self, pb: _Playback, outdata: np.ndarray, frames: int) -> None:
        if pb is not self._pb or pb.finished:
            # Superseded by a newer play(); go silent and end this stream.
            outdata.fill(0)
            raise sd.CallbackStop

        total = len(pb.data)
        filled = 0
        ended = False
        while filled < frames:
            if pb.pos >= total:
                if self._loop:
                    pb.pos = 0  # gapless wrap within this very buffer
                else:
                    ended = True
                    break
            n = min(frames - filled, total - pb.pos)
            outdata[filled:filled + n] = pb.data[pb.pos:pb.pos + n]
            pb.pos += n
            filled += n
        if filled < frames:
            outdata[filled:] = 0

        # per-sample gain envelope: fade-in * fade-out * volume
        idx = pb.frames_done + np.arange(frames, dtype=np.float32)
        gain = np.full(frames, self._volume, dtype=np.float32)
        if pb.fade_in_frames > 0:
            gain *= np.clip(idx / pb.fade_in_frames, 0.0, 1.0)
        faded_out = False
        if pb.fadeout_at is not None:
            if pb.fade_out_frames > 0:
                fade = 1.0 - (idx - pb.fadeout_at) / pb.fade_out_frames
                gain *= np.clip(fade, 0.0, 1.0)
                faded_out = pb.frames_done + frames >= pb.fadeout_at + pb.fade_out_frames
            else:
                gain[:] = 0.0
                faded_out = True
        if filled:
            outdata[:filled] *= gain[:filled, None]

        pb.frames_done += frames
        if ended or faded_out:
            pb.finished = True
            raise sd.CallbackStop

    # -- teardown ---------------------------------------------------------------

    def _on_finished(self, pb: _Playback) -> None:
        """PortAudio calls this after the stream stops. Clear state only if
        this playback is still the current one (it may have been replaced)."""
        pb.finished = True
        with self._lock:
            if self._pb is pb:
                self._pb = None
                self._loop = False
        self._close_stream(pb)

    def _teardown(self, pb: _Playback | None) -> None:
        if pb is None:
            return
        pb.finished = True
        self._close_stream(pb)

    @staticmethod
    def _close_stream(pb: _Playback) -> None:
        stream, pb.stream = pb.stream, None
        if stream is None:
            return
        try:
            stream.abort(ignore_errors=True)
            stream.close(ignore_errors=True)
        except Exception:
            pass
