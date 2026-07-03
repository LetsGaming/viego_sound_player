/* Viego Soundboard — client
 *
 * One tap on a tile plays that sound on the server. Tapping the playing
 * tile again stops it. GET /api/status is polled so several devices (or a
 * reloaded page) always show the true server state.
 */
"use strict";

const $ = (id) => document.getElementById(id);

const els = {
  langSwitch: $("lang-switch"),
  chips: $("category-chips"),
  board: $("board"),
  boardEmpty: $("board-empty"),
  search: $("search"),
  dock: $("dock"),
  dockTitle: $("dock-title"),
  dockTime: $("dock-time"),
  progressFill: $("progress-fill"),
  loopBtn: $("loop-btn"),
  stopBtn: $("stop-btn"),
  muteBtn: $("mute-btn"),
  volume: $("volume"),
  volValue: $("vol-value"),
  volIcon: $("vol-icon"),
  toast: $("toast"),
};

const FAVORITES_KEY = "viego.favorites";
const RECENT_KEY = "viego.recent";
const LANG_KEY = "viego.language";
const RECENT_LIMIT = 12;

const state = {
  library: { languages: [], categories: [], sounds: [] },
  language: localStorage.getItem(LANG_KEY) || "en",
  category: "favorites",
  search: "",
  favorites: new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]")),
  recent: JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"),
  playingKey: null,
  loop: false,
  volumeBeforeMute: 1,
};

/* ---------- helpers ---------- */

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function post(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

let toastTimer = null;
function toast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove("show"), 2500);
}

function fmtTime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function persistFavorites() {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...state.favorites]));
}

function rememberRecent(key) {
  state.recent = [key, ...state.recent.filter((k) => k !== key)].slice(0, RECENT_LIMIT);
  localStorage.setItem(RECENT_KEY, JSON.stringify(state.recent));
}

/* ---------- rendering ---------- */

function renderLanguageSwitch() {
  els.langSwitch.innerHTML = "";
  for (const lang of state.library.languages) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = lang.toUpperCase();
    btn.setAttribute("aria-pressed", String(lang === state.language));
    btn.addEventListener("click", () => {
      state.language = lang;
      localStorage.setItem(LANG_KEY, lang);
      renderLanguageSwitch();
      renderBoard();
    });
    els.langSwitch.appendChild(btn);
  }
}

function renderChips() {
  const chips = [
    { id: "favorites", label: "★ Favorites" },
    { id: "recent", label: "Recent" },
    { id: "all", label: "All" },
    ...state.library.categories.map((c) => ({ id: c.id, label: c.label })),
  ];
  els.chips.innerHTML = "";
  for (const chip of chips) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = chip.label;
    btn.setAttribute("aria-pressed", String(chip.id === state.category));
    btn.addEventListener("click", () => {
      state.category = chip.id;
      renderChips();
      renderBoard();
    });
    els.chips.appendChild(btn);
  }
}

function visibleSounds() {
  const q = state.search.trim().toLowerCase();
  const byLang = (s) => s.language === "-" || s.language === state.language;
  let sounds = state.library.sounds.filter(byLang);

  if (state.category === "favorites") {
    sounds = sounds.filter((s) => state.favorites.has(s.key));
  } else if (state.category === "recent") {
    const order = new Map(state.recent.map((k, i) => [k, i]));
    sounds = sounds
      .filter((s) => order.has(s.key))
      .sort((a, b) => order.get(a.key) - order.get(b.key));
  } else if (state.category !== "all") {
    sounds = sounds.filter((s) => s.category === state.category);
  }

  if (q) {
    sounds = sounds.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.filename.toLowerCase().includes(q)
    );
  }
  return sounds;
}

function categoryLabel(id) {
  const c = state.library.categories.find((c) => c.id === id);
  return c ? c.label : id;
}

function renderBoard() {
  const sounds = visibleSounds();
  els.board.querySelectorAll(".tile").forEach((t) => t.remove());

  if (sounds.length === 0) {
    els.boardEmpty.hidden = false;
    els.boardEmpty.textContent =
      state.category === "favorites" && !state.search
        ? "No favorites yet — tap the ☆ on any sound to pin it here."
        : "No sounds match.";
    return;
  }
  els.boardEmpty.hidden = true;

  const frag = document.createDocumentFragment();
  for (const sound of sounds) {
    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "tile";
    tile.dataset.key = sound.key;
    tile.classList.toggle("playing", sound.key === state.playingKey);
    if (sound.description) tile.title = sound.description;

    const title = document.createElement("span");
    title.className = "tile-title";
    title.textContent = sound.title;

    const meta = document.createElement("span");
    meta.className = "tile-meta";
    meta.innerHTML = `<span>${categoryLabel(sound.category)}</span><span>${fmtTime(sound.duration)}</span>`;

    const fav = document.createElement("button");
    fav.type = "button";
    fav.className = "tile-fav";
    fav.setAttribute("aria-label", "Favorite");
    fav.setAttribute("aria-pressed", String(state.favorites.has(sound.key)));
    fav.textContent = state.favorites.has(sound.key) ? "★" : "☆";
    fav.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFavorite(sound.key, fav);
    });

    tile.append(title, meta, fav);
    tile.addEventListener("click", () => onTileTap(sound));
    frag.appendChild(tile);
  }
  els.board.appendChild(frag);
}

