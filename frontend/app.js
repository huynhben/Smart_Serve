const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Request failed");
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function renderEmptyState(container, message) {
  container.innerHTML = "";
  const div = document.createElement("div");
  div.className = "empty-state";
  div.textContent = message;
  container.appendChild(div);
}

function formatMacros(macronutrients) {
  const entries = Object.entries(macronutrients || {});
  if (!entries.length) {
    return "Macros: not provided";
  }
  return `Macros: ${entries
    .map(([key, value]) => `${key} ${Number(value).toFixed(1)}g`)
    .join(" • ")}`;
}

function renderScanResults(results) {
  const container = document.getElementById("scan-results");
  container.innerHTML = "";

  if (!results.items.length) {
    renderEmptyState(
      container,
      "No AI matches yet. Try a different description."
    );
    return;
  }

  const template = document.getElementById("scan-item-template");

  results.items.forEach(({ food, confidence }) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector(".scan-title").textContent = food.name;
    fragment.querySelector(
      ".scan-serving"
    ).textContent = `Serving: ${food.serving_size}`;
    fragment.querySelector(
      ".scan-calories"
    ).textContent = `${food.calories} kcal`;
    fragment.querySelector(".scan-confidence").textContent = `Confidence: ${(
      confidence * 100
    ).toFixed(0)}%`;

    const quantityInput = fragment.querySelector(".scan-quantity");
    const logButton = fragment.querySelector(".log-button");

    logButton.addEventListener("click", async () => {
      logButton.disabled = true;
      try {
        const quantity = Number(quantityInput.value) || 1;
        await request("/entries", {
          method: "POST",
          body: JSON.stringify({ food, quantity }),
        });
        await Promise.all([loadEntries(), loadSummary()]);
      } catch (error) {
        alert(error.message);
      } finally {
        logButton.disabled = false;
      }
    });

    container.appendChild(fragment);
  });
}

// ...existing code...

async function renderEntries(entries) {
  const container = document.getElementById("log-entries");
  container.innerHTML = "";

  if (!entries.items.length) {
    renderEmptyState(
      container,
      "No foods logged yet. Scan or add one to get started."
    );
    await renderSummary(); // Update the summary to show 0 if no entries exist
    return;
  }

  const template = document.getElementById("log-entry-template");

  entries.items.forEach((entry, index) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector(".log-title").textContent = entry.food.name;
    fragment.querySelector(
      ".log-calories"
    ).innerHTML = `<span class="badge">${entry.calories.toFixed(
      0
    )} kcal</span> — Qty ${entry.quantity}`;
    fragment.querySelector(
      ".log-serving"
    ).textContent = `Serving: ${entry.food.serving_size}`;
    fragment.querySelector(".log-macros").textContent = formatMacros(
      entry.macronutrients
    );
    const date = new Date(entry.timestamp);
    fragment.querySelector(
      ".log-timestamp"
    ).textContent = `Logged at ${date.toLocaleString()}`;

    const editButton = fragment.querySelector(".edit-button");
    const deleteButton = fragment.querySelector(".delete-button");

    editButton.addEventListener("click", async () => {
      const newQuantity = prompt(
        `Edit quantity for ${entry.food.name}:`,
        entry.quantity
      );
      if (newQuantity && !isNaN(newQuantity)) {
        try {
          await request(`/entries/${index}`, {
            method: "PATCH",
            body: JSON.stringify({ quantity: parseFloat(newQuantity) }),
          });
          await loadEntries(); // Reload entries and update the summary
        } catch (error) {
          alert(error.message);
        }
      }
    });

    deleteButton.addEventListener("click", async () => {
      if (confirm(`Are you sure you want to delete ${entry.food.name}?`)) {
        try {
          await request(`/entries/${index}`, { method: "DELETE" });
          await loadEntries(); // Reload entries and update the summary
        } catch (error) {
          alert(error.message);
        }
      }
    });

    container.appendChild(fragment);
  });
}

