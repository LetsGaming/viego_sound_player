// Constants and Variables
const DARK_MODE_TOGGLE = document.getElementById("darkModeToggle");
const DESCRIPTION = document.getElementById("desc");
const VOLUME_SLIDER = document.getElementById("volume");
const VOLUME_VALUE = document.getElementById("volume-value");
const PLAY_BUTTON = document.getElementById("play-button");
const REPEAT_BUTTON = document.getElementById("repeat-button");
const PLAY_ICON = document.getElementById("play-icon");
const LOOP_ICON = document.getElementById("repeat-icon");
const VOLUME_ICON = document.getElementById("volume-icon");
const SOUND_PROGRESS = document.getElementById("sound-progress");
const MAX_SOUND_LENGTH = document.getElementById("sound-max-length");
const CURRENT_SOUND_PROGRESS = document.getElementById(
  "sound-current-progress"
);

const BASE_ICON_URL = "/static/bootstrap/icons";
const REPEAT_ON_URL = `${BASE_ICON_URL}/repeat_on.svg`;
const REPEAT_OFF_URL = `${BASE_ICON_URL}/repeat_off.svg`;
const START_SOUND_URL = `${BASE_ICON_URL}/play-fill.svg`;
const STOP_SOUND_URL = `${BASE_ICON_URL}/stop-fill.svg`;
const VOLUME_UP_URL = `${BASE_ICON_URL}/volume-up.svg`;
const VOLUME_MUTE_URL = `${BASE_ICON_URL}/volume-mute.svg`;

let REPEAT_ON, REPEAT_OFF, START_SOUND, STOP_SOUND, VOLUME_UP, VOLUME_MUTE;
let isPlaying = false;
let loopEnabled = false;
let soundsData = [];
let currentSound = null;
let soundInterval = null;

// Helper Functions
async function fetchSVG(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Network response was not ok");
    return await response.text();
  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
  }
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show";
  setTimeout(
    () => (toast.className = toast.className.replace("show", "")),
    3000
  );
}

function setData() {
  const formData = new FormData(document.getElementById("play-form"));
  const data = new URLSearchParams();
  formData.forEach((value, key) => data.append(key, value));
  data.append("loop", loopEnabled ? "on" : "off");
  return data;
}

async function initializeIcons() {
  REPEAT_ON = await fetchSVG(REPEAT_ON_URL);
  REPEAT_OFF = await fetchSVG(REPEAT_OFF_URL);
  START_SOUND = await fetchSVG(START_SOUND_URL);
  STOP_SOUND = await fetchSVG(STOP_SOUND_URL);
  VOLUME_UP = await fetchSVG(VOLUME_UP_URL);
  VOLUME_MUTE = await fetchSVG(VOLUME_MUTE_URL);
  setLoopIcon();
  setPlayIcon();
  setVolumeIcon();
}

// Update Functions
async function updateSounds() {
  const language = document.getElementById("language").value;
  const category = document.getElementById("category").value;
  try {
    const response = await fetch(
      `/sounds?language=${language}&category=${category}`
    );
    const sounds = await response.json();
    soundsData = sounds;
    const soundSelect = document.getElementById("sound");
    soundSelect.innerHTML = sounds
      .map(
        (sound) => `<option value="${sound.filename}">${sound.title}</option>`
      )
      .join("");
  } catch (error) {
    console.error("Error fetching sounds:", error);
  }
}

function setSoundLength() {
  const selectedSound = soundsData.find(
    (sound) => sound.filename === document.getElementById("sound").value
  );
  if (selectedSound) {
    const formattedLength = selectedSound.length.toFixed(2);
    SOUND_PROGRESS.max = formattedLength;
    SOUND_PROGRESS.value = 0;
    MAX_SOUND_LENGTH.textContent = formattedLength;
    CURRENT_SOUND_PROGRESS.textContent = "0.00";
  } else {
    SOUND_PROGRESS.max = 0;
    MAX_SOUND_LENGTH.textContent = "0.00";
    CURRENT_SOUND_PROGRESS.textContent = "0.00";
  }
}

