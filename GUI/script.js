// Initial load
updateSounds();

// Handle language and category changes
document.getElementById("language").addEventListener("change", updateSounds);
document.getElementById("category").addEventListener("change", updateSounds);

// Handle toggle sound switch change
let loopEnabled = false;
document
  .getElementById("toggle-sound")
  .addEventListener("change", function (event) {
    const data = setData();

    // Handle sound playing or stopping
    if (event.target.checked) {
      handlePlaySound(data);
    } else {
      handleStopSound();
    }
  });

// Function to update sound options based on selected language and category
function updateSounds() {
  const language = document.getElementById("language").value;
  const category = document.getElementById("category").value;

  fetch(`/sounds?language=${language}&category=${category}`)
    .then((response) => response.json())
    .then((sounds) => {
      const soundSelect = document.getElementById("sound");
      soundSelect.innerHTML = "";
      sounds.forEach((sound) => {
        const option = document.createElement("option");
        option.value = sound;
        option.textContent = sound;
        soundSelect.appendChild(option);
      });
    })
    .catch((error) => console.error("Error fetching sounds:", error));
}

function setData() {
  const formData = new FormData(document.getElementById("play-form"));
  const data = new URLSearchParams();

  // Collect form data and check loop status
  for (const pair of formData) {
    if (pair[0] === "loop") {
      loopEnabled = true;
    }
    data.append(pair[0], pair[1]);
  }

  // Append "loop" status if not already set
  if (!loopEnabled) {
    data.append("loop", "off");
  }

  return data;
}

// Function to handle playing sound
function handlePlaySound(data) {
  document.querySelector('label[for="toggle-sound"]').textContent =
    "Stop Sound";

  fetch("/play", {
    method: "POST",
    body: data,
  })
    .then((response) => response.text())
    .then((message) => {
      showToast(message);
      handleSoundFinish();
    })
    .catch((error) => showToast("Error playing sound: " + error));
}

// Function to handle stopping sound
function handleStopSound() {
  if (loopEnabled) {
    fetch("/stop", {
      method: "POST",
    })
      .then((response) => response.text())
      .then((message) => {
        showToast(message);
        handleSoundFinish();
      })
      .catch((error) => showToast("Error stopping sound: " + error));
  } else {
    isPlaying = false;
    document.querySelector('label[for="toggle-sound"]').textContent =
      "Play Sound";
  }
}

// Function to handle when sound finishes playing
function handleSoundFinish() {
  if (!loopEnabled) {
    document.getElementById("toggle-sound").checked = false;
    document.querySelector('label[for="toggle-sound"]').textContent =
      "Play Sound";
  }
}

// Function to show toast messages
function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast show";
  setTimeout(() => {
    toast.className = toast.className.replace("show", "");
  }, 3000);
}