async function renderSummary() {
  const summaryContainer = document.getElementById("summary");
  summaryContainer.innerHTML = ""; // Clear the summary container

  try {
    const response = await request("/summary");
    const summaries = response.days;

    if (!summaries.length) {
      summaryContainer.textContent = "No data available for today.";
      return;
    }

    const today = new Date().toISOString().split("T")[0];
    const todaySummary = summaries.find((log) => log.day === today);

    if (!todaySummary || !todaySummary.entries.length) {
      summaryContainer.textContent = "No entries logged for today.";
      return;
    }

    const totalCalories = todaySummary.total_calories.toFixed(0);
    const macros = formatMacros(todaySummary.total_macronutrients);

    summaryContainer.innerHTML = `
      <p>Total Calories: <strong>${totalCalories} kcal</strong></p>
      <p>Macronutrients: <strong>${macros}</strong></p>
    `;
  } catch (error) {
    summaryContainer.textContent = "Failed to load daily summary.";
    console.error(error);
  }
}

async function loadEntries() {
  try {
    const response = await request("/entries");
    await renderEntries(response);
    await renderSummary(); // Ensure the summary is updated
  } catch (error) {
    console.error("Failed to load entries:", error);
  }
}

async function loadSummary() {
  try {
    const summary = await request("/summary");
    renderSummary(summary);
  } catch (error) {
    console.error(error);
  }
}

function collectMacros(form) {
  const macros = {};
  const protein = Number(form["manual-protein"].value);
  const carbs = Number(form["manual-carbs"].value);
  const fat = Number(form["manual-fat"].value);

  if (!Number.isNaN(protein) && form["manual-protein"].value)
    macros.protein = protein;
  if (!Number.isNaN(carbs) && form["manual-carbs"].value) macros.carbs = carbs;
  if (!Number.isNaN(fat) && form["manual-fat"].value) macros.fat = fat;

  return macros;
}

async function setupScanForm() {
  const form = document.getElementById("scan-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = form.querySelector("#scan-query");
    const query = input.value.trim();
    if (!query) return;

    form.querySelector("button").disabled = true;
    try {
      const results = await request(
        `/foods/search?query=${encodeURIComponent(query)}`,
        {
          method: "GET",
          headers: {},
        }
      );
      renderScanResults(results);
    } catch (error) {
      alert(error.message);
    } finally {
      form.querySelector("button").disabled = false;
    }
  });
}

async function setupManualForm() {
  const form = document.getElementById("manual-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const data = {
      name: form["manual-name"].value.trim(),
      serving_size: form["manual-serving"].value.trim(),
      calories: Number(form["manual-calories"].value),
      macronutrients: collectMacros(form),
      aliases: [],
    };
    const quantity = Number(form["manual-quantity"].value) || 1;
    const saveToLibrary = form["manual-save"].checked;

    try {
      await request("/entries", {
        method: "POST",
        body: JSON.stringify({ food: data, quantity }),
      });
      if (saveToLibrary) {
        await request("/foods", { method: "POST", body: JSON.stringify(data) });
      }
      form.reset();
      form["manual-quantity"].value = "1";
      await Promise.all([loadEntries(), loadSummary()]);
    } catch (error) {
      alert(error.message);
    }
  });
}

async function init() {
  await Promise.all([loadEntries(), loadSummary()]);
  setupScanForm();
  setupManualForm();
  setupCamera();
}

function setupCamera() {
  const video = document.getElementById("camera-preview");
  const captureButton = document.getElementById("camera-capture");
  const fileInput = document.getElementById("camera-file");

  if (!navigator.mediaDevices || !video) return;

  navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" } })
    .then((stream) => {
      video.srcObject = stream;
    })
    .catch((err) => {
      console.warn("Camera not available:", err);
    });

  captureButton.addEventListener("click", async () => {
    captureButton.disabled = true;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(async (blob) => {
        if (!blob) return;
        try {
          const results = await sendImageBlob(blob);
          renderScanResults(results);
        } catch (err) {
          alert("Image scan failed: " + err.message);
        }
      }, "image/jpeg");
    } finally {
      captureButton.disabled = false;
    }
  });

  fileInput.addEventListener("change", async (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (!f) return;
    try {
      const results = await sendImageBlob(f);
      renderScanResults(results);
    } catch (err) {
      alert("Image scan failed: " + err.message);
    }
  });
}

async function sendImageBlob(blob) {
  const fd = new FormData();
  fd.append("file", blob, "capture.jpg");

  const response = await fetch(`${API_BASE}/scan-image`, {
    method: "POST",
    body: fd,
  });

  if (!response.ok) {
    const txt = await response.text();
    throw new Error(txt || "Image scan failed");
  }

  return response.json();
}

init();
