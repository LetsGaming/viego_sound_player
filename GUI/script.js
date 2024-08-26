// Initial constants and variables
const DESCRIPTION = document.getElementById("desc");
const VOLUME_SLIDER = document.getElementById("volume");
const VOLUME_VALUE = document.getElementById("volume-value");
const PLAY_ICON = document.getElementById("toggle-sound");
const LOOP_ICON = document.getElementById("loop-icon");

const REPEAT_ON_URL = "/static/bootstrap/icons/repeat_on.svg";
const REPEAT_OFF_URL = "/static/bootstrap/icons/repeat_off.svg";
const START_SOUND_URL = "/static/bootstrap/icons/play-fill.svg";
const STOP_SOUND_URL = "/static/bootstrap/icons/stop-fill.svg";
let REPEAT_ON, REPEAT_OFF, START_SOUND, STOP_SOUND;

let isPlaying = false;
let loopEnabled = false;
let soundsData = [];

// Helper function to fetch SVG content
async function fetchSVG(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error("Network response was not ok");
    return await response.text();
  } catch (error) {
    console.error("There was a problem with the fetch operation:", error);
  }
}

// Fetch SVGs for repeat icons
(async function initializeIcons() {
  REPEAT_ON = await fetchSVG(REPEAT_ON_URL);
  REPEAT_OFF = await fetchSVG(REPEAT_OFF_URL);
  START_SOUND = await fetchSVG(START_SOUND_URL);
  STOP_SOUND = await fetchSVG(STOP_SOUND_URL);
  setLoopIcon();
  setPlayIcon();
})();

// Function to update sound options based on selected language and category
async function updateSounds() {
  const language = document.getElementById("language").value;
  const category = document.getElementById("category").value;
  
  try {
    const response = await fetch(`/sounds?language=${language}&category=${category}`);
    const sounds = await response.json();
    soundsData = sounds;
    
    const soundSelect = document.getElementById("sound");
    soundSelect.innerHTML = sounds.map(sound => 
      `<option value="${sound.filename}">${sound.title}</option>`
    ).join('');
  } catch (error) {
    console.error("Error fetching sounds:", error);
  }
}

// Event listeners
document.getElementById("language").addEventListener("change", updateSounds);
document.getElementById("category").addEventListener("change", updateSounds);

document.getElementById("sound").addEventListener("change", function (event) {
  const selectedSound = soundsData.find(sound => sound.filename === event.target.value);
  DESCRIPTION.innerHTML = selectedSound ? selectedSound.description : '';
});

VOLUME_SLIDER.addEventListener("input", function () {
  VOLUME_VALUE.textContent = VOLUME_SLIDER.value;
  updateVolume(VOLUME_SLIDER.value);
});

PLAY_ICON.addEventListener("click", handlePlaying);

LOOP_ICON.addEventListener("click", toggleLoop);

function toggleLoop() {
  loopEnabled = !loopEnabled;
  setLoopIcon();
}

function setLoopIcon() {
  LOOP_ICON.innerHTML = loopEnabled ? REPEAT_ON : REPEAT_OFF;
}

async function handlePlaying() {
  togglePlaying();
  const data = setData();
  isPlaying ? await handlePlaySound(data) : await handleStopSound();
}

function togglePlaying() { 
  isPlaying = !isPlaying;
  setPlayIcon();
}
function setPlayIcon() {
  PLAY_ICON.innerHTML = isPlaying ? STOP_SOUND : START_SOUND;
}

// Function to prepare data for sound play
function setData() {
  const formData = new FormData(document.getElementById("play-form"));
  const data = new URLSearchParams();
  formData.forEach((value, key) => data.append(key, value));
  data.append("loop", loopEnabled ? "on" : "off");
  return data;
}

// Function to handle playing sound
async function handlePlaySound(data) {
  try {
    const response = await fetch("/play", { method: "POST", body: data });
    const message = await response.text();
    togglePlaying();
    showToast(message);
  } catch (error) {
    showToast("Error playing sound: " + error);
  }
}

// Function to handle stopping sound
async function handleStopSound() {
  try {
    const response = await fetch("/stop", { method: "POST" });
    const message = await response.text();
    togglePlaying();
    showToast(message);
  } catch (error) {
    showToast("Error stopping sound: " + error);
  }
}

// Function to update volume
async function updateVolume(volume) {
  try {
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

// Function to show toast messages
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show";
  setTimeout(() => toast.className = toast.className.replace("show", ""), 3000);
}

// Initial call to populate sounds
updateSounds();