function updateSoundProgress() {
  const max = parseInt(SOUND_PROGRESS.max);
  SOUND_PROGRESS.value = 0;
  soundInterval = setInterval(() => {
    if (SOUND_PROGRESS.value < max) {
      const newValue = parseFloat(SOUND_PROGRESS.value) + 1;
      SOUND_PROGRESS.value = newValue;
      CURRENT_SOUND_PROGRESS.textContent = newValue.toFixed(2);
    } else {
      if (!isPlaying) {
        SOUND_PROGRESS.value = SOUND_PROGRESS.max;
        CURRENT_SOUND_PROGRESS.textContent = SOUND_PROGRESS.max;
        clearInterval(soundInterval);
      } else {
        SOUND_PROGRESS.value = 0;
        CURRENT_SOUND_PROGRESS.textContent = "0.00";
      }
    }
  }, 1000);
}

function setDescription() {
  const selectedSound = soundsData.find(
    (sound) => sound.filename === document.getElementById("sound").value
  );
  DESCRIPTION.innerHTML = selectedSound ? selectedSound.description : "";
}

// Event Listeners
DARK_MODE_TOGGLE.addEventListener("change", function () {
  if (DARK_MODE_TOGGLE.checked) {
    document.body.classList.add("dark-mode");
    localStorage.setItem("darkMode", "enabled");
  } else {
    document.body.classList.remove("dark-mode");
    localStorage.setItem("darkMode", "disabled");
  }
});

document.getElementById("language").addEventListener("change", changeSelection);
document.getElementById("category").addEventListener("change", changeSelection);

document.getElementById("sound").addEventListener("change", function () {
  setDescription();
  setSoundLength();
});

async function changeSelection() {
  await updateSounds();
  setDescription();
  setSoundLength();
}

VOLUME_SLIDER.addEventListener("input", function () {
  const volumePercentage = parseInt(VOLUME_SLIDER.value * 100);
  VOLUME_VALUE.textContent = `${volumePercentage}%`;
});

VOLUME_SLIDER.addEventListener("change", function () {
  updateVolume(VOLUME_SLIDER.value);
});

PLAY_BUTTON.addEventListener("click", handlePlaying);
REPEAT_BUTTON.addEventListener("click", toggleLoop);

// Toggle Functions
function togglePlaying() {
  isPlaying = !isPlaying;
  setPlayIcon();
}

function toggleLoop() {
  loopEnabled = !loopEnabled;
  setLoopIcon();
}

function setPlayIcon() {
  PLAY_ICON.innerHTML = isPlaying ? STOP_SOUND : START_SOUND;
}

function setLoopIcon() {
  LOOP_ICON.innerHTML = loopEnabled ? REPEAT_ON : REPEAT_OFF;
}

function setVolumeIcon() {
  VOLUME_ICON.innerHTML = VOLUME_SLIDER.value > 0 ? VOLUME_UP : VOLUME_MUTE;
}

// Sound Control Functions
async function handlePlaying() {
  togglePlaying();
  isPlaying ? await handlePlaySound(setData()) : await handleStopSound();
}

async function handlePlaySound(data) {
  try {
    updateSoundProgress();
    const response = await fetch("/play", { method: "POST", body: data });
    const message = await response.text();
    togglePlaying();
    showToast(message);
  } catch (error) {
    showToast("Error playing sound: " + error);
  }
}

async function handleStopSound() {
  try {
    const response = await fetch("/stop", { method: "POST" });
    const message = await response.text();
    clearInterval(soundInterval);
    togglePlaying();
    showToast(message);
  } catch (error) {
    showToast("Error stopping sound: " + error);
  }
}

async function updateVolume(volume) {
  try {
    setVolumeIcon();
    const response = await fetch("/volume", {
      method: "POST",
      body: new URLSearchParams({ volume: volume }),
    });
    const message = await response.text();
    showToast(message);
  } catch (error) {
    showToast("Error setting volume: " + error);
  }
}

// Initialization Functions
function initializeDarkMode() {
  const darkMode = localStorage.getItem("darkMode");
  if (darkMode === "enabled") {
    document.body.classList.add("dark-mode");
    DARK_MODE_TOGGLE.checked = true;
  }
}

async function init() {
  await updateSounds();
  await initializeIcons();
  initializeDarkMode();
  setDescription();
  setSoundLength();
}

// Initialize the application
init();
