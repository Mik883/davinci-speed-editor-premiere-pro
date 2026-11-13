const { entrypoints } = require("uxp");
const { localFileSystem } = require("uxp").storage;
const os = require("os");

const CONFIG_PATH = `${os.homedir()}\\AppData\\Local\\SpeedEditorPremiere\\premiere_mapping.json`;
const CONFIG_URL = encodeURI(`file:/${CONFIG_PATH.replace(/\\/g, "/")}`);

const BUTTONS = [
  "SMART_INSRT", "APPND", "RIPL_OWR", "CLOSE_UP", "PLACE_ON_TOP", "SRC_OWR",
  "IN", "OUT", "TRIM_IN", "TRIM_OUT", "ROLL", "SLIP_SRC", "SLIP_DEST",
  "TRANS_DUR", "CUT", "DIS", "SMTH_CUT", "SOURCE", "TIMELINE", "SYNC_BIN",
  "TRANS", "VIDEO_ONLY", "AUDIO_ONLY", "RIPL_DEL", "AUDIO_LEVEL", "FULL_VIEW",
  "SNAP", "SPLIT", "LIVE_OWR", "ESC", "CAM1", "CAM2", "CAM3", "CAM4",
  "CAM5", "CAM6", "CAM7", "CAM8", "CAM9", "STOP_PLAY"
];

const LABELS = {
  SMART_INSRT: "Smart Insert", APPND: "Append", RIPL_OWR: "Ripple Overwrite",
  CLOSE_UP: "Close Up", PLACE_ON_TOP: "Place on Top", SRC_OWR: "Source Overwrite",
  IN: "In", OUT: "Out", TRIM_IN: "Trim In", TRIM_OUT: "Trim Out", ROLL: "Roll",
  SLIP_SRC: "Slip Source", SLIP_DEST: "Slip Destination", TRANS_DUR: "Transition Duration",
  CUT: "Cut", DIS: "Dissolve", SMTH_CUT: "Smooth Cut", SOURCE: "Source",
  TIMELINE: "Timeline", SYNC_BIN: "Sync Bin", TRANS: "Transition",
  VIDEO_ONLY: "Video Only", AUDIO_ONLY: "Audio Only", RIPL_DEL: "Ripple Delete",
  AUDIO_LEVEL: "Audio Level", FULL_VIEW: "Full View", SNAP: "Snap", SPLIT: "Split",
  LIVE_OWR: "Live Overwrite", ESC: "Esc", STOP_PLAY: "Stop / Play"
};

for (let camera = 1; camera <= 9; camera += 1) LABELS[`CAM${camera}`] = `Camera ${camera}`;

const ACTIONS = [
  ["", "— Nessuna azione —"],
  ["SMART_INSRT", "Smart Insert"], ["SRC_OWR", "Source Overwrite"],
  ["IN", "Imposta In"], ["OUT", "Imposta Out"],
  ["TRIM_IN", "Trim In"], ["TRIM_OUT", "Trim Out"], ["CLEAR_IN", "Cancella In"],
  ["CLEAR_OUT", "Cancella Out"], ["ROLL", "Roll"], ["SLIDE", "Slide"],
  ["SLIP_SRC", "Slip Source"], ["SLIP_DEST", "Slip Destination"],
  ["CUT", "Cut / Add Edit"], ["SOURCE", "Attiva Source Monitor"],
  ["TIMELINE", "Attiva Timeline"], ["TRANS", "Transizione"],
  ["VIDEO_ONLY", "Solo video"], ["AUDIO_ONLY", "Solo audio"],
  ["RIPL_DEL", "Ripple Delete"], ["AUDIO_LEVEL", "Audio Gain"],
  ["FULL_VIEW", "Full View"], ["REVIEW", "Review"], ["SNAP", "Snap"],
  ["STOP_PLAY", "Play / Stop"], ["UNDO", "Undo"], ["MARK", "Marker"],
  ["SET_TRANS_DUR", "Imposta durata transizione"]
];
for (let camera = 1; camera <= 9; camera += 1) {
  ACTIONS.push([`CAM${camera}`, `Camera ${camera}`]);
  ACTIONS.push([`SELECT_CAM${camera}`, `Seleziona Camera ${camera}`]);
}

const speed = document.querySelector("#jogSpeed");
const speedValue = document.querySelector("#speedValue");
const status = document.querySelector("#status");
const mappingRows = document.querySelector("#mappingRows");
let config = null;
let configFile = null;
let saveTimer = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
  })[char]);
}

function setStatus(message, kind = "") {
  status.textContent = message;
  status.className = `status ${kind}`;
}

function renderValue() {
  speedValue.textContent = `${Number(speed.value).toFixed(2)}×`;
}

function actionOptions(selected) {
  const values = ACTIONS.some(([value]) => value === selected)
    ? ACTIONS
    : [[selected, selected], ...ACTIONS];
  return values.map(([value, label]) =>
    `<option value="${escapeHtml(value)}"${value === selected ? " selected" : ""}>${escapeHtml(label)}</option>`
  ).join("");
}

