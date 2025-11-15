const API_BASE = '/api';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Request failed');
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function renderEmptyState(container, message) {
  container.innerHTML = '';
  const div = document.createElement('div');
  div.className = 'empty-state';
  div.textContent = message;
  container.appendChild(div);
}

function formatMacros(macronutrients) {
  const entries = Object.entries(macronutrients || {});
  if (!entries.length) {
    return 'Macros: not provided';
  }
  return `Macros: ${entries.map(([key, value]) => `${key} ${Number(value).toFixed(1)}g`).join(' • ')}`;
}

function formatDate(value) {
  const date = value.includes('T') ? new Date(value) : new Date(`${value}T00:00:00`);
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

function clampProgress(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(1, value));
}

function createProgressCard(label, payload, unit = 'kcal') {
  const card = document.createElement('div');
  card.className = 'progress-card';

  const heading = document.createElement('h3');
  heading.textContent = label;
  card.appendChild(heading);

  const meta = document.createElement('div');
  meta.className = 'progress-meta';
  if (payload.target) {
    meta.innerHTML = `<span>${payload.consumed.toFixed(unit === 'g' ? 1 : 0)} ${unit}</span>
      <span>${payload.target.toFixed(unit === 'g' ? 1 : 0)} ${unit} goal</span>`;
  } else {
    meta.innerHTML = `<span>${payload.consumed.toFixed(unit === 'g' ? 1 : 0)} ${unit}</span>
      <span>No target set</span>`;
  }
  card.appendChild(meta);

  const bar = document.createElement('div');
  bar.className = 'progress-bar';
  const fill = document.createElement('div');
  fill.className = 'progress-bar-fill';
  const progressValue = payload.progress !== undefined && payload.progress !== null ? clampProgress(payload.progress) : clampProgress(payload.consumed > 0 ? 1 : 0);
  fill.style.width = `${(progressValue * 100).toFixed(0)}%`;
  bar.appendChild(fill);
  card.appendChild(bar);

  return card;
}

function renderProgress(stats) {
  const container = document.getElementById('today-progress');
  container.innerHTML = '';
  if (!stats?.today) {
    renderEmptyState(container, 'Log a food or set a goal to see progress.');
    return;
  }

  container.appendChild(createProgressCard('Calories', stats.today.calories, 'kcal'));

  const macros = stats.today.macronutrients || {};
  const macroKeys = Object.keys(macros);
  if (!macroKeys.length) {
    const hint = document.createElement('p');
    hint.className = 'form-hint';
    hint.textContent = 'Add macro targets to break down progress by protein, carbs, and fat.';
    container.appendChild(hint);
  } else {
    macroKeys.forEach((nutrient) => {
      const card = createProgressCard(nutrient.toUpperCase(), macros[nutrient], 'g');
      container.appendChild(card);
    });
  }
}

function renderWeekly(weekly) {
  const container = document.getElementById('weekly-insights');
  container.innerHTML = '';

  if (!weekly?.days?.length) {
    renderEmptyState(container, 'No weekly data yet. Track meals for a few days to unlock insights.');
    return;
  }

  const streakRow = document.createElement('div');
  streakRow.className = 'week-row';
  streakRow.innerHTML = `<strong>Current streak</strong><span class="streak-badge">🔥 ${weekly.current_streak} days</span>`;
  container.appendChild(streakRow);

  const averageRow = document.createElement('div');
  averageRow.className = 'week-row';
  averageRow.innerHTML = `<strong>Average calories (active days)</strong><span>${weekly.average_calories.toFixed(0)} kcal</span>`;
  container.appendChild(averageRow);

  weekly.days.forEach((day) => {
    const row = document.createElement('div');
    row.className = 'week-row';
    const entriesLabel = day.entry_count ? `${day.entry_count} entries` : 'No meals';
    row.innerHTML = `<strong>${formatDate(day.day)}</strong><span>${day.calories.toFixed(0)} kcal · ${entriesLabel}</span>`;
    container.appendChild(row);
  });
}

function renderLifetime(lifetime) {
  const container = document.getElementById('lifetime-stats');
  container.innerHTML = '';

  if (!lifetime || !lifetime.total_entries) {
    renderEmptyState(container, 'No history yet. Once you start logging, your lifetime stats will appear here.');
    return;
  }

  const stats = [
    { label: 'Entries logged', value: lifetime.total_entries },
    { label: 'Calories tracked', value: `${lifetime.total_calories.toFixed(0)} kcal` },
    { label: 'First entry', value: lifetime.first_entry ? formatDate(lifetime.first_entry) : 'Not logged yet' },
    {
      label: 'Most logged food',
      value: lifetime.most_logged_food ? `${lifetime.most_logged_food.name} (${lifetime.most_logged_food.count}×)` : '—',
    },
  ];

  stats.forEach((stat) => {
    const pill = document.createElement('div');
    pill.className = 'stat-pill';
    pill.innerHTML = `<span>${stat.label}</span><span>${stat.value}</span>`;
    container.appendChild(pill);
  });
}

