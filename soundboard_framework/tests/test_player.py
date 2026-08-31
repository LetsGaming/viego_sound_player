import numpy as np

from soundboard_framework.library import Sound
from soundboard_framework.player import Player, _Playback


def make_sound():
    return Sound(
        key="en/general/x",
        language="en",
        category="general",
        filename="x",
        title="X",
        description="",
        duration=1.0,
        path="/dev/null",
    )


def test_player_stores_fade_settings():
    player = Player(fade_in_ms=400, fade_out_ms=300)
    assert player._fade_in_ms == 400
    assert player._fade_out_ms == 300


def test_playback_computes_fade_frames_from_constructor_args():
    data = np.ones((8000, 1), dtype="float32")
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=500, fade_out_ms=250)

    assert pb.fade_in_frames == 4000  # 500ms at 8kHz
    assert pb.fade_out_frames == 2000  # 250ms at 8kHz


def test_render_loops_gaplessly_when_loop_enabled():
    data = np.arange(4, dtype="float32").reshape(4, 1)  # 4-frame "sound"
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=0, fade_out_ms=0)
    player = Player(fade_in_ms=0, fade_out_ms=0)
    player._pb = pb
    player._loop = True

    out = np.zeros((6, 1), dtype="float32")  # request more frames than the sound has
    player._render(pb, out, 6)

    # wraps within the same callback: [0,1,2,3] then wraps to [0,1]
    np.testing.assert_array_equal(out[:, 0], [0, 1, 2, 3, 0, 1])
    assert pb.pos == 2
    assert not pb.finished


def test_render_ends_when_loop_disabled_and_data_exhausted():
    data = np.arange(4, dtype="float32").reshape(4, 1)
    pb = _Playback(make_sound(), data, samplerate=8000, fade_in_ms=0, fade_out_ms=0)
    player = Player(fade_in_ms=0, fade_out_ms=0)
    player._pb = pb
    player._loop = False

    out = np.full((6, 1), -1, dtype="float32")

    try:
        player._render(pb, out, 6)
    except Exception as exc:
        # sounddevice.CallbackStop is raised when a stream ends; accept any
        # exception here since `sd` may be unavailable in the test env.
        assert type(exc).__name__ == "CallbackStop"

    np.testing.assert_array_equal(out[:4, 0], [0, 1, 2, 3])
    np.testing.assert_array_equal(out[4:, 0], [0, 0])
    assert pb.finished
