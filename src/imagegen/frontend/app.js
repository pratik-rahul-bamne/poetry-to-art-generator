/**
 * ImageGen AI — Frontend Application Logic
 * ChatGPT Image Gen 2-style experience
 */

const API = "/api/imagegen";

// ─── State ────────────────────────────────────────────────────────────────
let state = {
  selectedStyle: "none",
  selectedWidth:  512,
  selectedHeight: 512,
  numImages: 1,
  sidebarOpen: true,
  settingsOpen: false,
  activeJobs: {},       // jobId → intervalId
  currentLightbox: null,
};

// ─── DOM Refs ─────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const DOM = {
  sidebar:        $("sidebar"),
  sidebarToggle:  $("sidebarToggle"),
  menuBtn:        $("menuBtn"),
  historyList:    $("historyList"),
  newGenBtn:      $("newGenBtn"),
  welcomeScreen:  $("welcomeScreen"),
  resultsArea:    $("resultsArea"),
  resultsContainer: $("resultsContainer"),
  promptInput:    $("promptInput"),
  generateBtn:    $("generateBtn"),
  btnText:        document.querySelector(".btn-text"),
  btnIcon:        document.querySelector(".btn-icon"),
  btnLoader:      document.querySelector(".btn-loader"),
  settingsToggle: $("settingsToggle"),
  settingsPanel:  $("settingsPanel"),
  stepsRange:     $("stepsRange"),
  stepsVal:       $("stepsVal"),
  guidanceRange:  $("guidanceRange"),
  guidanceVal:    $("guidanceVal"),
  seedInput:      $("seedInput"),
  negativePrompt: $("negativePrompt"),
  statusDot:      $("statusDot"),
  statusText:     $("statusText"),
  lightbox:       $("lightbox"),
  lightboxBackdrop: $("lightboxBackdrop"),
  lightboxImg:    $("lightboxImg"),
  lightboxPrompt: $("lightboxPrompt"),
  lightboxClose:  $("lightboxClose"),
  lightboxDownload: $("lightboxDownload"),
  lightboxCopyPrompt: $("lightboxCopyPrompt"),
  toast:          $("toast"),
};

// ─── Init ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadHistory();
  checkStatus();
  setInterval(checkStatus, 5000);
});

// ─── Event Listeners ──────────────────────────────────────────────────────
function setupEventListeners() {
  // Sidebar toggle
  DOM.sidebarToggle.addEventListener("click", toggleSidebar);
  DOM.menuBtn.addEventListener("click", toggleSidebar);

  // New generation
  DOM.newGenBtn.addEventListener("click", () => {
    DOM.welcomeScreen.style.display = "flex";
    DOM.resultsArea.style.display = "none";
    DOM.promptInput.value = "";
    DOM.promptInput.focus();
  });

  // Prompt input
  DOM.promptInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      generate();
    }
  });
  DOM.promptInput.addEventListener("input", autoResizeTextarea);

  // Generate button
  DOM.generateBtn.addEventListener("click", generate);

  // Settings toggle
  DOM.settingsToggle.addEventListener("click", () => {
    state.settingsOpen = !state.settingsOpen;
    DOM.settingsPanel.style.display = state.settingsOpen ? "block" : "none";
    DOM.settingsToggle.classList.toggle("active", state.settingsOpen);
  });

  // Sliders
  DOM.stepsRange.addEventListener("input", () => {
    DOM.stepsVal.textContent = DOM.stepsRange.value;
  });
  DOM.guidanceRange.addEventListener("input", () => {
    DOM.guidanceVal.textContent = parseFloat(DOM.guidanceRange.value).toFixed(1);
  });

  // Style chips
  document.querySelectorAll(".style-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".style-chip").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.selectedStyle = btn.dataset.style;
    });
  });

  // Size buttons
  document.querySelectorAll(".size-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".size-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.selectedWidth  = parseInt(btn.dataset.w);
      state.selectedHeight = parseInt(btn.dataset.h);
    });
  });

  // Num images buttons
  document.querySelectorAll(".num-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".num-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.numImages = parseInt(btn.dataset.num);
    });
  });

  // Suggestion cards
  document.querySelectorAll(".suggestion-card").forEach(card => {
    card.addEventListener("click", () => {
      DOM.promptInput.value = card.dataset.prompt;
      autoResizeTextarea();
      DOM.promptInput.focus();
      generate();
    });
  });

  // Lightbox
  DOM.lightboxBackdrop.addEventListener("click", closeLightbox);
  DOM.lightboxClose.addEventListener("click", closeLightbox);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeLightbox();
  });
  DOM.lightboxCopyPrompt.addEventListener("click", () => {
    if (state.currentLightbox?.prompt) {
      navigator.clipboard.writeText(state.currentLightbox.prompt);
      showToast("✅ Prompt copied to clipboard!");
    }
  });
}

