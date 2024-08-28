// Constants and Configuration
const ICONS = {
  BASE_URL: "/static/bootstrap/icons",
  REPEAT_ON: "repeat_on.svg",
  REPEAT_OFF: "repeat_off.svg",
  START_SOUND: "play-fill.svg",
  STOP_SOUND: "stop-fill.svg",
  VOLUME_UP: "volume-up.svg",
  VOLUME_MUTE: "volume-mute.svg",
};

const ELEMENTS = {
  DARK_MODE_TOGGLE: document.getElementById("darkModeToggle"),
  DESCRIPTION: document.getElementById("desc"),
  VOLUME_SLIDER: document.getElementById("volume"),
  VOLUME_VALUE: document.getElementById("volume-value"),
  PLAY_BUTTON: document.getElementById("play-button"),
  REPEAT_BUTTON: document.getElementById("repeat-button"),
  PLAY_ICON: document.getElementById("play-icon"),
  LOOP_ICON: document.getElementById("repeat-icon"),
  VOLUME_ICON: document.getElementById("volume-icon"),
  SOUND_PROGRESS: document.getElementById("sound-progress"),
  MAX_SOUND_LENGTH: document.getElementById("sound-max-length"),
  CURRENT_SOUND_PROGRESS: document.getElementById("sound-current-progress"),
  TOAST: document.getElementById("toast"),
  SOUND_SELECT: document.getElementById("sound"),
  LANGUAGE_SELECT: document.getElementById("language"),
  CATEGORY_SELECT: document.getElementById("category"),
};

// Variables
let iconsCache = {};
let isPlaying = false;
let loopEnabled = false;
let soundsData = [];
let soundInterval = null;

// Helper Functions
async function fetchAndCacheIcon(key) {
  if (!iconsCache[key]) {
    try {
      const response = await fetch(`${ICONS.BASE_URL}/${ICONS[key]}`);
      if (!response.ok) throw new Error("Network response was not ok");
      iconsCache[key] = await response.text();
    } catch (error) {
      console.error("Icon fetch failed:", error);
    }
  }
  return iconsCache[key];
}

function showToast(message) {
  ELEMENTS.TOAST.textContent = message;
  ELEMENTS.TOAST.className = "toast show";
  setTimeout(() => ELEMENTS.TOAST.className = ELEMENTS.TOAST.className.replace("show", ""), 3000);
}

function setData() {
  const formData = new FormData(document.getElementById("play-form"));
  const data = new URLSearchParams();
  formData.forEach((value, key) => data.append(key, value));
  data.append("loop", loopEnabled ? "on" : "off");
  return data;
}

async function initializeIcons() {
  // Filter out the BASE_URL key before fetching and caching the icons
  await Promise.all(
    Object.keys(ICONS)
      .filter(key => key !== "BASE_URL")
      .map(fetchAndCacheIcon)
  );

  setIcon(ELEMENTS.LOOP_ICON, loopEnabled ? "REPEAT_ON" : "REPEAT_OFF");
  setIcon(ELEMENTS.PLAY_ICON, isPlaying ? "STOP_SOUND" : "START_SOUND");
  setIcon(ELEMENTS.VOLUME_ICON, ELEMENTS.VOLUME_SLIDER.value > 0 ? "VOLUME_UP" : "VOLUME_MUTE");
}

function setIcon(element, iconKey) {
  element.innerHTML = iconsCache[iconKey];
}

// Update Functions
async function updateSounds() {
  const language = ELEMENTS.LANGUAGE_SELECT.value;
  const category = ELEMENTS.CATEGORY_SELECT.value;
  try {
    const response = await fetch(`/sounds?language=${language}&category=${category}`);
    soundsData = await response.json();
    populateSoundOptions(soundsData);
  } catch (error) {
    console.error("Error fetching sounds:", error);
  }
}

function populateSoundOptions(sounds) {
  ELEMENTS.SOUND_SELECT.innerHTML = sounds.map(sound => 
    `<option value="${sound.filename}">${sound.title}</option>`).join("");
  setDescriptionAndLength();
}

function setDescriptionAndLength() {
  const selectedSound = soundsData.find(sound => sound.filename === ELEMENTS.SOUND_SELECT.value);
  if (selectedSound) {
    ELEMENTS.DESCRIPTION.innerHTML = selectedSound.description;
    const formattedLength = selectedSound.length.toFixed(2);
    ELEMENTS.SOUND_PROGRESS.max = formattedLength;
    ELEMENTS.SOUND_PROGRESS.value = 0;
    ELEMENTS.MAX_SOUND_LENGTH.textContent = formattedLength;
    ELEMENTS.CURRENT_SOUND_PROGRESS.textContent = "0.00";
  } else {
    resetSoundProgress();
  }
}