function shortcutText(value) {
  return Array.isArray(value) ? value.join(", ") : (value || "");
}

function editorCell(key, prefix, mode, nativeTarget, shortcut) {
  const safeKey = escapeHtml(key);
  return `<div class="mapping-cell" data-key="${safeKey}" data-prefix="${prefix}">
    <select class="mode">
      <option value="native"${mode === "native" ? " selected" : ""}>Comando Premiere</option>
      <option value="shortcut"${mode === "shortcut" ? " selected" : ""}>Scorciatoia</option>
      <option value="off"${mode === "off" ? " selected" : ""}>Disattivato</option>
    </select>
    <select class="native-action"${mode === "native" ? "" : " hidden"}>${actionOptions(nativeTarget || "")}</select>
    <input class="shortcut${mode === "shortcut" ? "" : " hidden"}" type="text"
      value="${escapeHtml(shortcutText(shortcut))}" placeholder="es. ctrl+k oppure end, comma">
  </div>`;
}

function renderMappings() {
  if (!config) return;
  mappingRows.innerHTML = BUTTONS.map(key => {
    const singleMode = config.mapping_modes?.[key] || "native";
    const doubleMode = config.double_press_modes?.[key] || "off";
    return `<div class="mapping-row">
      <div class="key-name">${escapeHtml(LABELS[key] || key)}</div>
      ${editorCell(key, "single", singleMode, config.native_button_targets?.[key], config.buttons?.[key])}
      ${editorCell(key, "double", doubleMode, config.double_press_targets?.[key], config.double_press_buttons?.[key])}
    </div>`;
  }).join("");

  mappingRows.querySelectorAll(".mode").forEach(select => {
    select.addEventListener("change", event => {
      const cell = event.target.closest(".mapping-cell");
      cell.querySelector(".native-action").classList.toggle("hidden", event.target.value !== "native");
      cell.querySelector(".shortcut").classList.toggle("hidden", event.target.value !== "shortcut");
    });
  });
}

async function loadConfig() {
  try {
    configFile = await localFileSystem.getEntryWithUrl(CONFIG_URL);
    config = JSON.parse(await configFile.read());
    speed.value = Number(config.transport?.jog_scale ?? 1);
    renderValue();
    renderMappings();
    setStatus("Collegato al bridge · impostazioni live", "ok");
  } catch (error) {
    setStatus(`Configurazione non disponibile: ${error.message}`, "error");
  }
}

async function writeLatest(mutator, successMessage) {
  if (!configFile) return;
  try {
    const latest = JSON.parse(await configFile.read());
    mutator(latest);
    await configFile.write(`${JSON.stringify(latest, null, 2)}\n`);
    config = latest;
    setStatus(successMessage, "ok");
  } catch (error) {
    setStatus(`Salvataggio non riuscito: ${error.message}`, "error");
  }
}

async function saveSpeed() {
  await writeLatest(latest => {
    latest.transport = latest.transport || {};
    latest.transport.jog_scale = Math.round(Number(speed.value) * 1000) / 1000;
  }, "Velocità applicata");
}

function parseShortcut(text) {
  const parts = text.split(",").map(part => part.trim()).filter(Boolean);
  if (!parts.length) return null;
  return parts.length === 1 ? parts[0] : parts;
}

async function saveMappings() {
  await writeLatest(latest => {
    latest.mapping_modes = latest.mapping_modes || {};
    latest.native_button_targets = latest.native_button_targets || {};
    latest.buttons = latest.buttons || {};
    latest.double_press_modes = latest.double_press_modes || {};
    latest.double_press_targets = latest.double_press_targets || {};
    latest.double_press_buttons = latest.double_press_buttons || {};
    mappingRows.querySelectorAll(".mapping-cell").forEach(cell => {
      const key = cell.dataset.key;
      const prefix = cell.dataset.prefix;
      const mode = cell.querySelector(".mode").value;
      const target = cell.querySelector(".native-action").value || null;
      const shortcut = parseShortcut(cell.querySelector(".shortcut").value);
      if (prefix === "single") {
        latest.mapping_modes[key] = mode;
        latest.native_button_targets[key] = target;
        latest.buttons[key] = shortcut;
      } else {
        latest.double_press_modes[key] = mode;
        latest.double_press_targets[key] = target;
        latest.double_press_buttons[key] = shortcut;
      }
    });
  }, "Mappatura salvata e applicata");
}

speed.addEventListener("input", () => {
  renderValue();
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(saveSpeed, 160);
});
document.querySelector("#resetSpeed").addEventListener("click", () => {
  speed.value = 1;
  renderValue();
  saveSpeed();
});
document.querySelector("#reloadConfig").addEventListener("click", loadConfig);
document.querySelector("#saveMappings").addEventListener("click", saveMappings);
document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(item => item.classList.toggle("active", item === tab));
  document.querySelectorAll(".tab-page").forEach(page => page.classList.toggle("active", page.id === `tab-${tab.dataset.tab}`));
}));

entrypoints.setup({
  panels: {
    speedEditorPanel: {
      create() {},
      show() { loadConfig(); }
    }
  }
});

loadConfig();