// ─── Auto-resize Textarea ─────────────────────────────────────────────────
function autoResizeTextarea() {
  const ta = DOM.promptInput;
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
}

// ─── Toggle Sidebar ───────────────────────────────────────────────────────
function toggleSidebar() {
  state.sidebarOpen = !state.sidebarOpen;
  DOM.sidebar.classList.toggle("collapsed", !state.sidebarOpen);
}

// ─── Check API Status ─────────────────────────────────────────────────────
async function checkStatus() {
  try {
    const res = await fetch(`${API}/status`);
    if (!res.ok) throw new Error("not ok");
    const data = await res.json();

    if (data.current_job) {
      setStatus("working", "Generating...");
    } else if (data.pipeline_loading) {
      setStatus("loading", "Loading model...");
    } else if (data.pipeline_ready) {
      setStatus("done", "Ready");
    } else {
      setStatus("idle", "Idle");
    }
  } catch {
    setStatus("idle", "API offline");
  }
}

function setStatus(type, text) {
  DOM.statusDot.className = "status-dot " + type;
  DOM.statusText.textContent = text;
}

// ─── Generate ─────────────────────────────────────────────────────────────
async function generate() {
  const prompt = DOM.promptInput.value.trim();
  if (!prompt) {
    DOM.promptInput.focus();
    showToast("⚠️ Please enter a prompt first!");
    return;
  }

  // Switch to results view
  DOM.welcomeScreen.style.display = "none";
  DOM.resultsArea.style.display = "flex";

  // Build request
  const req = {
    prompt,
    negative_prompt: DOM.negativePrompt.value.trim() || undefined,
    width:  state.selectedWidth,
    height: state.selectedHeight,
    steps:  parseInt(DOM.stepsRange.value),
    guidance_scale: parseFloat(DOM.guidanceRange.value),
    seed:   parseInt(DOM.seedInput.value) || -1,
    style:  state.selectedStyle,
    num_images: state.numImages,
  };

  // Disable button
  setGenerating(true);

  try {
    const res  = await fetch(`${API}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Generation failed");
    }

    const data = await res.json();
    createJobCard(data.job_id, prompt, req);
    pollJob(data.job_id);

  } catch (err) {
    showToast("❌ " + err.message);
    setGenerating(false);
  }
}

function setGenerating(active) {
  DOM.generateBtn.disabled = active;
  DOM.btnText.style.display = active ? "none" : "inline";
  DOM.btnIcon.style.display = active ? "none" : "block";
  DOM.btnLoader.style.display = active ? "flex" : "none";
}

// ─── Job Card ─────────────────────────────────────────────────────────────
function createJobCard(jobId, prompt, req) {
  const card = document.createElement("div");
  card.className = "gen-card";
  card.id = `card-${jobId}`;

  const styleLabel = req.style !== "none" ? ` · ${req.style.replace("_", " ")}` : "";
  const sizeLabel  = `${req.width}×${req.height}`;

  card.innerHTML = `
    <div class="gen-card-header">
      <div class="gen-avatar">✨</div>
      <div class="gen-meta">
        <p class="gen-prompt-text">${escapeHtml(prompt)}</p>
        <p class="gen-info">${sizeLabel}${styleLabel} · ${req.steps} steps · scale ${req.guidance_scale}</p>
      </div>
    </div>
    <div class="gen-progress" id="progress-${jobId}">
      <div class="progress-bar-track">
        <div class="progress-bar-fill" id="fill-${jobId}" style="width:2%"></div>
      </div>
      <div class="progress-label">
        <span id="progress-text-${jobId}">Starting up...</span>
        <span id="progress-pct-${jobId}">0%</span>
      </div>
    </div>
    <div class="gen-images-grid cols-${req.num_images > 2 ? 4 : req.num_images}" id="images-${jobId}">
      ${Array(req.num_images).fill(`<div class="img-skeleton"></div>`).join("")}
    </div>
    <div class="gen-card-footer" id="footer-${jobId}" style="display:none"></div>
  `;

  DOM.resultsContainer.insertBefore(card, DOM.resultsContainer.firstChild);
  card.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ─── Poll Job ─────────────────────────────────────────────────────────────
function pollJob(jobId) {
  const interval = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/job/${jobId}`);
      if (!res.ok) return;
      const job  = await res.json();

      updateJobCard(jobId, job);

      if (job.status === "done" || job.status === "error") {
        clearInterval(interval);
        delete state.activeJobs[jobId];
        setGenerating(false);
        if (job.status === "done") {
          showToast(`🎨 Image ready! Took ${job.time_taken}s`);
          loadHistory();
          checkStatus();
        } else {
          showToast("❌ Generation failed: " + (job.error || "Unknown error"));
        }
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }, 2000);

  state.activeJobs[jobId] = interval;
}

