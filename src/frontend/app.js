/**
 * PoemVision AI v2.0 — Frontend Application
 * Architecture: AuthManager + TabRouter + GenerationFlow + GalleryManager + AdminManager
 *
 * API endpoints used:
 *   POST /api/v1/auth/register
 *   POST /api/v1/auth/login
 *   GET  /api/v1/auth/me
 *   GET  /api/v1/gallery
 *   GET  /api/v1/sd-status
 *   POST /api/v1/sd-preload
 *   POST /api/v1/analyze
 *   POST /api/v1/generate-image
 *   POST /api/v1/compose
 *   GET  /api/v1/download/{filename}
 *   GET  /api/v1/history (auth)
 *   GET  /api/v1/poems   (auth)
 *   POST /api/v1/poems   (auth)
 *   DELETE /api/v1/poems/{id} (auth)
 *   GET  /api/v1/admin/stats (admin)
 *   GET  /api/v1/admin/logs  (admin)
 *   GET  /api/v1/admin/users (admin)
 *   PATCH /api/v1/users/me  (auth)
 */

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  // Generation
  analysis: null,
  bgFilename: null,
  finalFilename: null,
  storyFilename: null,
  poemText: "",
  font: "Dancing Script, cursive",
  sdStyle: "none",
  sdWidth: 512, sdHeight: 512, sdSteps: 20, sdGuidance: 7.5, sdSeed: -1,
  sdStatusInterval: null,
  // Auth
  token: localStorage.getItem("pv_token") || null,
  user: null,
  // Current tab
  currentTab: "generate",
};

// ── API Base ──────────────────────────────────────────────────────────────────
const API = "/api/v1";

async function apiFetch(endpoint, body, method) {
  const m = method || (body !== undefined ? "POST" : "GET");
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;

  const opts = { method: m, headers };
  if (body !== undefined && m !== "GET") opts.body = JSON.stringify(body);

  const res = await fetch(endpoint, opts);

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const err = await res.json(); detail = err.detail || detail; } catch (_) {}
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ── Particle background ───────────────────────────────────────────────────────
(function initParticles() {
  const container = document.getElementById("particles");
  for (let i = 0; i < 35; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.left = `${Math.random() * 100}%`;
    p.style.top = `${100 + Math.random() * 10}%`;
    p.style.width = p.style.height = `${1 + Math.random() * 2.5}px`;
    p.style.animationDuration = `${8 + Math.random() * 16}s`;
    p.style.animationDelay = `${Math.random() * 10}s`;
    p.style.opacity = `${0.2 + Math.random() * 0.6}`;
    container.appendChild(p);
  }
})();

// ═══════════════════════════════════════════════════════════════════════════════
// AUTH MANAGER
// ═══════════════════════════════════════════════════════════════════════════════

function openAuthModal(tab = "login") {
  document.getElementById("authModalOverlay").classList.remove("hidden");
  switchModalTab(tab);
}

function closeAuthModal() {
  document.getElementById("authModalOverlay").classList.add("hidden");
}

function closeAuthModalIfOutside(e) {
  if (e.target === document.getElementById("authModalOverlay")) closeAuthModal();
}

function switchModalTab(tab) {
  document.getElementById("loginForm").classList.toggle("hidden", tab !== "login");
  document.getElementById("registerForm").classList.toggle("hidden", tab !== "register");
  document.getElementById("modalTabLogin").classList.toggle("active", tab === "login");
  document.getElementById("modalTabRegister").classList.toggle("active", tab === "register");
  document.getElementById("loginError").classList.add("hidden");
  document.getElementById("registerError").classList.add("hidden");
}

async function submitLogin(e) {
  e.preventDefault();
  const btn = document.getElementById("loginSubmitBtn");
  const errEl = document.getElementById("loginError");
  errEl.classList.add("hidden");
  btn.disabled = true;
  btn.textContent = "Signing in…";

  try {
    const data = await apiFetch(`${API}/auth/login`, {
      email: document.getElementById("loginEmail").value,
      password: document.getElementById("loginPassword").value,
    });
    handleAuthSuccess(data);
    closeAuthModal();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign In";
  }
}

