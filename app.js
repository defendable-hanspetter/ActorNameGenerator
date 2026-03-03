const MAX_BATCH_SIZE = 25;

const STYLE_RULES = {
  class: { label: "Class", sourceKey: "classes", render: (f, s) => `${f} the ${s}` },
  location: { label: "Location", sourceKey: "locations", render: (f, s) => `${f} of ${s}` },
  plane: { label: "Plane", sourceKey: "planes", render: (f, s) => `${f} of ${s}` },
  deity: { label: "Deity", sourceKey: "deities", render: (f, s) => `${f} of ${s}` },
};

const STYLE_KEYS = Object.keys(STYLE_RULES);
const FILES = {
  felines: "felines.txt",
  classes: "dnd_classes.txt",
  locations: "dnd_locations.txt",
  deities: "dnd_deities.txt",
  planes: "dnd_planes.txt",
};

const state = {
  sources: {},
  felinesByInitial: {},
  secondByStyleInitial: {},
};

function firstLetter(term) {
  const match = String(term).trim().match(/[A-Za-z]/);
  return match ? match[0].toLowerCase() : null;
}

function groupByInitial(values) {
  const grouped = {};
  for (const value of values) {
    const letter = firstLetter(value);
    if (!letter) continue;
    if (!grouped[letter]) grouped[letter] = [];
    grouped[letter].push(value);
  }
  return grouped;
}

function parseTxt(raw) {
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

async function loadSources() {
  const entries = Object.entries(FILES);
  const loaded = {};

  for (const [key, file] of entries) {
    const response = await fetch(file, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Failed loading ${file}: ${response.status}`);
    }
    const text = await response.text();
    const parsed = parseTxt(text);
    if (!parsed.length) {
      throw new Error(`File is empty: ${file}`);
    }
    loaded[key] = parsed;
  }

  state.sources = loaded;
  state.felinesByInitial = groupByInitial(loaded.felines);
  state.secondByStyleInitial = {};

  for (const style of STYLE_KEYS) {
    const sourceKey = STYLE_RULES[style].sourceKey;
    state.secondByStyleInitial[style] = groupByInitial(loaded[sourceKey]);
  }
}

function randomChoice(values) {
  return values[Math.floor(Math.random() * values.length)];
}

function pickStyle(value) {
  return STYLE_RULES[value] ? value : randomChoice(STYLE_KEYS);
}

function chooseAlliterativePair(style) {
  const felinesByInitial = state.felinesByInitial;
  const secondByInitial = state.secondByStyleInitial[style];
  const felineLetters = Object.keys(felinesByInitial);
  if (!felineLetters.length) {
    throw new Error("No valid feline terms available.");
  }

  const overlap = felineLetters.filter((letter) => (secondByInitial[letter] || []).length > 0);
  if (!overlap.length) {
    throw new Error("No alliterative overlap found between felines and selected style terms.");
  }

  while (true) {
    const letter = randomChoice(felineLetters);
    const secondCandidates = secondByInitial[letter] || [];
    if (!secondCandidates.length) continue;
    return [randomChoice(felinesByInitial[letter]), randomChoice(secondCandidates)];
  }
}

function generateBatch(requestedStyle, count) {
  const style = pickStyle(requestedStyle);
  const rule = STYLE_RULES[style];
  const result = [];

  for (let i = 0; i < count; i += 1) {
    const [feline, second] = chooseAlliterativePair(style);
    result.push(rule.render(feline, second));
  }

  return { style, names: result };
}

function renderResults(style, names) {
  const title = document.getElementById("result-title");
  const list = document.getElementById("results");
  title.textContent = `Results (${STYLE_RULES[style].label})`;
  list.innerHTML = names.map((name) => `<li>${name}</li>`).join("");
}

function setStatus(message, isError = false) {
  const status = document.getElementById("status");
  status.textContent = message;
  status.style.color = isError ? "#b42318" : "#4d647e";
}

function bindUi() {
  const form = document.getElementById("generator-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();

    try {
      const style = document.getElementById("style").value;
      const countRaw = Number.parseInt(document.getElementById("count").value, 10);
      const count = Number.isFinite(countRaw) ? Math.min(MAX_BATCH_SIZE, Math.max(1, countRaw)) : 1;
      const { style: selectedStyle, names } = generateBatch(style, count);
      renderResults(selectedStyle, names);
      setStatus(`Generated ${names.length} codenames.`);
    } catch (error) {
      setStatus(error.message || String(error), true);
    }
  });
}

async function main() {
  try {
    await loadSources();
    bindUi();
    setStatus("Ready.");
  } catch (error) {
    setStatus(error.message || String(error), true);
  }
}

main();