function renderScanResults(results) {
  const container = document.getElementById('scan-results');
  container.innerHTML = '';

  if (!results.items.length) {
    renderEmptyState(container, 'No AI matches yet. Try a different description.');
    return;
  }

  const template = document.getElementById('scan-item-template');

  results.items.forEach(({ food, confidence }) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector('.scan-title').textContent = food.name;
    fragment.querySelector('.scan-serving').textContent = `Serving: ${food.serving_size}`;
    fragment.querySelector('.scan-calories').textContent = `${food.calories} kcal`;
    fragment.querySelector('.scan-confidence').textContent = `Confidence: ${(confidence * 100).toFixed(0)}%`;

    const quantityInput = fragment.querySelector('.scan-quantity');
    const logButton = fragment.querySelector('.log-button');

    logButton.addEventListener('click', async () => {
      logButton.disabled = true;
      try {
        const quantity = Number(quantityInput.value) || 1;
        await request('/entries', {
          method: 'POST',
          body: JSON.stringify({ food, quantity }),
        });
        await refreshCoreData();
      } catch (error) {
        alert(error.message);
      } finally {
        logButton.disabled = false;
      }
    });

    container.appendChild(fragment);
  });
}

function renderEntries(entries) {
  const container = document.getElementById('log-entries');
  container.innerHTML = '';

  if (!entries.items.length) {
    renderEmptyState(container, 'No foods logged yet. Scan or add one to get started.');
    return;
  }

  const template = document.getElementById('log-entry-template');

  entries.items.forEach((entry, index) => {
    const fragment = template.content.cloneNode(true);
    fragment.querySelector('.log-title').textContent = entry.food.name;
    fragment.querySelector('.log-calories').innerHTML = `<span class="badge">${entry.calories.toFixed(0)} kcal</span> — Qty ${entry.quantity}`;
    fragment.querySelector('.log-serving').textContent = `Serving: ${entry.food.serving_size}`;
    fragment.querySelector('.log-macros').textContent = formatMacros(entry.macronutrients);
    const date = new Date(entry.timestamp);
    fragment.querySelector('.log-timestamp').textContent = `Logged at ${date.toLocaleString()}`;

    const editButton = fragment.querySelector('.edit-button');
    const deleteButton = fragment.querySelector('.delete-button');

    editButton.addEventListener('click', async () => {
      const newQuantity = prompt(`Edit quantity for ${entry.food.name}:`, entry.quantity);
      if (newQuantity && !Number.isNaN(Number(newQuantity))) {
        try {
          await request(`/entries/${index}`, {
            method: 'PATCH',
            body: JSON.stringify({ quantity: parseFloat(newQuantity) }),
          });
          await refreshCoreData();
        } catch (error) {
          alert(error.message);
        }
      }
    });

    deleteButton.addEventListener('click', async () => {
      if (confirm(`Are you sure you want to delete ${entry.food.name}?`)) {
        try {
          await request(`/entries/${index}`, { method: 'DELETE' });
          await refreshCoreData();
        } catch (error) {
          alert(error.message);
        }
      }
    });

    container.appendChild(fragment);
  });
}

function renderSummary(summaryResponse) {
  const summaryContainer = document.getElementById('summary');
  summaryContainer.innerHTML = '';

  const summaries = summaryResponse?.days || [];
  if (!summaries.length) {
    renderEmptyState(summaryContainer, 'No days logged yet.');
    return;
  }

  summaries
    .slice(-7)
    .reverse()
    .forEach((log) => {
      const entryCount = log.entries.length;
      const block = document.createElement('div');
      block.className = 'summary-day';
      block.innerHTML = `
        <h3>${formatDate(log.day)}</h3>
        <p><strong>${log.total_calories.toFixed(0)} kcal</strong> · ${entryCount} ${entryCount === 1 ? 'entry' : 'entries'}</p>
        <p>${formatMacros(log.total_macronutrients)}</p>
      `;
      summaryContainer.appendChild(block);
    });
}