function updateJobCard(jobId, job) {
  const fill     = $(`fill-${jobId}`);
  const pct      = $(`progress-pct-${jobId}`);
  const label    = $(`progress-text-${jobId}`);
  const progress = $(`progress-${jobId}`);
  const imagesEl = $(`images-${jobId}`);
  const footer   = $(`footer-${jobId}`);

  if (!fill) return;

  const p = job.progress || 0;
  fill.style.width = p + "%";
  pct.textContent  = p + "%";

  // Status labels
  const labels = {
    "pending":       "Queued...",
    "loading_model": "Loading AI model (first time only)...",
    "queued":        "Queued...",
    "generating":    job.step ? `Step ${job.step}/${job.total_steps}...` : "Generating...",
    "done":          "Complete!",
    "error":         "Error: " + (job.error || "failed"),
  };
  label.textContent = labels[job.status] || job.status;

  // Show images when done
  if (job.status === "done" && job.images && job.images.length > 0) {
    progress.style.display = "none";
    imagesEl.innerHTML = job.images.map((filename, i) => `
      <div class="gen-img-wrap" data-img="${filename}" data-prompt="${escapeHtml(job.prompt || "")}">
        <img src="${API}/image/${filename}" alt="Generated image ${i+1}" loading="lazy" />
        <div class="img-overlay">
          <button class="img-action-btn" title="View fullscreen" onclick="openLightbox('${filename}', '${escapeHtml(job.prompt || '')}')">
            <svg viewBox="0 0 24 24" fill="none"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <a class="img-action-btn" href="${API}/image/${filename}" download="${filename}" title="Download">
            <svg viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </a>
        </div>
      </div>
    `).join("");

    // Footer
    footer.style.display = "flex";
    footer.innerHTML = `
      <span class="footer-badge">⏱ ${job.time_taken}s</span>
      <span class="footer-badge">🎲 Seed: ${job.seed}</span>
      <div class="footer-actions">
        <button class="footer-btn" onclick="reusePrompt('${escapeHtml(job.prompt || '')}')">
          <svg viewBox="0 0 24 24" fill="none"><path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Regenerate
        </button>
        <button class="footer-btn" onclick="copyPromptText('${escapeHtml(job.prompt || '')}')">
          <svg viewBox="0 0 24 24" fill="none"><path d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Copy Prompt
        </button>
      </div>
    `;
  }

  if (job.status === "error") {
    progress.style.display = "none";
    imagesEl.innerHTML = `
      <div style="grid-column:1/-1; padding:20px; text-align:center; color:var(--error); font-size:13px;">
        ❌ ${escapeHtml(job.error || "Generation failed")}
      </div>
    `;
  }
}

// ─── Lightbox ─────────────────────────────────────────────────────────────
function openLightbox(filename, prompt) {
  state.currentLightbox = { filename, prompt };
  DOM.lightboxImg.src = `${API}/image/${filename}`;
  DOM.lightboxImg.alt = prompt;
  DOM.lightboxPrompt.textContent = prompt;
  DOM.lightboxDownload.href = `${API}/image/${filename}`;
  DOM.lightboxDownload.download = filename;
  DOM.lightbox.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeLightbox() {
  DOM.lightbox.style.display = "none";
  DOM.lightboxImg.src = "";
  state.currentLightbox = null;
  document.body.style.overflow = "";
}

// ─── Reuse Prompt ─────────────────────────────────────────────────────────
function reusePrompt(prompt) {
  DOM.promptInput.value = prompt;
  autoResizeTextarea();
  DOM.promptInput.focus();
  DOM.promptInput.scrollIntoView({ behavior: "smooth" });
}

function copyPromptText(prompt) {
  navigator.clipboard.writeText(prompt).then(() => {
    showToast("✅ Prompt copied!");
  });
}

// ─── History ──────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch(`${API}/history`);
    if (!res.ok) return;
    const hist = await res.json();
    renderHistory(hist);
  } catch {
    // API not running yet
  }
}