async function submitRegister(e) {
  e.preventDefault();
  const btn = document.getElementById("registerSubmitBtn");
  const errEl = document.getElementById("registerError");
  errEl.classList.add("hidden");
  btn.disabled = true;
  btn.textContent = "Creating account…";

  try {
    const data = await apiFetch(`${API}/auth/register`, {
      name: document.getElementById("regName").value,
      email: document.getElementById("regEmail").value,
      password: document.getElementById("regPassword").value,
    });
    handleAuthSuccess(data);
    closeAuthModal();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Account";
  }
}

function handleAuthSuccess(data) {
  state.token = data.access_token;
  state.user = { id: data.user_id, name: data.name, email: data.email, role: data.role };
  localStorage.setItem("pv_token", data.access_token);
  updateAuthUI();
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("pv_token");
  updateAuthUI();
  switchTab("generate");
  closeUserDropdown();
}

function updateAuthUI() {
  const isAuth = !!state.user;
  const isAdmin = state.user?.role === "admin";

  document.getElementById("loginBtn").classList.toggle("hidden", isAuth);
  document.getElementById("userMenuWrap").classList.toggle("hidden", !isAuth);

  if (isAuth) {
    const initial = (state.user.name || "U")[0].toUpperCase();
    document.querySelectorAll(".user-avatar").forEach(el => el.textContent = initial);
    document.getElementById("userDisplayName").textContent = state.user.name || "User";
    document.getElementById("dropdownEmail").textContent = state.user.email || "";
  }

  // Show/hide auth-only tabs
  document.querySelectorAll(".auth-only").forEach(el => el.classList.toggle("hidden", !isAuth));
  document.querySelectorAll(".admin-only").forEach(el => el.classList.toggle("hidden", !isAdmin));

  // Save poem toggle
  document.getElementById("saveToggleRow").classList.toggle("hidden", !isAuth);
  document.getElementById("saveResultRow").classList.toggle("hidden", !isAuth);

  // Admin menu
  document.getElementById("adminMenuBtn")?.classList.toggle("hidden", !isAdmin);
}

function toggleUserDropdown() {
  document.getElementById("userDropdown").classList.toggle("hidden");
}

function closeUserDropdown() {
  document.getElementById("userDropdown").classList.add("hidden");
}

// Close dropdown on outside click
document.addEventListener("click", (e) => {
  const wrap = document.getElementById("userMenuWrap");
  if (wrap && !wrap.contains(e.target)) closeUserDropdown();
});

// ═══════════════════════════════════════════════════════════════════════════════
// TAB ROUTER
// ═══════════════════════════════════════════════════════════════════════════════