function collectMacros(form) {
  const macros = {};
  const protein = Number(form['manual-protein'].value);
  const carbs = Number(form['manual-carbs'].value);
  const fat = Number(form['manual-fat'].value);

  if (!Number.isNaN(protein) && form['manual-protein'].value) macros.protein = protein;
  if (!Number.isNaN(carbs) && form['manual-carbs'].value) macros.carbs = carbs;
  if (!Number.isNaN(fat) && form['manual-fat'].value) macros.fat = fat;

  return macros;
}

function collectGoalPayload(form) {
  const payload = { macronutrients: {} };
  const caloriesRaw = form['goal-calories'].value.trim();
  payload.calories = caloriesRaw ? Number(caloriesRaw) : null;

  ['protein', 'carbs', 'fat'].forEach((nutrient) => {
    const raw = form[`goal-${nutrient}`].value.trim();
    if (raw) {
      payload.macronutrients[nutrient] = Number(raw);
    }
  });

  return payload;
}

function updateGoalStatus(message) {
  const status = document.getElementById('goal-status');
  if (status) {
    status.textContent = message;
  }
}

function populateGoalForm(goals) {
  const form = document.getElementById('goal-form');
  if (!form) return;

  form['goal-calories'].value = goals.calories ?? '';
  form['goal-protein'].value = goals.macronutrients?.protein ?? '';
  form['goal-carbs'].value = goals.macronutrients?.carbs ?? '';
  form['goal-fat'].value = goals.macronutrients?.fat ?? '';

  if (goals.calories || Object.keys(goals.macronutrients || {}).length) {
    updateGoalStatus('Goals loaded. Adjust them anytime you want to rebalance your plan.');
  } else {
    updateGoalStatus('Set calories and macros to get personalised progress tracking.');
  }
}

async function loadEntriesAndSummary() {
  try {
    const [entries, summary] = await Promise.all([request('/entries'), request('/summary')]);
    renderEntries(entries);
    renderSummary(summary);
  } catch (error) {
    console.error('Failed to load entries or summary:', error);
  }
}

async function loadStats() {
  try {
    const stats = await request('/stats');
    renderProgress(stats);
    renderWeekly(stats.weekly);
    renderLifetime(stats.lifetime);
  } catch (error) {
    console.error('Failed to load stats:', error);
  }
}

async function loadGoals() {
  try {
    const response = await request('/goals');
    populateGoalForm(response.goals || {});
  } catch (error) {
    console.error('Failed to load goals:', error);
  }
}

async function refreshCoreData() {
  await Promise.all([loadEntriesAndSummary(), loadStats()]);
}

function setupScanForm() {
  const form = document.getElementById('scan-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = form.querySelector('#scan-query');
    const query = input.value.trim();
    if (!query) return;

    form.querySelector('button').disabled = true;
    try {
      const results = await request(`/foods/search?query=${encodeURIComponent(query)}`);
      renderScanResults(results);
    } catch (error) {
      alert(error.message);
    } finally {
      form.querySelector('button').disabled = false;
    }
  });
}

function setupManualForm() {
  const form = document.getElementById('manual-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const data = {
      name: form['manual-name'].value.trim(),
      serving_size: form['manual-serving'].value.trim(),
      calories: Number(form['manual-calories'].value),
      macronutrients: collectMacros(form),
      aliases: [],
    };
    const quantity = Number(form['manual-quantity'].value) || 1;
    const saveToLibrary = form['manual-save'].checked;

    try {
      await request('/entries', {
        method: 'POST',
        body: JSON.stringify({ food: data, quantity }),
      });
      if (saveToLibrary) {
        await request('/foods', { method: 'POST', body: JSON.stringify(data) });
      }
      form.reset();
      form['manual-quantity'].value = '1';
      await refreshCoreData();
    } catch (error) {
      alert(error.message);
    }
  });
}

function setupGoalForm() {
  const form = document.getElementById('goal-form');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = collectGoalPayload(form);
    try {
      await request('/goals', { method: 'PUT', body: JSON.stringify(payload) });
      updateGoalStatus('Goals saved. Today’s progress just refreshed.');
      await loadStats();
    } catch (error) {
      alert(error.message);
    }
  });

  const resetButton = document.getElementById('goal-reset');
  resetButton.addEventListener('click', async () => {
    try {
      await request('/goals', {
        method: 'PUT',
        body: JSON.stringify({
          calories: null,
          macronutrients: { protein: null, carbs: null, fat: null },
        }),
      });
      form.reset();
      updateGoalStatus('Goals cleared. Set new targets whenever you are ready.');
      await loadStats();
    } catch (error) {
      alert(error.message);
    }
  });
}

async function init() {
  await Promise.all([loadEntriesAndSummary(), loadStats(), loadGoals()]);
  setupScanForm();
  setupManualForm();
  setupGoalForm();
}

init();