function resetSoundProgress() {
  ELEMENTS.SOUND_PROGRESS.max = 0;
  ELEMENTS.MAX_SOUND_LENGTH.textContent = "0.00";
  ELEMENTS.CURRENT_SOUND_PROGRESS.textContent = "0.00";
}

function updateSoundProgress() {
  const max = parseInt(ELEMENTS.SOUND_PROGRESS.max);
  ELEMENTS.SOUND_PROGRESS.value = 0;
  soundInterval = setInterval(() => {
    if (ELEMENTS.SOUND_PROGRESS.value < max) {
      const newVal = parseFloat(ELEMENTS.SOUND_PROGRESS.value) + 1;
      ELEMENTS.SOUND_PROGRESS.value = newVal
      ELEMENTS.CURRENT_SOUND_PROGRESS.textContent = newVal.toFixed(2);
    } else {
      handleEndOfSound();
    }
  }, 1000);
}

function handleEndOfSound() {
  if (!isPlaying) {
    ELEMENTS.SOUND_PROGRESS.value = ELEMENTS.SOUND_PROGRESS.max;
    ELEMENTS.CURRENT_SOUND_PROGRESS.textContent = ELEMENTS.SOUND_PROGRESS.max;
    clearInterval(soundInterval);
  } else {
    resetSoundProgress();
  }
}

// Event Handlers
function handleDarkModeToggle() {
  document.body.classList.toggle("dark-mode", ELEMENTS.DARK_MODE_TOGGLE.checked);
  localStorage.setItem("darkMode", ELEMENTS.DARK_MODE_TOGGLE.checked ? "enabled" : "disabled");
}

function handleSelectionChange() {
  updateSounds().then(setDescriptionAndLength);
}

function handleSoundChange() {
  setDescriptionAndLength();
}

function handleVolumeChange() {
  updateVolumeText();
  updateVolume(ELEMENTS.VOLUME_SLIDER.value);
}

function updateVolumeText() {
  const volumePercentage = parseInt(ELEMENTS.VOLUME_SLIDER.value * 100);
  ELEMENTS.VOLUME_VALUE.textContent = `${volumePercentage}%`;
}

async function updateVolume(volume) {
  setIcon(ELEMENTS.VOLUME_ICON, volume > 0 ? "VOLUME_UP" : "VOLUME_MUTE");
  try {
    const response = await fetch("/volume", {
      method: "POST",
      body: new URLSearchParams({ volume }),
    });
    showToast(await response.text());
  } catch (error) {
    showToast("Error setting volume: " + error);
  }
}

function togglePlaying() {
  isPlaying = !isPlaying;
  setIcon(ELEMENTS.PLAY_ICON, isPlaying ? "STOP_SOUND" : "START_SOUND");
}

function toggleLoop() {
  loopEnabled = !loopEnabled;
  setIcon(ELEMENTS.LOOP_ICON, loopEnabled ? "REPEAT_ON" : "REPEAT_OFF");
}

async function handlePlaying() {
  togglePlaying();
  if (isPlaying) {
    await handlePlaySound(setData());
  } else {
    await handleStopSound();
  }
}

async function handlePlaySound(data) {
  try {
    updateSoundProgress();
    const response = await fetch("/play", { method: "POST", body: data });
    showToast(await response.text());
  } catch (error) {
    showToast("Error playing sound: " + error);
  } finally {
    togglePlaying();
  }
}

async function handleStopSound() {
  try {
    const response = await fetch("/stop", { method: "POST" });
    showToast(await response.text());
  } catch (error) {
    showToast("Error stopping sound: " + error);
  } finally {
    clearInterval(soundInterval);
    togglePlaying();
  }
}

// Initialization Functions
function initializeDarkMode() {
  const darkMode = localStorage.getItem("darkMode") === "enabled";
  document.body.classList.toggle("dark-mode", darkMode);
  ELEMENTS.DARK_MODE_TOGGLE.checked = darkMode;
}

async function initializeApp() {
  await updateSounds();
  await initializeIcons();
  initializeDarkMode();
  setDescriptionAndLength();
}

// Event Listeners
ELEMENTS.DARK_MODE_TOGGLE.addEventListener("change", handleDarkModeToggle);
ELEMENTS.LANGUAGE_SELECT.addEventListener("change", handleSelectionChange);
ELEMENTS.CATEGORY_SELECT.addEventListener("change", handleSelectionChange);
ELEMENTS.SOUND_SELECT.addEventListener("change", handleSoundChange);
ELEMENTS.VOLUME_SLIDER.addEventListener("input", updateVolumeText);
ELEMENTS.VOLUME_SLIDER.addEventListener("change", handleVolumeChange);
ELEMENTS.PLAY_BUTTON.addEventListener("click", handlePlaying);
ELEMENTS.REPEAT_BUTTON.addEventListener("click", toggleLoop);

// Initialize the application
initializeApp();