function switchTab(tab) {
  state.currentTab = tab;
  closeUserDropdown();

  // Panel visibility
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  const panel = document.getElementById(`panel-${tab}`);
  if (panel) panel.classList.add("active");

  // Tab button active state
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById(`tab-${tab}`);
  if (btn) btn.classList.add("active");

  // Hero only on generate tab
  const hero = document.getElementById("heroSection");
  if (hero) hero.style.display = (tab === "generate") ? "" : "none";

  // Lazy-load tab content
  if (tab === "gallery")  loadGallery();
  if (tab === "history")  loadHistory();
  if (tab === "saved")    loadSavedPoems();
  if (tab === "profile")  loadProfile();
  if (tab === "admin")    loadAdmin();

  // Scroll to top
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SD STATUS
// ═══════════════════════════════════════════════════════════════════════════════

async function pollSDStatus() {
  try {
    const status = await apiFetch(`${API}/sd-status`);
    const dot   = document.getElementById("sdDot");
    const label = document.getElementById("sdStatusLabel");

    if (status.ready) {
      dot.className = "sd-dot ready"; label.textContent = "SD Ready ✓";
      document.getElementById("sdPreloadLink").textContent = "Model loaded ✓";
      if (state.sdStatusInterval) { clearInterval(state.sdStatusInterval); state.sdStatusInterval = null; }
    } else if (status.loading) {
      dot.className = "sd-dot loading"; label.textContent = "Loading model...";
    } else {
      dot.className = "sd-dot idle"; label.textContent = "SD not loaded";
    }
  } catch {
    document.getElementById("sdDot").className = "sd-dot error";
    document.getElementById("sdStatusLabel").textContent = "API offline";
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// GENERATION FLOW
// ═══════════════════════════════════════════════════════════════════════════════

function setStep(stepId, status, label) {
  const el = document.getElementById(stepId);
  const statusEl = el.querySelector(".step-status");
  el.className = "step " + status;
  statusEl.className = "step-status " + status;
  statusEl.textContent = label;
}

function resetSteps() {
  for (let i = 1; i <= 3; i++) setStep(`step${i}`, "", "—");
}

function showCard(id) {
  ["inputCard","progressCard","resultCard","errorCard"].forEach(c => {
    const el = document.getElementById(c);
    if (el) el.classList.toggle("hidden", c !== id);
  });
}

function showError(message) {
  document.getElementById("errorMessage").textContent = message;
  showCard("errorCard");
}

function showAnalysisTags(analysis) {
  document.getElementById("tagTheme").textContent = "🎭 " + analysis.theme;
  document.getElementById("tagMood").textContent  = "💫 " + analysis.mood;
  document.getElementById("tagLang").textContent  = "🌐 " + analysis.language;
  document.getElementById("analysisTags").classList.remove("hidden");
}

async function startGeneration() {
  const poem = document.getElementById("poemInput").value.trim();
  if (poem.length < 10) { alert("Please enter a poem with at least a few lines."); return; }

  const theme    = document.getElementById("themeSelect").value;
  const format   = document.getElementById("formatSelect").value;
  const provider = document.getElementById("providerSelect").value;
  state.poemText = poem;

  const btn = document.getElementById("generateBtn");
  btn.disabled = true;

  resetSteps();
  document.getElementById("analysisTags").classList.add("hidden");
  document.getElementById("sdProgressBlock").classList.add("hidden");
  showCard("progressCard");

  const isSD = provider === "stable-diffusion";
  document.getElementById("step2Desc").textContent = isSD
    ? "Stable Diffusion generates locally on your machine"
    : "Cloud AI creates a matching aesthetic image";

  try {
    // Step 1: Analyze
    setStep("step1", "active", "Running…");
    const analyzeRes = await apiFetch(`${API}/analyze`, { poem, theme_override: theme || null });
    state.analysis = analyzeRes;
    setStep("step1", "done", "✓ Done");
    showAnalysisTags(analyzeRes);

    // Step 2: Generate image
    setStep("step2", "active", "Running…");
    if (isSD) {
      document.getElementById("sdProgressBlock").classList.remove("hidden");
      document.getElementById("sdProgressText").textContent = `Running Stable Diffusion (${state.sdSteps} steps)...`;
      startSDProgressAnimation();
    }

    let sdStyleFinal = state.sdStyle;
    if (sdStyleFinal === "none" && analyzeRes.mood) {
      const moodMap = { romantic:"romantic", dark:"dark", sad:"dark", nature:"nature", joyful:"joyful", mystical:"mystical", melancholic:"melancholic" };
      sdStyleFinal = moodMap[analyzeRes.mood?.toLowerCase()] || "none";
    }

    const imageRes = await apiFetch(`${API}/generate-image`, {
      image_prompt: analyzeRes.image_prompt,
      provider,
      sd_style:    sdStyleFinal,
      sd_width:    state.sdWidth,
      sd_height:   state.sdHeight,
      sd_steps:    state.sdSteps,
      sd_guidance: state.sdGuidance,
      sd_seed:     state.sdSeed,
    });
    state.bgFilename = imageRes.bg_filename;
    stopSDProgressAnimation();
    document.getElementById("sdProgressBlock").classList.add("hidden");
    setStep("step2", "done", "✓ Done");

    // Step 3: Compose
    setStep("step3", "active", "Running…");
    const composeRes = await apiFetch(`${API}/compose`, {
      poem,
      bg_filename: state.bgFilename,
      theme: analyzeRes.theme,
      mood: analyzeRes.mood,
      format,
    });
    state.finalFilename = composeRes.final_filename;
    setStep("step3", "done", "✓ Done");

    // Show result
    await showResult(composeRes.url, analyzeRes, format, provider);
    loadGallery();
    if (format === "square") {
      generateStoryVersion(poem, state.bgFilename, analyzeRes).catch(() => {});
    }

    // Auto-save poem if logged in and toggle checked
    const saveToggle = document.getElementById("savePoemToggle");
    if (state.user && saveToggle && saveToggle.checked) {
      saveCurrentPoem(analyzeRes).catch(() => {});
    }

  } catch (err) {
    console.error(err);
    stopSDProgressAnimation();
    showError(err.message || "An unexpected error occurred. Please check your API key and try again.");
  } finally {
    btn.disabled = false;
  }
}

// SD progress animation
let _sdAnimFrame = null, _sdStart = null;
function startSDProgressAnimation() {
  const fill = document.getElementById("sdProgressFill");
  _sdStart = Date.now();
  function animate() {
    const elapsed = (Date.now() - _sdStart) / 1000;
    const pct = 95 * (1 - Math.exp(-elapsed / 120));
    fill.style.width = pct + "%";
    _sdAnimFrame = requestAnimationFrame(animate);
  }
  _sdAnimFrame = requestAnimationFrame(animate);
}
function stopSDProgressAnimation() {
  if (_sdAnimFrame) { cancelAnimationFrame(_sdAnimFrame); _sdAnimFrame = null; }
  const fill = document.getElementById("sdProgressFill");
  fill.style.width = "100%";
  setTimeout(() => { fill.style.width = "0%"; }, 600);
}

async function generateStoryVersion(poem, bgFilename, analysis) {
  const res = await apiFetch(`${API}/compose`, { poem, bg_filename: bgFilename, theme: analysis.theme, mood: analysis.mood, format: "story" });
  state.storyFilename = res.final_filename;
}

async function showResult(imageUrl, analysis, format, provider) {
  const img = document.getElementById("resultImage");
  img.src = imageUrl + "?t=" + Date.now();
  const meta = document.getElementById("resultMeta");
  const dims = format === "story" ? "1080×1920" : "1024×1024";
  const provLabel = provider === "stable-diffusion" ? "Stable Diffusion" : "Pollinations.ai";
  meta.textContent = `${dims} · ${analysis.theme} · ${analysis.language} · via ${provLabel}`;
  await new Promise(r => { img.onload = r; img.onerror = r; setTimeout(r, 2000); });
  showCard("resultCard");
}

function downloadImage(format) {
  const filename = (format === "story" && state.storyFilename) ? state.storyFilename : state.finalFilename;
  if (!filename) { alert("Image not ready. Please wait a moment."); return; }
  const link = document.createElement("a");
  link.href = `${API}/download/${filename}`;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function resetApp() {
  state.analysis = null; state.bgFilename = null; state.finalFilename = null; state.storyFilename = null;
  state.poemText = "";
  document.getElementById("poemInput").value = "";
  document.getElementById("charCounter").textContent = "0 / 1200";
  document.getElementById("themeSelect").value = "";
  document.getElementById("formatSelect").value = "square";
  document.getElementById("fontSelect").value = "Dancing Script, cursive";
  document.getElementById("poemInput").style.fontFamily = state.font;
  showCard("inputCard");
}

// ═══════════════════════════════════════════════════════════════════════════════
// SAVE POEM
// ═══════════════════════════════════════════════════════════════════════════════

async function saveCurrentPoem(analysis) {
  if (!state.user) { openAuthModal("register"); return; }
  const poem = state.poemText || document.getElementById("poemInput").value.trim();
  if (!poem) return;

  const btn = document.getElementById("savePoemBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }

  try {
    await apiFetch(`${API}/poems`, {
      poem_text: poem,
      theme: analysis?.theme || state.analysis?.theme,
      mood: analysis?.mood || state.analysis?.mood,
      language: analysis?.language || state.analysis?.language,
    });
    if (btn) { btn.textContent = "✓ Saved!"; btn.style.color = "var(--success)"; }
  } catch (err) {
    if (btn) { btn.textContent = "Save failed"; btn.disabled = false; }
    console.warn("Save failed:", err);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// GALLERY
// ═══════════════════════════════════════════════════════════════════════════════

let _galleryLoaded = false;

async function loadGallery() {
  const grid = document.getElementById("galleryGrid");
  if (!grid) return;

  try {
    const items = await apiFetch(`${API}/gallery`);
    _galleryLoaded = true;

    if (!items || items.length === 0) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🎨</div><div class="empty-text">No creations yet</div><div class="empty-hint">Generate your first artwork to see it here!</div></div>`;
      return;
    }

    grid.innerHTML = items.map(item => `
      <div class="gallery-item" onclick="window.open('${item.image_path}', '_blank')">
        <img class="gallery-thumb" src="${item.image_path}" alt="Gallery art" loading="lazy">
        <div class="gallery-info">
          <p class="gallery-poem-preview">${item.poem_text ? (item.poem_text.substring(0, 80) + "...") : "Poem artwork"}</p>
          <div class="gallery-meta">
            ${item.theme ? `<span class="gallery-tag tag-theme-gallery">${item.theme}</span>` : ""}
            ${item.mood ? `<span class="gallery-tag tag-mood-gallery">${item.mood}</span>` : ""}
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.warn("Gallery load failed:", err);
    if (grid) grid.innerHTML = `<div class="empty-state">Could not load gallery.</div>`;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HISTORY
// ═══════════════════════════════════════════════════════════════════════════════

async function loadHistory() {
  const grid = document.getElementById("historyGrid");
  if (!grid) return;
  if (!state.user) {
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔒</div><div class="empty-text">Sign in to view history</div></div>`;
    return;
  }

  grid.innerHTML = `<div class="empty-state">Loading…</div>`;
  try {
    const data = await apiFetch(`${API}/history`);
    const items = data.items || [];

    if (!items.length) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">📜</div><div class="empty-text">No history yet</div><div class="empty-hint">Generate your first artwork to see it here.</div></div>`;
      return;
    }

    grid.innerHTML = items.map(item => `
      <div class="history-item">
        ${item.final_artwork_url ? `<img class="history-thumb" src="${item.final_artwork_url}" alt="Artwork" loading="lazy">` : `<div style="height:200px;background:var(--surface);display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:40px;">🎨</div>`}
        <div class="history-info">
          <span class="history-status ${item.status}">${item.status}</span>
          <div class="history-meta">
            <span>⏱ ${item.generation_time ? item.generation_time.toFixed(1) + "s" : "—"}</span>
            <span>📡 ${item.provider_used || "—"}</span>
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:6px;">${item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}</div>
          ${item.final_artwork_url ? `<button onclick="window.open('${item.final_artwork_url}','_blank')" style="margin-top:10px;padding:6px 14px;border-radius:8px;background:var(--surface-hover);border:1px solid var(--border);color:var(--text-primary);font-size:12px;cursor:pointer;">View →</button>` : ""}
        </div>
      </div>
    `).join("");
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Failed to load history.</div>`;
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SAVED POEMS
// ═══════════════════════════════════════════════════════════════════════════════

async function loadSavedPoems() {
  const grid = document.getElementById("savedGrid");
  if (!grid) return;
  if (!state.user) {
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔒</div><div class="empty-text">Sign in to view saved poems</div></div>`;
    return;
  }

  grid.innerHTML = `<div class="empty-state">Loading…</div>`;
  try {
    const data = await apiFetch(`${API}/poems`);
    const items = data.items || [];

    if (!items.length) {
      grid.innerHTML = `<div class="empty-state"><div class="empty-icon">💾</div><div class="empty-text">No saved poems yet</div><div class="empty-hint">Generate artwork and save your poems for later.</div></div>`;
      return;
    }

    grid.innerHTML = items.map(item => `
      <div class="saved-item" id="saved-${item.id}">
        <div class="saved-info">
          <p class="saved-poem-text">${escapeHtml(item.poem_text)}</p>
          <div class="gallery-meta" style="margin-bottom:10px;">
            ${item.theme ? `<span class="gallery-tag tag-theme-gallery">${item.theme}</span>` : ""}
            ${item.mood ? `<span class="gallery-tag tag-mood-gallery">${item.mood}</span>` : ""}
            ${item.language ? `<span class="gallery-tag" style="background:rgba(126,182,240,0.1);color:var(--accent-3);">${item.language}</span>` : ""}
          </div>
          <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;">${item.created_at ? new Date(item.created_at).toLocaleDateString() : ""}</div>
          <div class="saved-actions">
            <button class="btn-generate-saved" onclick="generateFromSaved('${encodeURIComponent(item.poem_text)}')">✦ Generate</button>
            <button class="btn-delete-saved" onclick="deleteSavedPoem('${item.id}')">🗑 Delete</button>
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Failed to load saved poems.</div>`;
  }
}

function generateFromSaved(encodedPoem) {
  const poem = decodeURIComponent(encodedPoem);
  document.getElementById("poemInput").value = poem;
  document.getElementById("charCounter").textContent = `${poem.length} / 1200`;
  switchTab("generate");
}

async function deleteSavedPoem(id) {
  if (!confirm("Delete this poem?")) return;
  try {
    await apiFetch(`${API}/poems/${id}`, undefined, "DELETE");
    const el = document.getElementById(`saved-${id}`);
    if (el) el.remove();
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// PROFILE
// ═══════════════════════════════════════════════════════════════════════════════

async function loadProfile() {
  if (!state.user) return;

  document.getElementById("profileName").textContent = state.user.name;
  document.getElementById("profileEmail").textContent = state.user.email;
  document.getElementById("profileRole").textContent = state.user.role;
  document.getElementById("profileAvatarLg").textContent = (state.user.name || "U")[0].toUpperCase();
  document.getElementById("editName").value = state.user.name;

  try {
    const me = await apiFetch(`${API}/auth/me`);
    const memberSince = me.created_at ? new Date(me.created_at).getFullYear() : "—";
    document.getElementById("statMember").textContent = memberSince;
  } catch {}

  try {
    const poems = await apiFetch(`${API}/poems`);
    document.getElementById("statPoems").textContent = poems.total || 0;
  } catch {}

  try {
    const hist = await apiFetch(`${API}/history`);
    document.getElementById("statGenerations").textContent = hist.total || 0;
  } catch {}
}

async function updateProfile() {
  const name = document.getElementById("editName").value.trim();
  if (!name) return;
  const hint = document.getElementById("editHint");
  try {
    await apiFetch(`${API}/users/me`, { name }, "PATCH");
    state.user.name = name;
    document.getElementById("userDisplayName").textContent = name;
    document.getElementById("profileName").textContent = name;
    document.querySelectorAll(".user-avatar").forEach(el => el.textContent = name[0].toUpperCase());
    document.getElementById("profileAvatarLg").textContent = name[0].toUpperCase();
    hint.textContent = "✓ Profile updated";
    hint.style.color = "var(--success)";
  } catch (err) {
    hint.textContent = "Update failed: " + err.message;
    hint.style.color = "var(--error)";
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN
// ═══════════════════════════════════════════════════════════════════════════════

async function loadAdmin() {
  if (!state.user || state.user.role !== "admin") return;

  try {
    const stats = await apiFetch(`${API}/admin/stats`);
    document.getElementById("aStatUsers").textContent = stats.total_users;
    document.getElementById("aStatPoems").textContent = stats.total_poems;
    document.getElementById("aStatGens").textContent = stats.total_generations;
    document.getElementById("aStatDownloads").textContent = stats.total_downloads;
  } catch {}

  try {
    const logs = await apiFetch(`${API}/admin/logs`);
    const logList = document.getElementById("adminLogList");
    if (logs.length === 0) { logList.innerHTML = "<div class='empty-state' style='padding:20px'>No logs yet</div>"; return; }
    logList.innerHTML = logs.map(log => `
      <div class="admin-log-item">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="admin-log-action">${log.module} · ${log.action}</span>
          <span class="admin-log-time">${log.created_at ? new Date(log.created_at).toLocaleString() : ""}</span>
        </div>
        ${log.description ? `<div class="admin-log-desc">${log.description}</div>` : ""}
      </div>
    `).join("");
  } catch {}

  try {
    const users = await apiFetch(`${API}/admin/users`);
    const userList = document.getElementById("adminUserList");
    if (!users.items?.length) { userList.innerHTML = "<div class='empty-state' style='padding:20px'>No users yet</div>"; return; }
    userList.innerHTML = users.items.map(u => `
      <div class="admin-user-item">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div class="admin-user-name">${escapeHtml(u.name)}</div>
            <div class="admin-user-email">${escapeHtml(u.email)}</div>
          </div>
          <span class="admin-user-role role-${u.role}">${u.role}</span>
        </div>
      </div>
    `).join("");
  } catch {}
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

function escapeHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ═══════════════════════════════════════════════════════════════════════════════
// EVENT WIRING
// ═══════════════════════════════════════════════════════════════════════════════

// Character counter
document.getElementById("poemInput").addEventListener("input", function() {
  document.getElementById("charCounter").textContent = `${this.value.length} / 1200`;
});

// Font preview
document.getElementById("fontSelect").addEventListener("change", function() {
  state.font = this.value;
  document.getElementById("poemInput").style.fontFamily = this.value;
});

// Provider selector — show/hide SD options
document.getElementById("providerSelect").addEventListener("change", function() {
  document.getElementById("sdOptions").style.display = this.value === "stable-diffusion" ? "block" : "none";
});

// SD Options toggle
document.getElementById("sdOptionsToggle").addEventListener("click", () => {
  const body = document.getElementById("sdOptionsBody");
  const icon = document.getElementById("sdToggleIcon");
  const isOpen = body.style.display !== "none";
  body.style.display = isOpen ? "none" : "block";
  icon.textContent = isOpen ? "▼" : "▲";
});

// SD Style chips
document.querySelectorAll(".sd-chip").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sd-chip").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.sdStyle = btn.dataset.style;
  });
});

// SD Size buttons
document.querySelectorAll(".sd-size-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sd-size-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.sdWidth = parseInt(btn.dataset.w);
    state.sdHeight = parseInt(btn.dataset.h);
  });
});

// SD Sliders
document.getElementById("sdSteps").addEventListener("input", function() {
  state.sdSteps = parseInt(this.value);
  document.getElementById("stepsVal").textContent = this.value;
});
document.getElementById("sdGuidance").addEventListener("input", function() {
  state.sdGuidance = parseFloat(this.value);
  document.getElementById("guidanceVal").textContent = parseFloat(this.value).toFixed(1);
});
document.getElementById("sdSeed").addEventListener("input", function() {
  state.sdSeed = parseInt(this.value) || -1;
});

// SD Preload link
document.getElementById("sdPreloadLink").addEventListener("click", async () => {
  const link = document.getElementById("sdPreloadLink");
  link.textContent = "Loading..."; link.style.pointerEvents = "none";
  try {
    const res = await apiFetch(`${API}/sd-preload`, {});
    link.textContent = res.message || "Loading started!";
    pollSDStatus();
  } catch (e) {
    link.textContent = "Failed — check console";
  }
});

// Keyboard shortcut: Escape to close modal
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAuthModal();
});

// ═══════════════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  // Restore auth session
  if (state.token) {
    try {
      const me = await apiFetch(`${API}/auth/me`);
      state.user = { id: me.id, name: me.name, email: me.email, role: me.role };
    } catch {
      // Token expired or invalid
      state.token = null;
      localStorage.removeItem("pv_token");
    }
  }

  updateAuthUI();

  // Init SD status
  pollSDStatus();
  state.sdStatusInterval = setInterval(pollSDStatus, 5000);

  // Font select init
  const fontSelect = document.getElementById("fontSelect");
  fontSelect.value = state.font;
  document.getElementById("poemInput").style.fontFamily = state.font;

  // SD options visibility
  document.getElementById("sdOptions").style.display = "block";

  // Load gallery for initial tab
  loadGallery();
});