function toggleFavorite(key, favBtn) {
  if (state.favorites.has(key)) state.favorites.delete(key);
  else state.favorites.add(key);
  persistFavorites();
  if (state.category === "favorites") {
    renderBoard();
  } else if (favBtn) {
    const on = state.favorites.has(key);
    favBtn.textContent = on ? "★" : "☆";
    favBtn.setAttribute("aria-pressed", String(on));
  }
}

/* ---------- playback ---------- */

async function onTileTap(sound) {
  try {
    if (sound.key === state.playingKey) {
      applyStatus(await post("/api/stop"));
    } else {
      rememberRecent(sound.key);
      applyStatus(await post("/api/play", { key: sound.key, loop: state.loop }));
      if (navigator.vibrate) navigator.vibrate(15);
    }
  } catch (err) {
    toast(err.message, true);
  }
}

function applyStatus(status) {
  const previousKey = state.playingKey;
  state.playingKey = status.playing ? status.sound.key : null;
  state.loop = status.loop;

  els.dock.classList.toggle("playing", status.playing);
  els.loopBtn.setAttribute("aria-pressed", String(state.loop));

  if (status.playing) {
    els.dockTitle.textContent = status.sound.title;
    const dur = status.sound.duration || 0;
    els.dockTime.textContent = `${fmtTime(status.position)} / ${fmtTime(dur)}${status.loop ? " · looping" : ""}`;
    els.progressFill.style.width = dur ? `${(status.position / dur) * 100}%` : "0%";
  } else {
    els.dockTitle.textContent = "Nothing playing";
    els.dockTime.textContent = "";
    els.progressFill.style.width = "0%";
  }

  if (previousKey !== state.playingKey) {
    for (const tile of els.board.querySelectorAll(".tile")) {
      tile.classList.toggle("playing", tile.dataset.key === state.playingKey);
    }
  }

  if (status.audio_available === false) {
    els.dockTitle.textContent = "No audio device on server";
  }
}

function setVolumeUI(volume) {
  const pct = Math.round(volume * 100);
  els.volume.value = pct;
  els.volValue.textContent = `${pct}%`;
  els.volIcon.classList.toggle("muted", pct === 0);
  els.muteBtn.classList.toggle("muted", pct === 0);
}

let volumeTimer = null;
function onVolumeInput() {
  const volume = els.volume.value / 100;
  setVolumeUI(volume);
  // debounce network calls while dragging
  clearTimeout(volumeTimer);
  volumeTimer = setTimeout(() => {
    post("/api/volume", { volume }).catch((err) => toast(err.message, true));
  }, 120);
}

function onMuteTap() {
  const current = els.volume.value / 100;
  let next;
  if (current > 0) {
    state.volumeBeforeMute = current;
    next = 0;
  } else {
    next = state.volumeBeforeMute || 1;
  }
  setVolumeUI(next);
  post("/api/volume", { volume: next }).catch((err) => toast(err.message, true));
}

async function onLoopTap() {
  try {
    applyStatus(await post("/api/loop", { loop: !state.loop }));
  } catch (err) {
    toast(err.message, true);
  }
}

async function onStopTap() {
  try {
    applyStatus(await post("/api/stop"));
  } catch (err) {
    toast(err.message, true);
  }
}

/* ---------- status polling ---------- */

let pollTimer = null;
function startPolling() {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      applyStatus(await api("/api/status"));
    } catch {
      /* transient network hiccup — keep last known state */
    }
  }, 1000);
}
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopPolling();
  else startPolling();
});

/* keep the screen awake while the panel is open, if supported */
let wakeLock = null;
async function requestWakeLock() {
  try {
    if ("wakeLock" in navigator) wakeLock = await navigator.wakeLock.request("screen");
  } catch {
    /* not critical */
  }
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) requestWakeLock();
});

/* ---------- init ---------- */

async function init() {
  els.search.addEventListener("input", () => {
    state.search = els.search.value;
    renderBoard();
  });
  els.volume.addEventListener("input", onVolumeInput);
  els.muteBtn.addEventListener("click", onMuteTap);
  els.loopBtn.addEventListener("click", onLoopTap);
  els.stopBtn.addEventListener("click", onStopTap);

  try {
    state.library = await api("/api/library");
  } catch (err) {
    toast("Could not load the sound library: " + err.message, true);
    return;
  }

  if (!state.library.languages.includes(state.language)) {
    state.language = state.library.languages[0] || "en";
  }
  if (state.favorites.size === 0) state.category = "all";

  renderLanguageSwitch();
  renderChips();
  renderBoard();

  try {
    const status = await api("/api/status");
    applyStatus(status);
    setVolumeUI(status.volume ?? 1);
  } catch {
    /* status will sync via polling */
  }

  startPolling();
  requestWakeLock();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

init();