function renderHistory(items) {
  if (!items || items.length === 0) {
    DOM.historyList.innerHTML = `
      <div class="history-empty">
        <svg viewBox="0 0 24 24" fill="none"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        <p>No generations yet</p>
      </div>
    `;
    return;
  }

  DOM.historyList.innerHTML = items.slice(0, 20).map(item => {
    const thumb = item.images && item.images[0]
      ? `<img class="history-thumb" src="${API}/image/${item.images[0]}" alt="" loading="lazy" />`
      : `<div class="history-thumb-placeholder">🎨</div>`;

    const date = new Date(item.created_at).toLocaleDateString();

    return `
      <div class="history-item" onclick="loadHistoryItem(${JSON.stringify(JSON.stringify(item))})" title="${escapeHtml(item.prompt)}">
        ${thumb}
        <div class="history-info">
          <div class="history-prompt">${escapeHtml(item.prompt)}</div>
          <div class="history-meta">${date} · ${item.width}×${item.height}</div>
        </div>
      </div>
    `;
  }).join("");
}

function loadHistoryItem(itemJson) {
  try {
    const item = JSON.parse(itemJson);
    DOM.welcomeScreen.style.display = "none";
    DOM.resultsArea.style.display = "flex";

    if ($(`card-${item.id}`)) return;

    const card = document.createElement("div");
    card.className = "gen-card";
    card.id = `card-${item.id}`;

    const styleLabel = item.style && item.style !== "none" ? ` · ${item.style.replace("_", " ")}` : "";

    card.innerHTML = `
      <div class="gen-card-header">
        <div class="gen-avatar">🕒</div>
        <div class="gen-meta">
          <p class="gen-prompt-text">${escapeHtml(item.prompt)}</p>
          <p class="gen-info">${item.width}×${item.height}${styleLabel} · ${new Date(item.created_at).toLocaleString()}</p>
        </div>
      </div>
      <div class="gen-images-grid cols-${item.images.length > 2 ? 4 : item.images.length}">
        ${item.images.map((f, i) => `
          <div class="gen-img-wrap">
            <img src="${API}/image/${f}" alt="Image ${i+1}" loading="lazy" />
            <div class="img-overlay">
              <button class="img-action-btn" onclick="openLightbox('${f}', '${escapeHtml(item.prompt)}')">
                <svg viewBox="0 0 24 24" fill="none"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
              <a class="img-action-btn" href="${API}/image/${f}" download="${f}">
                <svg viewBox="0 0 24 24" fill="none"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </a>
            </div>
          </div>
        `).join("")}
      </div>
      <div class="gen-card-footer" style="display:flex">
        <span class="footer-badge">⏱ ${item.time_taken}s</span>
        <span class="footer-badge">🎲 Seed: ${item.seed}</span>
        <div class="footer-actions">
          <button class="footer-btn" onclick="reusePrompt('${escapeHtml(item.prompt)}')">
            <svg viewBox="0 0 24 24" fill="none"><path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Regenerate
          </button>
        </div>
      </div>
    `;

    DOM.resultsContainer.insertBefore(card, DOM.resultsContainer.firstChild);
    card.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    console.error("History load error:", e);
  }
}

// ─── Toast ────────────────────────────────────────────────────────────────
let toastTimeout;
function showToast(msg, duration = 3000) {
  DOM.toast.textContent = msg;
  DOM.toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => DOM.toast.classList.remove("show"), duration);
}

// ─── Utilities ────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ─── Expose globals for inline onclick handlers ───────────────────────────
window.openLightbox    = openLightbox;
window.reusePrompt     = reusePrompt;
window.copyPromptText  = copyPromptText;
window.loadHistoryItem = loadHistoryItem;
