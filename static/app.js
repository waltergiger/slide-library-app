/* Slide Library — client. Talks to the FastAPI backend in ../app/main.py.
 * No build step, no framework: one state object, a render() per view, and
 * a click-delegation dispatcher keyed by data-action attributes. */

(() => {
  "use strict";

  // ---------------------------------------------------------------- icons --
  const ICON = {
    search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg>`,
    minus: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>`,
    external: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3h7v7M21 3l-9 9M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>`,
    plus: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>`,
    chevronLeft: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>`,
    arrowRight: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>`,
    moon: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/></svg>`,
    sun: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`,
    folder: `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/></svg>`,
    dots: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="9" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="15" cy="18" r="1"/></svg>`,
    x: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>`,
    xSmall: `<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>`,
    check: `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>`,
    refresh: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7M21 3v6h-6"/></svg>`,
    trash: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0-1 14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1L5 6"/></svg>`,
    download: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0-4-4m4 4 4-4M4 19h16"/></svg>`,
    star: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 2.7 5.9 6.3.7-4.7 4.4 1.3 6.2L12 17.3 6.4 20.2l1.3-6.2-4.7-4.4 6.3-.7Z"/></svg>`,
    save: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>`,
    pencil: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`,
    layers: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 10 5-10 5L2 7Z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/></svg>`,
    starFill: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 2.7 5.9 6.3.7-4.7 4.4 1.3 6.2L12 17.3 6.4 20.2l1.3-6.2-4.7-4.4 6.3-.7Z"/></svg>`,
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- state --
  const BUILDER_KEY = "slidelib-builder";
  const THEME_KEY = "slidelib-theme";
  const PANEL_KEY = "slidelib-panel";
  const ZOOM_KEY = "slidelib-zoom";
  const PANEL_W_KEY = "slidelib-panel-width";

  const readPref = (key) => { try { return localStorage.getItem(key); } catch (e) { return null; } };
  const writePref = (key, value) => { try { localStorage.setItem(key, String(value)); } catch (e) { /* per-viewer convenience only */ } };

  // The Builder is auto-kept in localStorage as a working copy (survives a
  // reload); "Save" additionally stores it server-side as a named deck that
  // can be reopened from any browser. `dirty` = edits since the last Save.
  const emptyBuilder = () => ({ title: "", category: "", addDividers: true, chapters: [], draftId: null, dirty: false, savedAt: null });

  function loadBuilder() {
    try {
      const raw = localStorage.getItem(BUILDER_KEY);
      if (raw) {
        const b = { ...emptyBuilder(), ...JSON.parse(raw) };
        if (!b.draftId && b.title === "New Deck") b.title = ""; // old placeholder default, never named by the user
        return b;
      }
    } catch (e) { /* ignore corrupt storage */ }
    return emptyBuilder();
  }
  function saveBuilder(markDirty = true) {
    if (markDirty) state.builder.dirty = true;
    try { localStorage.setItem(BUILDER_KEY, JSON.stringify(state.builder)); } catch (e) { /* storage full/blocked */ }
    refreshSaveStatus();
  }

  const state = {
    view: "library",
    theme: (() => { try { return localStorage.getItem(THEME_KEY) || "dark"; } catch (e) { return "dark"; } })(),
    domains: [{ name: "All domains", count: 0 }],
    selectedDomain: "All domains",
    query: "",
    filters: { pptx: true, pdf: true, favoritesOnly: false },
    typesBeforeFavorites: null,
    decks: [],
    favSlides: [],
    currentDeck: null,
    slideSelection: new Set(),
    sources: [],
    showSourceForm: false,
    sourceForm: { path: "", domain: "" },
    browsing: false,
    builder: loadBuilder(),
    slideResults: [],
    panelOpen: readPref(PANEL_KEY) !== "closed",
    health: null,
    dismissLoBanner: false,
    zoom: ViewModel.normalizeZoom(readPref(ZOOM_KEY)),
    panelWidth: ViewModel.clampPanelWidth(readPref(PANEL_W_KEY), window.innerWidth),
    dragging: null,
    dropTarget: null,
    showDrafts: false,
    drafts: [],
    draftFilter: "all",
    editingDraft: null,
    saving: false,
    toast: null,
  };

  // ------------------------------------------------------------------ api --
  async function api(path, opts) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const err = new Error(body.detail || `Request failed (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return res.json();
  }

  async function refreshDomains() { state.domains = await api("/api/domains"); }
  // Favorites with no file type chosen lists the starred slides themselves;
  // choosing PPTX and/or PDF as well lists the decks that contain them.
  const favoriteSlidesMode = () => state.filters.favoritesOnly && !state.filters.pptx && !state.filters.pdf;

  async function refreshDecks() {
    const params = new URLSearchParams();
    if (state.selectedDomain && state.selectedDomain !== "All domains") params.set("domain", state.selectedDomain);
    if (state.query.trim()) params.set("q", state.query.trim());
    if (favoriteSlidesMode()) {
      state.favSlides = await api(`/api/favorites?${params}`);
      return;
    }
    if (state.filters.favoritesOnly) params.set("favorites_only", "true");
    const q = state.query.trim();
    // Slide-level hits are what you drag into the deck panel; decks alone can't be dragged.
    const [decks, slides] = await Promise.all([
      api(`/api/decks?${params}`),
      q && !state.filters.favoritesOnly ? api(`/api/search?q=${encodeURIComponent(q)}`) : [],
    ]);
    state.decks = decks;
    state.slideResults = state.selectedDomain === "All domains" ? slides : slides.filter((r) => r.domain === state.selectedDomain);
  }
  async function refreshDrafts() { state.drafts = await api("/api/drafts"); }
  async function refreshSources() { state.sources = await api("/api/sources"); }
  async function loadDeck(id) {
    state.currentDeck = await api(`/api/decks/${id}`);
    state.slideSelection = new Set();
  }

  let sourcesPollHandle = null;
  function ensureSourcesPolling() {
    const active = state.sources.some((s) => s.status === "indexing" || s.status === "pending");
    if (active && !sourcesPollHandle) {
      sourcesPollHandle = setInterval(async () => {
        await refreshSources();
        if (state.view === "sources") render();
        if (!state.sources.some((s) => s.status === "indexing" || s.status === "pending")) {
          clearInterval(sourcesPollHandle);
          sourcesPollHandle = null;
          await refreshDomains();
          await refreshDecks();
        }
      }, 1500);
    }
  }

  // ------------------------------------------------------------- helpers --
  function applyTheme() {
    document.body.setAttribute("data-theme", state.theme);
  }

  // The preferred panel width is kept as chosen; what is applied is clamped to
  // the current window, so shrinking the window never permanently shrinks the preference.
  const effectivePanelWidth = () => ViewModel.clampPanelWidth(state.panelWidth, window.innerWidth);

  function applyLayout() {
    const root = document.documentElement.style;
    root.setProperty("--zoom", String(state.zoom / 100));
    root.setProperty("--panel-w", effectivePanelWidth() + "px");
  }

  function setZoom(next) {
    state.zoom = next;
    writePref(ZOOM_KEY, next);
    render();
  }

  function zoomControl() {
    const atMin = state.zoom === ViewModel.ZOOM_STEPS[0];
    const atMax = state.zoom === ViewModel.ZOOM_STEPS[ViewModel.ZOOM_STEPS.length - 1];
    return `<div class="zoom-control" role="group" aria-label="Zoom slides">
      <button type="button" class="zoom-btn" data-action="zoomOut" aria-label="Zoom out" title="Zoom out" ${atMin ? "disabled" : ""}>${ICON.minus}</button>
      <button type="button" class="zoom-value" data-action="zoomReset" aria-label="Zoom ${state.zoom}%, click to reset to 100%" title="Reset to 100%">${state.zoom}%</button>
      <button type="button" class="zoom-btn" data-action="zoomIn" aria-label="Zoom in" title="Zoom in" ${atMax ? "disabled" : ""}>${ICON.plus}</button>
    </div>`;
  }

  // ---- panel splitter: drag with the mouse, arrow keys when focused, double-click resets.
  // Listeners live on `document` (not the handle) because render() replaces the handle element.
  let resizing = null;

  function setPanelWidth(width, persist) {
    state.panelWidth = ViewModel.clampPanelWidth(width, window.innerWidth);
    applyLayout();
    document.querySelectorAll("[data-resizer]").forEach((h) => h.setAttribute("aria-valuenow", String(effectivePanelWidth())));
    if (persist) writePref(PANEL_W_KEY, state.panelWidth);
  }

  document.addEventListener("pointerdown", (e) => {
    const handle = e.target.closest && e.target.closest("[data-resizer]");
    if (!handle || e.button > 0) return;
    e.preventDefault();
    resizing = { startX: e.clientX, startWidth: effectivePanelWidth() };
    document.body.classList.add("resizing");
    handle.classList.add("active");
  });
  document.addEventListener("pointermove", (e) => {
    if (resizing) setPanelWidth(resizing.startWidth + (resizing.startX - e.clientX), false); // panel is on the right: dragging left widens it
  });
  const endResize = () => {
    if (!resizing) return;
    resizing = null;
    document.body.classList.remove("resizing");
    document.querySelectorAll("[data-resizer].active").forEach((h) => h.classList.remove("active"));
    writePref(PANEL_W_KEY, state.panelWidth);
  };
  document.addEventListener("pointerup", endResize);
  document.addEventListener("pointercancel", endResize);
  document.addEventListener("dblclick", (e) => {
    if (e.target.closest && e.target.closest("[data-resizer]")) setPanelWidth(ViewModel.PANEL.def, true);
  });
  window.addEventListener("resize", applyLayout);
  function toggleTheme() {
    state.theme = state.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem(THEME_KEY, state.theme); } catch (e) { /* ignore */ }
    render();
  }
  function themeToggleButton(extraClass) {
    return `<button type="button" class="icon-btn ${extraClass || ""}" data-action="toggleTheme" aria-label="${state.theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}">${state.theme === "dark" ? ICON.sun : ICON.moon}</button>`;
  }
  function showToast(message, kind) {
    state.toast = { message, kind: kind || "ok" };
    render();
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => { state.toast = null; render(); }, 6000);
  }

  const appNameFor = (ext) => (ext === "pdf" ? "your PDF viewer" : "PowerPoint");

  // Full path + filename as a real link. The browser can't follow file:// from an
  // http page, so the click is intercepted and the local server opens the file.
  function fileLink(d) {
    const breakable = esc(d.path).replace(/([\/\\])/g, "$1<wbr>"); // let long paths wrap at separators
    return `<a href="${esc(ViewModel.fileUrl(d.path))}" class="file-link" data-action="openFile" data-id="${d.id}"
      title="Open in ${appNameFor(d.ext)}: ${esc(d.path)}" aria-label="Open ${esc(d.path)} in ${appNameFor(d.ext)}">${ICON.external}<span>${breakable}</span></a>`;
  }

  async function openFile(id) {
    try {
      const { path } = await api(`/api/decks/${id}/open`, { method: "POST" });
      const name = path.split(/[\\/]/).pop();
      showToast(`Opening ${name} in ${appNameFor(name.toLowerCase().endsWith(".pdf") ? "pdf" : "pptx")}…`);
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  function badgeFor(ext) { return ext === "pdf" ? { cls: "pdf", label: "PDF" } : { cls: "pptx", label: "PPT" }; }

  function findOrCreateChapter(name) {
    let ch = state.builder.chapters.find((c) => c.name === name);
    if (!ch) {
      ch = { id: newId(), name, slides: [] };
      state.builder.chapters.push(ch);
    }
    return ch;
  }

  const newId = () => "ch" + Date.now() + Math.random().toString(36).slice(2, 6);
  const categoriesOf = () => [...new Set(state.drafts.map((d) => d.category).filter(Boolean))].sort((a, b) => a.localeCompare(b));

  const slideRef = (slide) => ({
    file_id: slide.file_id,
    slide_index: slide.slide_index,
    title: slide.title,
    deck_title: slide.deck_title,
    thumb_url: slide.thumb_url,
  });

  function addSlideToChapter(chapterId, slide) {
    if (BuilderModel.insertSlide(state.builder.chapters, chapterId, Infinity, slideRef(slide))) saveBuilder();
  }

  const builderSlideCount = () => state.builder.chapters.reduce((n, c) => n + c.slides.length, 0);

  function builderStatus() {
    const b = state.builder;
    if (state.saving) return { cls: "", text: "Saving…" };
    if (b.draftId && !b.dirty) {
      const t = b.savedAt ? new Date(b.savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
      return { cls: "saved", text: `Saved${t ? " " + t : ""}` };
    }
    if (b.draftId) return { cls: "dirty", text: "Unsaved changes" };
    return { cls: builderSlideCount() ? "dirty" : "", text: "Not saved yet" };
  }
  // Updates the status chip in place — used while typing, where a full render() would steal input focus.
  function refreshSaveStatus() {
    const el = document.getElementById("saveStatus");
    if (!el) return;
    const st = builderStatus();
    el.className = "save-status " + st.cls;
    el.textContent = st.text;
  }

  let pendingFocus = null;
  let focusTarget = null; // "name" (deck name field) or "edit" (inline saved-deck editor)

  async function toggleFavoriteFor(fileId, slideIndex, nextValue) {
    try {
      await api(`/api/decks/${fileId}/slides/${slideIndex}/favorite`, {
        method: "POST",
        body: JSON.stringify({ favorite: nextValue }),
      });
    } catch (err) {
      showToast(String(err.message || err), "error");
      return;
    }
    if (state.currentDeck && state.currentDeck.id === fileId) {
      const s = state.currentDeck.slides.find((x) => x.index === slideIndex);
      if (s) s.favorite = nextValue;
    }
    state.slideResults.forEach((r) => { if (r.file_id === fileId && r.slide_index === slideIndex) r.favorite = nextValue; });
    if (!nextValue && state.filters.favoritesOnly && state.view === "library") {
      await refreshDecks();
    }
    render();
  }

  // -------------------------------------------------------------- render --
  function render() {
    applyTheme();
    applyLayout();
    const app = document.getElementById("app");
    if (state.view === "deck" && !state.currentDeck) { app.innerHTML = `<div style="padding:40px">Loading…</div>`; return; }
    let html;
    if (state.view === "library") html = renderLibrary();
    else if (state.view === "deck") html = renderDeck();
    else html = renderSources();
    const withDecks = state.view !== "sources";
    app.innerHTML = html
      + (withDecks ? `<datalist id="categoryOptions">${categoriesOf().map((c) => `<option value="${esc(c)}">`).join("")}</datalist>` : "")
      + (withDecks && state.showDrafts ? renderDraftsModal() : "")
      + renderToast();
    attachHandlers();
    if (pendingFocus) {
      const target = [...app.querySelectorAll(".chapter-slide")].find(
        (el) => el.dataset.chapter === pendingFocus.chapterId && Number(el.dataset.slideIndex) === pendingFocus.index);
      if (target) target.focus();
      pendingFocus = null;
    }
    if (focusTarget) {
      const el = focusTarget === "name" ? document.getElementById("deckName") : app.querySelector(".draft-row.editing input");
      if (el) { el.focus(); if (el.select) el.select(); }
      focusTarget = null;
    }
    const modal = app.querySelector(".modal");
    if (modal && !modal.contains(document.activeElement)) modal.focus();
  }

  function renderToast() {
    if (!state.toast) return "";
    return `<div class="toast ${state.toast.kind === "error" ? "error" : ""}">
      <span style="font-size:13px;line-height:1.4;">${esc(state.toast.message)}</span>
      <button type="button" data-action="dismissToast" aria-label="Dismiss" style="opacity:0.75;">${ICON.x}</button>
    </div>`;
  }

  const panelToggleButton = () => {
    const n = builderSlideCount();
    return `<button type="button" class="btn ${state.panelOpen ? "btn-secondary" : "btn-primary"}" data-action="togglePanel" aria-pressed="${state.panelOpen}">
      ${ICON.layers} ${state.panelOpen ? "Hide deck" : "New deck"}${!state.panelOpen && n ? `<span class="btn-badge">${n}</span>` : ""}
    </button>`;
  };

  function renderLibrary() {
    const domainsHtml = state.domains.map((d) => {
      const active = d.name === state.selectedDomain;
      return `<button type="button" class="nav-item ${active ? "active" : ""}" data-action="selectDomain" data-value="${esc(d.name)}">
        <span class="left">${ICON.folder}${esc(d.name)}</span>
        <span class="nav-count">${d.count}</span>
      </button>`;
    }).join("");

    if (favoriteSlidesMode()) return renderLibraryShell(domainsHtml, renderFavoriteSlides());

    const typeVisible = (ext) => (ext === "pdf" ? state.filters.pdf : state.filters.pptx);
    const noTypeSelected = !state.filters.pptx && !state.filters.pdf;
    const visibleDecks = noTypeSelected ? [] : state.decks.filter((d) => typeVisible(d.ext));

    const decksHtml = visibleDecks.map((d) => {
      const b = badgeFor(d.ext);
      return `<div class="deck-card" data-action="openDeck" data-id="${d.id}" role="link" tabindex="0" aria-label="Open deck ${esc(d.title)}">
        <div class="deck-card-top">
          <div class="badge ${b.cls}">${b.label}</div>
          <span class="tag">${esc(d.domain)}</span>
        </div>
        <div class="deck-title">${esc(d.title)}</div>
        <div class="deck-meta">${d.slide_count} slides</div>
        ${fileLink(d)}
      </div>`;
    }).join("");

    const emptyMessage = noTypeSelected
      ? "No file type selected — turn on PPTX or PDF above to see decks."
      : (state.filters.favoritesOnly
          ? "No favorited slides match these filters yet — star a few slides in a deck first."
          : (state.query ? `No decks match "${esc(state.query)}".` : "No decks indexed yet — add a source directory to get started."));

    const decksBody = visibleDecks.length
      ? `<div class="deck-grid">${decksHtml}</div>`
      : `<div class="empty-state">${ICON.search}<span style="font-size:14.5px;">${state.decks === null ? "Loading…" : emptyMessage}</span></div>`;

    // Slide-level hits for a text search: these are what can be dragged into the deck panel.
    const slidesSection = state.slideResults.length && !noTypeSelected
      ? renderSlideGroup("Matching slides", state.slideResults.filter((r) => typeVisible(r.ext))) : "";
    const body = slidesSection ? `${slidesSection}<div class="fav-group-head" style="margin-top:8px;"><span class="tag">Decks</span></div>${decksBody}` : decksBody;

    return renderLibraryShell(domainsHtml, body, visibleDecks.length);
  }

  function filterRow() {
    const filterChip = (key, label, iconHtml) => `<label class="filter-chip ${state.filters[key] ? "active" : ""}">
      <input type="checkbox" data-bind="filter-${key}" ${state.filters[key] ? "checked" : ""}>
      ${iconHtml || ""}${label}
    </label>`;
    return `<div class="filter-row">
      ${filterChip("pptx", "PPTX")}
      ${filterChip("pdf", "PDF")}
      ${filterChip("favoritesOnly", "Favorites", ICON.starFill)}
    </div>`;
  }

  // One draggable slide thumbnail, used for favorites and for search hits.
  function renderSlideTile(f) {
    const b = badgeFor(f.ext);
    const payload = { file_id: f.file_id, slide_index: f.slide_index, title: f.title, deck_title: f.deck_title, thumb_url: f.thumb_url };
    return `<div class="fav-tile">
      <div class="slide-card" draggable="true" data-drag="source" data-slide="${esc(JSON.stringify(payload))}" data-action="openDeck" data-id="${f.file_id}" role="button" tabindex="0" aria-label="${esc(f.title)}, from ${esc(f.deck_title)}, slide ${f.slide_index + 1}. Drag into the deck panel to add.">
        ${f.thumb_url ? `<img src="${esc(f.thumb_url)}" alt="" draggable="false">` : `<div class="title">${esc(f.title)}</div>`}
        <button type="button" class="star-btn ${f.favorite ? "active" : ""}" data-action="toggleFavorite" data-file-id="${f.file_id}" data-index="${f.slide_index}" data-favorite="${f.favorite ? "1" : "0"}" aria-label="${f.favorite ? "Remove from favorites" : "Mark as favorite"}" aria-pressed="${!!f.favorite}">${f.favorite ? ICON.starFill : ICON.star}</button>
        <div class="slide-index">${f.slide_index + 1}</div>
      </div>
      <div class="fav-caption"><div class="t">${esc(f.title)}</div><div class="d"><span class="badge-mini ${b.cls}">${b.label}</span>${esc(f.deck_title)}</div></div>
    </div>`;
  }

  function renderSlideGroup(label, items) {
    return `<section class="fav-group">
      <div class="fav-group-head"><span class="tag">${esc(label)}</span><span class="count">${items.length} slide${items.length === 1 ? "" : "s"}</span></div>
      <div class="fav-grid">${items.map(renderSlideTile).join("")}</div>
    </section>`;
  }

  function renderFavoriteSlides() {
    const slides = state.favSlides;
    if (!slides.length) {
      const msg = state.query ? `No favorite slides match "${esc(state.query)}".` : "No favorite slides yet — star a few slides in a deck first.";
      return { count: 0, unit: "slide", html: `<div class="empty-state">${ICON.starFill}<span style="font-size:14.5px;">${msg}</span></div>` };
    }
    const groups = new Map();
    slides.forEach((f) => { if (!groups.has(f.domain)) groups.set(f.domain, []); groups.get(f.domain).push(f); });
    const html = [...groups].map(([domain, items]) => renderSlideGroup(domain, items)).join("");
    return { count: slides.length, unit: "slide", html };
  }

  function renderLibraryShell(domainsHtml, body, deckCount) {
    // Favorites-slide mode passes {count, unit, html}; deck mode passes html + deck count.
    const { count, unit, html } = typeof body === "string" ? { count: deckCount, unit: "deck", html: body } : body;
    return `<div class="shell">
      <div class="sidebar">
        <div>
          <div class="brand"><div class="brand-mark">S</div><span class="brand-name">Slide Library</span></div>
          <div class="brand-caption">Presentation repository</div>
        </div>
        <div>
          <div class="nav-label">Domains</div>
          ${domainsHtml}
        </div>
        <div class="sidebar-bottom">
          <div class="divider"></div>
          <a href="#" class="link-row" data-action="openSavedDecks">${ICON.folder} Saved decks</a>
          <a href="#" class="link-row" data-action="goto" data-view="sources">${ICON.plus} Manage sources</a>
        </div>
      </div>
      <div class="main">
        ${state.health && !state.health.libreoffice && !state.dismissLoBanner ? `<div class="banner warn" role="alert">
          <div><strong>LibreOffice not found.</strong> Slides are indexed without thumbnails and export can't use its image fallback.
          Install LibreOffice from libreoffice.org (or point SLIDELIB_SOFFICE at its <em>soffice</em> executable), then re-index your sources.</div>
          <button type="button" class="icon-btn sm" data-action="dismissLoBanner" aria-label="Dismiss warning">${ICON.x}</button>
        </div>` : ""}
        <div class="top-row">
          <div class="search-wrap" style="flex-grow:1;max-width:420px;">
            ${ICON.search.replace("<svg", '<svg class="search-icon"')}
            <label for="librarySearch" class="sr-only">Search the library</label>
            <input id="librarySearch" class="input" type="text" placeholder="Search decks, slides, or text inside slides…" value="${esc(state.query)}" data-bind="query">
          </div>
          <div class="actions">
            ${zoomControl()}
            ${themeToggleButton()}
            ${panelToggleButton()}
          </div>
        </div>
        ${filterRow()}
        <div class="heading-row"><h1>${esc(state.selectedDomain)}</h1><span class="count">${count} ${unit}${count === 1 ? "" : "s"}</span></div>
        ${html}
      </div>
      ${renderDeckPanel()}
    </div>`;
  }

  function renderDeck() {
    const deck = state.currentDeck;
    const b = badgeFor(deck.ext);
    const slidesHtml = deck.slides.map((s) => {
      const selected = state.slideSelection.has(s.index);
      const payload = { file_id: deck.id, slide_index: s.index, title: s.title, deck_title: deck.title, thumb_url: s.thumb_url };
      return `<div class="slide-card ${selected ? "selected" : ""}" draggable="true" data-drag="source" data-slide="${esc(JSON.stringify(payload))}" data-action="toggleSlide" data-index="${s.index}" role="button" tabindex="0" aria-pressed="${selected}" aria-label="${esc(s.title)}, slide ${s.index + 1}">
        ${s.thumb_url
          ? `<img src="${esc(s.thumb_url)}" alt="" draggable="false">`
          : `<div class="title">${esc(s.title)}</div>`}
        <button type="button" class="star-btn ${s.favorite ? "active" : ""}" data-action="toggleFavorite" data-file-id="${deck.id}" data-index="${s.index}" data-favorite="${s.favorite ? "1" : "0"}" aria-label="${s.favorite ? "Remove from favorites" : "Mark as favorite"}" aria-pressed="${!!s.favorite}">${s.favorite ? ICON.starFill : ICON.star}</button>
        <div class="slide-indicator">${selected ? ICON.check : ""}</div>
        <div class="slide-index">${s.index + 1}</div>
      </div>`;
    }).join("");

    const count = state.slideSelection.size;
    const bar = count > 0 ? `<div class="floating-bar" ${state.panelOpen ? `style="left:calc((100% - var(--panel-w)) / 2)"` : ""}>
      <span style="font-size:13.5px;font-weight:500;">${count} slide${count === 1 ? "" : "s"} selected — click to select, drag any into the deck</span>
      <button type="button" class="go-btn" data-action="addSelectionToBuilder">Add to deck ${ICON.arrowRight}</button>
    </div>` : "";

    return `<div class="shell">
      <div class="stage">
        <div style="padding:24px 32px 0;">
          <a href="#" class="back-link" data-action="goto" data-view="library">${ICON.chevronLeft} Back to library</a>
          <div class="deck-header">
            <div class="left">
              <div class="deck-icon badge-${b.cls}" style="background:${b.cls === "pdf" ? "var(--pdf-badge)" : "var(--pptx-badge)"};">${b.label}</div>
              <div>
                <h1 style="margin:0 0 4px;font-size:21px;font-weight:700;">${esc(deck.title)}</h1>
                <div style="font-size:13px;color:var(--text-secondary);">${deck.slide_count} slides · ${deck.ext.toUpperCase()} · ${esc(deck.domain)}</div>
                <div style="margin-top:6px;">${fileLink(deck)}</div>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end;">
              ${zoomControl()}
              ${themeToggleButton()}
              <button type="button" class="btn btn-secondary" data-action="openFile" data-id="${deck.id}">${ICON.external} Open ${deck.ext === "pdf" ? "PDF" : "in PowerPoint"}</button>
              <button type="button" class="btn btn-secondary" data-action="addAllToBuilder">Add all ${deck.slide_count} to deck</button>
              ${panelToggleButton()}
            </div>
          </div>
          <div class="divider" style="margin-top:20px;"></div>
        </div>
        <div style="padding:20px 32px 110px;">
          <div class="slide-grid">${slidesHtml}</div>
        </div>
      </div>
      ${renderDeckPanel()}
    </div>
    ${bar}`;
  }

  // The right-hand "new deck": always next to the library so slides can be dragged straight in.
  function renderDeckPanel() {
    if (!state.panelOpen) return "";
    const bld = state.builder;
    const st = builderStatus();
    const totalSlides = builderSlideCount();

    const chaptersHtml = bld.chapters.map((ch) => {
      const slidesHtml = ch.slides.map((s, i) => `
        <div class="chapter-slide ${s.missing ? "is-missing" : ""}" draggable="true" data-drag="slide" data-chapter="${ch.id}" data-slide-index="${i}" tabindex="0"
             title="${esc(s.missing ? "No longer in the library: " + s.title : s.title)}"
             aria-label="${esc(s.title)}, slide ${i + 1} of ${ch.slides.length} in ${esc(ch.name)}${s.missing ? ", missing from library" : ""}. Alt plus arrow keys moves it.">
          <div class="thumb">${s.missing ? `<span class="missing-label">Missing</span>` : (s.thumb_url ? `<img src="${esc(s.thumb_url)}" alt="" draggable="false">` : "")}</div>
          <button type="button" class="remove" data-action="removeChapterSlide" data-chapter="${ch.id}" data-slide-index="${i}" aria-label="Remove slide">${ICON.xSmall}</button>
          <div class="t">${esc(s.title)}</div>
        </div>`).join("");
      return `<div class="chapter" data-drop="chapter" data-chapter="${ch.id}">
        <div class="chapter-head">
          <div class="left">
            <span class="chapter-grip" draggable="true" data-drag="chapter" data-chapter="${ch.id}" title="Drag to reorder chapter">${ICON.dots}</span>
            <input class="chapter-name" value="${esc(ch.name)}" data-bind="chapterName" data-chapter="${ch.id}" aria-label="Chapter name" style="width:${Math.max(6, ch.name.length)}ch">
            <span class="chapter-count">${ch.slides.length}</span>
          </div>
          <button type="button" aria-label="Remove chapter" style="color:var(--text-tertiary);padding:4px;" data-action="removeChapter" data-chapter="${ch.id}">${ICON.x}</button>
        </div>
        ${ch.slides.length ? `<div class="chapter-slides">${slidesHtml}</div>` : `<div class="chapter-empty">Drag slides here</div>`}
      </div>`;
    }).join("");

    const vw = window.innerWidth;
    return `<aside class="deck-panel" aria-label="New deck">
      <div class="panel-resizer" data-resizer role="separator" aria-orientation="vertical" tabindex="0"
           aria-label="Resize deck panel (drag, or use arrow keys; double-click to reset)"
           aria-valuemin="${ViewModel.PANEL.min}" aria-valuemax="${ViewModel.maxPanelWidth(vw)}" aria-valuenow="${effectivePanelWidth()}"></div>
      <div class="deck-panel-head">
        <div class="panel-title-row">
          <span class="nav-label" style="padding:0;">New deck</span>
          <button type="button" class="icon-btn sm" data-action="togglePanel" aria-label="Hide deck panel">${ICON.x}</button>
        </div>
        <input id="deckName" class="input deck-name" value="${esc(bld.title)}" data-bind="deckName" placeholder="Name your deck…" aria-label="Deck name" maxlength="200">
        <input class="input input-sm" list="categoryOptions" value="${esc(bld.category)}" data-bind="deckCategory" placeholder="Category (optional)" aria-label="Deck category" maxlength="60">
        <div class="panel-status">
          <span id="saveStatus" class="save-status ${st.cls}">${st.text}</span> ·
          ${bld.chapters.length} chapter${bld.chapters.length === 1 ? "" : "s"} · ${totalSlides} slide${totalSlides === 1 ? "" : "s"}
        </div>
        <div class="panel-actions">
          <button type="button" class="btn btn-primary btn-sm" data-action="saveDraft" ${state.saving ? "disabled" : ""}>${ICON.save} Save</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="exportDeck">${ICON.download} Export .pptx</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="openSavedDecks">${ICON.folder} Open saved</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="newDeck">${ICON.plus} New</button>
        </div>
        <label class="panel-check"><input type="checkbox" data-bind="addDividers" ${bld.addDividers ? "checked" : ""}> Add a divider slide per chapter</label>
      </div>
      <div class="deck-panel-body">
        ${chaptersHtml}
        <div class="new-chapter-drop" data-drop="newChapter">
          ${ICON.plus}<span>${bld.chapters.length ? "Drop slides here for a new chapter" : "Drag slides here to start your deck"}</span>
        </div>
        <div class="new-chapter-row">
          <input class="input input-sm" type="text" placeholder="New chapter name…" data-bind="newChapterName" aria-label="New chapter name">
          <button type="button" class="btn btn-secondary btn-sm" data-action="addChapter">${ICON.plus} Add</button>
        </div>
        ${totalSlides ? `<div class="panel-hint">Drag to reorder or move between chapters · Alt + arrow keys on a focused slide</div>` : ""}
      </div>
    </aside>`;
  }

  const draftFilterKey = (d) => (d.category ? "cat:" + d.category : "none");

  function renderDraftsModal() {
    const cats = categoriesOf();
    const uncategorized = state.drafts.filter((d) => !d.category).length;
    let filter = state.draftFilter;
    if (filter.startsWith("cat:") && !cats.includes(filter.slice(4))) filter = "all";
    if (filter === "none" && !uncategorized) filter = "all";

    const chip = (key, label, n) => `<button type="button" class="filter-chip ${filter === key ? "active" : ""}" data-action="filterDrafts" data-value="${esc(key)}">${esc(label)}<span class="chip-count">${n}</span></button>`;
    const chips = cats.length
      ? `<div class="filter-row modal-chips">${chip("all", "All", state.drafts.length)}${cats.map((c) => chip("cat:" + c, c, state.drafts.filter((d) => d.category === c).length)).join("")}${uncategorized ? chip("none", "Uncategorized", uncategorized) : ""}</div>`
      : "";

    const row = (d) => {
      const editing = state.editingDraft && state.editingDraft.id === d.id;
      if (editing) {
        return `<div class="draft-row editing">
          <div class="body edit-fields">
            <input class="input input-sm" value="${esc(state.editingDraft.name)}" data-bind="draftEditName" placeholder="Deck name" aria-label="Deck name" maxlength="200">
            <input class="input input-sm" list="categoryOptions" value="${esc(state.editingDraft.category)}" data-bind="draftEditCategory" placeholder="Category (optional)" aria-label="Category" maxlength="60">
          </div>
          <button type="button" class="btn btn-primary btn-sm" data-action="saveDraftMeta">Save</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="cancelEditDraft">Cancel</button>
        </div>`;
      }
      return `<div class="draft-row ${d.id === state.builder.draftId ? "current" : ""}">
        <div class="body">
          <div class="name">${esc(d.name)}${d.id === state.builder.draftId ? ` <span class="tag">Open now</span>` : ""}</div>
          <div class="meta">${d.chapter_count} chapter${d.chapter_count === 1 ? "" : "s"} · ${d.slide_count} slide${d.slide_count === 1 ? "" : "s"} · Updated ${new Date(d.updated_at).toLocaleString()}</div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" data-action="openDraft" data-id="${d.id}">Open</button>
        <button type="button" class="icon-btn sm" data-action="editDraft" data-id="${d.id}" aria-label="Rename or change category of ${esc(d.name)}">${ICON.pencil}</button>
        <button type="button" class="icon-btn sm" data-action="deleteDraft" data-id="${d.id}" aria-label="Delete saved deck ${esc(d.name)}" style="color:var(--red-text);">${ICON.trash}</button>
      </div>`;
    };

    let list;
    if (filter === "all" && cats.length) {
      const group = (label, items) => items.length ? `<div class="draft-group"><div class="draft-group-head">${esc(label)}<span class="count">${items.length}</span></div>${items.map(row).join("")}</div>` : "";
      list = cats.map((c) => group(c, state.drafts.filter((d) => d.category === c))).join("") + group("Uncategorized", state.drafts.filter((d) => !d.category));
    } else {
      const shown = state.drafts.filter((d) => filter === "all" || draftFilterKey(d) === filter);
      list = shown.map(row).join("");
    }

    return `<div class="modal-backdrop" data-action="closeDrafts">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Saved decks" tabindex="-1">
        <div class="modal-head"><h2>Saved decks</h2><button type="button" class="icon-btn sm" data-action="closeDrafts" aria-label="Close">${ICON.x}</button></div>
        ${chips}
        <div class="modal-body">${list || `<div class="footnote">No saved decks yet — name your deck in the panel and press Save.</div>`}</div>
      </div>
    </div>`;
  }

  function renderSources() {
    const rowsHtml = state.sources.map((s) => {
      let chip, statsLine;
      if (s.status === "indexed") {
        chip = `<span class="chip green">Indexed</span>`;
        statsLine = `Updated ${s.last_indexed_at ? new Date(s.last_indexed_at).toLocaleString() : "—"}`;
      } else if (s.status === "indexing" || s.status === "pending") {
        const pct = s.files_total ? Math.round((s.files_done / s.files_total) * 100) : 0;
        chip = `<span class="chip amber">Indexing ${pct}%</span>`;
        statsLine = `${s.files_done} of ${s.files_total || "?"} files`;
      } else {
        chip = `<span class="chip red">Needs attention</span>`;
        statsLine = esc(s.error_message || "Unknown error");
      }
      const progress = s.files_total ? Math.round((s.files_done / s.files_total) * 100) : 0;
      return `<div class="source-row">
        <div class="folder-icon">${ICON.folder}</div>
        <div class="body">
          <div class="path">${esc(s.path)}</div>
          <div class="meta-line">
            <span class="tag">${esc(s.domain)}</span>
            ${chip}
            <span style="font-size:12px;color:var(--text-secondary);">${statsLine}</span>
          </div>
          ${(s.status === "indexing" || s.status === "pending") ? `<div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div>` : ""}
        </div>
        <div class="row-actions">
          <button type="button" class="btn btn-secondary btn-sm" data-action="reindexSource" data-id="${s.id}">${ICON.refresh} Re-index</button>
          <button type="button" class="icon-btn sm" data-action="deleteSource" data-id="${s.id}" aria-label="Remove directory" style="color:var(--red-text);">${ICON.trash}</button>
        </div>
      </div>`;
    }).join("");

    const indexedCount = state.sources.filter((s) => s.status === "indexed").length;

    const form = state.showSourceForm ? `<div class="source-form">
      <div style="font-size:13.5px;font-weight:600;">New source directory</div>
      <div class="fields">
        <div class="field" style="flex-grow:1;">
          <label for="srcPath">Folder path</label>
          <div style="display:flex;gap:8px;">
            <input id="srcPath" class="input" type="text" placeholder="/Volumes/Share/Strategy or \\\\fileshare\\Strategy" value="${esc(state.sourceForm.path)}" data-bind="sourcePath" style="flex-grow:1;">
            <button type="button" class="btn btn-secondary btn-sm" data-action="browseFolder" style="flex-shrink:0;" ${state.browsing ? "disabled" : ""}>${ICON.folder} ${state.browsing ? "Waiting…" : "Browse…"}</button>
          </div>
        </div>
        <div class="field" style="width:240px;flex-shrink:0;">
          <label for="srcDomain">Domain</label>
          <input id="srcDomain" class="input" type="text" list="domainOptions" placeholder="Strategy, Architecture…" value="${esc(state.sourceForm.domain)}" data-bind="sourceDomain">
          <datalist id="domainOptions">${state.domains.filter((d) => d.name !== "All domains").map((d) => `<option value="${esc(d.name)}">`).join("")}</datalist>
        </div>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;">
        <button type="button" class="btn btn-secondary btn-sm" data-action="toggleSourceForm">Cancel</button>
        <button type="button" class="btn btn-primary btn-sm" data-action="submitSource">Start indexing</button>
      </div>
    </div>` : "";

    return `<div class="sources-header">
      <a href="#" class="back-link" data-action="goto" data-view="library">${ICON.chevronLeft} Back to library</a>
      <div class="row">
        <div>
          <h1 style="margin:0 0 4px;font-size:21px;font-weight:700;">Manage source directories</h1>
          <span style="font-size:13px;color:var(--text-secondary);">${state.sources.length} directories · ${indexedCount} indexed</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${themeToggleButton()}
          <button type="button" class="btn btn-primary" data-action="toggleSourceForm">${ICON.plus} Add directory</button>
        </div>
      </div>
    </div>
    <div class="sources-list">
      ${form}
      ${rowsHtml || `<div class="footnote">No source directories yet. Add one to start indexing your PowerPoint and PDF decks.</div>`}
      <div class="footnote">The index rebuilds only for files that changed since the last run. Use re-index any time after adding or editing files on disk.</div>
    </div>`;
  }

  // ---------------------------------------------------------- interaction --
  function attachHandlers() {
    const app = document.getElementById("app");

    app.querySelectorAll("[data-bind]").forEach((el) => {
      const bind = el.dataset.bind;
      const evt = el.tagName === "SELECT" || el.type === "checkbox" ? "change" : "input";
      el.addEventListener(evt, (e) => onBind(bind, e, el));
      if (evt === "input") el.addEventListener("keydown", (e) => { if (e.key === "Enter") el.blur(); });
    });

    app.querySelectorAll("[data-drag]").forEach((el) => {
      el.addEventListener("dragstart", (e) => onDragStart(e, el));
      el.addEventListener("dragend", onDragEnd);
    });
    app.querySelectorAll('[data-drop="chapter"]').forEach((el) => {
      el.addEventListener("dragover", (e) => onDragOver(e, el));
      el.addEventListener("dragleave", (e) => { if (!el.contains(e.relatedTarget)) { clearDropIndicators(); state.dropTarget = null; } });
      el.addEventListener("drop", (e) => { e.preventDefault(); applyDrop(); });
    });
    app.querySelectorAll('[data-drop="newChapter"]').forEach((el) => {
      el.addEventListener("dragover", (e) => {
        if (!state.dragging || state.dragging.kind !== "source") return;
        e.preventDefault();
        clearDropIndicators();
        el.classList.add("drag-over");
        state.dropTarget = { kind: "newChapter" };
      });
      el.addEventListener("dragleave", (e) => { if (!el.contains(e.relatedTarget)) { el.classList.remove("drag-over"); state.dropTarget = null; } });
      el.addEventListener("drop", (e) => { e.preventDefault(); applyDrop(); });
    });
  }

  // ------------------------------------------------------- drag and drop --
  // Dragging never re-renders (that would cancel the drag): indicators are
  // toggled as CSS classes, the drop target is remembered in state.dropTarget
  // and the model change + render happen once, on drop.
  function onDragStart(e, el) {
    const kind = el.dataset.drag;
    if (kind === "source") {
      const slides = sourceSlidesFor(el);
      state.dragging = { kind, slides, fromSelection: slides.length > 1 };
    }
    else if (kind === "slide") state.dragging = { kind, chapterId: el.dataset.chapter, index: Number(el.dataset.slideIndex) };
    else state.dragging = { kind: "chapter", chapterId: el.dataset.chapter };
    e.dataTransfer.effectAllowed = kind === "source" ? "copy" : "move";
    e.dataTransfer.setData("text/plain", "slide-library"); // Firefox won't start a drag without data
    const visual = kind === "chapter" ? el.closest(".chapter") : el;
    if (kind === "chapter") e.dataTransfer.setDragImage(visual, 16, 16);
    setTimeout(() => visual.classList.add("dragging"), 0); // after the drag image is captured
  }

  // Dragging one of several selected slides in a deck view drags the whole selection, in deck order.
  function sourceSlidesFor(el) {
    const one = JSON.parse(el.dataset.slide);
    const deck = state.currentDeck;
    if (state.view === "deck" && deck && one.file_id === deck.id && state.slideSelection.size > 1 && state.slideSelection.has(one.slide_index)) {
      return deck.slides.filter((sl) => state.slideSelection.has(sl.index))
        .map((sl) => ({ file_id: deck.id, slide_index: sl.index, title: sl.title, deck_title: deck.title, thumb_url: sl.thumb_url }));
    }
    return [one];
  }

  function onDragEnd() {
    state.dragging = null;
    state.dropTarget = null;
    clearDropIndicators();
    document.querySelectorAll(".dragging").forEach((n) => n.classList.remove("dragging"));
  }

  function clearDropIndicators() {
    document.querySelectorAll(".drop-before, .drop-after, .drag-over").forEach((n) => n.classList.remove("drop-before", "drop-after", "drag-over"));
  }

  function onDragOver(e, chapterEl) {
    const d = state.dragging;
    if (!d) return;
    e.preventDefault();
    clearDropIndicators();
    const chapters = state.builder.chapters;
    const chapterId = chapterEl.dataset.chapter;

    if (d.kind === "chapter") {
      const r = chapterEl.getBoundingClientRect();
      const after = e.clientY > r.top + r.height / 2;
      state.dropTarget = { kind: "chapter", slot: chapters.findIndex((c) => c.id === chapterId) + (after ? 1 : 0) };
      chapterEl.classList.add(after ? "drop-after" : "drop-before");
      return;
    }

    const slideEl = e.target.closest ? e.target.closest(".chapter-slide") : null;
    if (slideEl && chapterEl.contains(slideEl)) {
      const r = slideEl.getBoundingClientRect();
      const after = e.clientX > r.left + r.width / 2;
      state.dropTarget = { kind: "slide", chapterId, slot: Number(slideEl.dataset.slideIndex) + (after ? 1 : 0) };
      slideEl.classList.add(after ? "drop-after" : "drop-before");
    } else {
      const ch = chapters.find((c) => c.id === chapterId);
      state.dropTarget = { kind: "slide", chapterId, slot: ch ? ch.slides.length : 0 };
      chapterEl.classList.add("drag-over");
    }
  }

  function applyDrop() {
    const d = state.dragging;
    const t = state.dropTarget;
    state.dragging = null;
    state.dropTarget = null;
    if (!d || !t) { render(); return; }
    const chapters = state.builder.chapters;
    let changed = false;
    if (d.kind === "chapter" && t.kind === "chapter") {
      changed = BuilderModel.moveChapter(chapters, d.chapterId, t.slot);
    } else if (d.kind === "slide" && t.kind === "slide") {
      pendingFocus = BuilderModel.moveSlide(chapters, { chapterId: d.chapterId, index: d.index }, { chapterId: t.chapterId, slot: t.slot });
      changed = !!pendingFocus;
    } else if (d.kind === "source" && t.kind === "slide") {
      const pos = BuilderModel.insertSlides(chapters, t.chapterId, t.slot, d.slides.map(slideRef));
      changed = !!pos;
      pendingFocus = pos;
    } else if (d.kind === "source" && t.kind === "newChapter") {
      const chapter = { id: newId(), name: d.slides[0].deck_title || "New chapter", slides: [] };
      chapters.push(chapter);
      BuilderModel.insertSlides(chapters, chapter.id, 0, d.slides.map(slideRef));
      changed = true;
    }
    if (changed) saveBuilder();
    if (changed && d.fromSelection) state.slideSelection = new Set(); // those slides are in the deck now
    render();
  }

  function onBind(name, e, el) {
    const v = el.type === "checkbox" ? el.checked : el.value;
    if (name === "query") { state.query = v; debounce("decks", () => { refreshDecks().then(render); }); }
    else if (name === "deckName") { state.builder.title = v; saveBuilder(); }
    else if (name === "deckCategory") { state.builder.category = v; saveBuilder(); }
    else if (name === "draftEditName") { state.editingDraft.name = v; }
    else if (name === "draftEditCategory") { state.editingDraft.category = v; }
    else if (name === "addDividers") { state.builder.addDividers = v; saveBuilder(); }
    else if (name === "newChapterName") { state._newChapterName = v; }
    else if (name === "chapterName") {
      const ch = state.builder.chapters.find((c) => c.id === el.dataset.chapter);
      if (ch) { ch.name = v; saveBuilder(); }
    } else if (name === "sourcePath") { state.sourceForm.path = v; }
    else if (name === "sourceDomain") { state.sourceForm.domain = v; }
    else if (name.startsWith("filter-")) {
      const key = name.slice("filter-".length);
      state.filters[key] = v;
      if (key === "favoritesOnly") {
        if (v) {
          state.typesBeforeFavorites = { pptx: state.filters.pptx, pdf: state.filters.pdf };
          state.filters.pptx = state.filters.pdf = false;
        } else if (!state.filters.pptx && !state.filters.pdf) {
          Object.assign(state.filters, state.typesBeforeFavorites || { pptx: true, pdf: true });
        }
      }
      refreshDecks().then(render);
    }
  }

  const debounceTimers = {};
  function debounce(key, fn, ms) {
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(fn, ms || 250);
  }

  document.addEventListener("click", async (e) => {
    const el = e.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    e.preventDefault();

    if (action === "toggleTheme") return toggleTheme();
    if (action === "dismissToast") { state.toast = null; return render(); }

    if (action === "goto") {
      state.view = el.dataset.view;
      if (state.view === "library") { await Promise.all([refreshDomains(), refreshDecks()]); }
      if (state.view === "sources") { await refreshSources(); ensureSourcesPolling(); }
      return render();
    }

    if (action === "selectDomain") {
      state.selectedDomain = el.dataset.value;
      await refreshDecks();
      return render();
    }

    if (action === "openDeck") {
      state.view = "deck";
      render();
      try { await loadDeck(el.dataset.id); } catch (err) { showToast(String(err.message || err), "error"); }
      return render();
    }

    if (action === "toggleSlide") {
      const idx = Number(el.dataset.index);
      if (state.slideSelection.has(idx)) state.slideSelection.delete(idx); else state.slideSelection.add(idx);
      return render();
    }

    if (action === "toggleFavorite") {
      const fileId = Number(el.dataset.fileId);
      const idx = Number(el.dataset.index);
      const next = el.dataset.favorite !== "1";
      return toggleFavoriteFor(fileId, idx, next);
    }

    if (action === "addSelectionToBuilder" || action === "addAllToBuilder") {
      const deck = state.currentDeck;
      const indices = action === "addAllToBuilder" ? deck.slides.map((s) => s.index) : Array.from(state.slideSelection);
      const ch = findOrCreateChapter(deck.title);
      indices.forEach((idx) => {
        const s = deck.slides.find((x) => x.index === idx);
        addSlideToChapter(ch.id, { file_id: deck.id, slide_index: idx, title: s.title, deck_title: deck.title, thumb_url: s.thumb_url });
      });
      state.slideSelection = new Set();
      state.panelOpen = true;
      showToast(`Added ${indices.length} slide${indices.length === 1 ? "" : "s"} to “${ch.name}”.`);
      return;
    }

    if (action === "addChapter") {
      const name = (state._newChapterName || "").trim() || "New chapter";
      state.builder.chapters.push({ id: newId(), name, slides: [] });
      state._newChapterName = "";
      saveBuilder();
      return render();
    }

    if (action === "removeChapter") {
      state.builder.chapters = state.builder.chapters.filter((c) => c.id !== el.dataset.chapter);
      saveBuilder();
      return render();
    }

    if (action === "removeChapterSlide") {
      const ch = state.builder.chapters.find((c) => c.id === el.dataset.chapter);
      if (ch) ch.slides.splice(Number(el.dataset.slideIndex), 1);
      saveBuilder();
      return render();
    }

    if (action === "exportDeck") return doExport();
    if (action === "dismissLoBanner") { state.dismissLoBanner = true; return render(); }
    if (action === "openFile") return openFile(Number(el.dataset.id));
    if (action === "togglePanel") return togglePanel();
    if (action === "zoomIn") return setZoom(ViewModel.stepZoom(state.zoom, 1));
    if (action === "zoomOut") return setZoom(ViewModel.stepZoom(state.zoom, -1));
    if (action === "zoomReset") return setZoom(ViewModel.DEFAULT_ZOOM);
    if (action === "saveDraft") return saveDraft();
    if (action === "filterDrafts") { state.draftFilter = el.dataset.value; return render(); }
    if (action === "editDraft") return editDraft(Number(el.dataset.id));
    if (action === "cancelEditDraft") { state.editingDraft = null; return render(); }
    if (action === "saveDraftMeta") return saveDraftMeta();
    if (action === "newDeck") return newDeck();
    if (action === "openSavedDecks") return openSavedDecks();
    if (action === "closeDrafts") {
      if (e.target !== el && el.classList.contains("modal-backdrop")) return; // click landed inside the dialog
      state.showDrafts = false;
      return render();
    }
    if (action === "openDraft") return openDraft(Number(el.dataset.id));
    if (action === "deleteDraft") return deleteDraft(Number(el.dataset.id));

    if (action === "toggleSourceForm") { state.showSourceForm = !state.showSourceForm; return render(); }

    if (action === "browseFolder") return browseFolder();

    if (action === "submitSource") return submitSource();

    if (action === "reindexSource") {
      await api(`/api/sources/${el.dataset.id}/reindex`, { method: "POST" });
      await refreshSources();
      ensureSourcesPolling();
      return render();
    }

    if (action === "deleteSource") {
      if (!confirm("Remove this source directory? Its decks will drop out of the index (files on disk are untouched).")) return;
      await api(`/api/sources/${el.dataset.id}`, { method: "DELETE" });
      await refreshSources();
      await refreshDomains();
      return render();
    }
  });

  async function browseFolder() {
    state.browsing = true;
    render();
    try {
      const { path } = await api("/api/browse-folder", { method: "POST" });
      if (path) {
        state.sourceForm.path = path;
        if (!state.sourceForm.domain.trim()) {
          const parts = path.split(/[\\/]/).filter(Boolean);
          state.sourceForm.domain = parts[parts.length - 1] || "";
        }
      }
    } catch (err) {
      showToast(String(err.message || err), "error");
    } finally {
      state.browsing = false;
      render();
    }
  }

  async function submitSource() {
    if (!state.sourceForm.path.trim()) { showToast("Enter a folder path first.", "error"); return; }
    try {
      await api("/api/sources", { method: "POST", body: JSON.stringify(state.sourceForm) });
      state.showSourceForm = false;
      state.sourceForm = { path: "", domain: "" };
      await refreshSources();
      ensureSourcesPolling();
      render();
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  document.addEventListener("keydown", (e) => {
    const t = e.target;
    if ((e.key === "Enter" || e.key === " ") && t.matches && t.matches('[role="link"][data-action], [role="button"][data-action]')
        && t.tagName !== "BUTTON" && t.tagName !== "A") {
      e.preventDefault();
      t.click();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s" && state.view !== "sources") {
      e.preventDefault();
      saveDraft();
      return;
    }
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && e.target.closest && e.target.closest("[data-resizer]")) {
      e.preventDefault();
      const step = e.shiftKey ? 96 : 24;
      setPanelWidth(effectivePanelWidth() + (e.key === "ArrowLeft" ? step : -step), true);
      return;
    }
    if (e.key === "Enter" && state.editingDraft && e.target.closest && e.target.closest(".draft-row.editing")) {
      e.preventDefault();
      saveDraftMeta();
      return;
    }
    if (e.key === "Escape" && state.showDrafts) {
      if (state.editingDraft) state.editingDraft = null; else state.showDrafts = false;
      render();
      return;
    }
    const slideEl = e.altKey && e.target.closest ? e.target.closest(".chapter-slide") : null;
    const direction = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" }[e.key];
    if (!slideEl || !direction) return;
    e.preventDefault();
    const pos = BuilderModel.stepSlide(state.builder.chapters, { chapterId: slideEl.dataset.chapter, index: Number(slideEl.dataset.slideIndex) }, direction);
    if (pos) { pendingFocus = pos; saveBuilder(); render(); }
  });

  // ------------------------------------------------------- saved decks --
  function hasUnsavedWork() {
    return state.builder.dirty && (state.builder.chapters.length > 0);
  }
  function confirmDiscard() {
    return !hasUnsavedWork() || confirm(`Discard unsaved changes to “${state.builder.title || "Untitled deck"}”?`);
  }

  function togglePanel() {
    state.panelOpen = !state.panelOpen;
    try { localStorage.setItem(PANEL_KEY, state.panelOpen ? "open" : "closed"); } catch (e) { /* per-viewer convenience only */ }
    render();
  }

  async function saveDraft() {
    if (state.saving) return;
    const b = state.builder;
    const name = (b.title || "").trim();
    if (!name) {
      state.panelOpen = true;
      focusTarget = "name";
      showToast("Give your deck a name before saving.", "error");
      return;
    }
    const body = JSON.stringify({
      name,
      category: (b.category || "").trim() || null,
      add_dividers: b.addDividers,
      chapters: b.chapters.map((c) => ({
        id: c.id,
        name: c.name,
        slides: c.slides.map((s) => ({ file_id: s.file_id, slide_index: s.slide_index, title: s.title, deck_title: s.deck_title })),
      })),
    });
    state.saving = true;
    render();
    try {
      let saved = null;
      if (b.draftId) {
        try { saved = await api(`/api/drafts/${b.draftId}`, { method: "PUT", body }); }
        catch (err) { if (err.status !== 404) throw err; /* deleted elsewhere: save as a new deck */ }
      }
      if (!saved) saved = await api("/api/drafts", { method: "POST", body });
      b.draftId = saved.id;
      b.savedAt = saved.updated_at;
      b.dirty = false;
      saveBuilder(false);
      state.saving = false;
      refreshDrafts().catch(() => {});
      showToast(`Saved “${saved.name}”.`);
    } catch (err) {
      state.saving = false;
      showToast(String(err.message || err), "error");
    }
  }

  async function openSavedDecks() {
    try { await refreshDrafts(); }
    catch (err) { showToast(String(err.message || err), "error"); return; }
    if (state.view === "sources") state.view = "library";
    state.editingDraft = null;
    state.showDrafts = true;
    render();
  }

  function editDraft(id) {
    const d = state.drafts.find((x) => x.id === id);
    if (!d) return;
    state.editingDraft = { id, name: d.name, category: d.category || "" };
    focusTarget = "edit";
    render();
  }

  async function saveDraftMeta() {
    const ed = state.editingDraft;
    if (!ed) return;
    const name = ed.name.trim();
    if (!name) { showToast("A saved deck needs a name.", "error"); return; }
    try {
      const updated = await api(`/api/drafts/${ed.id}`, { method: "PATCH", body: JSON.stringify({ name, category: ed.category.trim() || null }) });
      // Keep the open Builder in step, otherwise its next Save would silently undo the rename.
      if (state.builder.draftId === ed.id) {
        state.builder.title = updated.name;
        state.builder.category = updated.category || "";
        saveBuilder(false);
      }
      state.editingDraft = null;
      await refreshDrafts();
      render();
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  async function openDraft(id) {
    if (id !== state.builder.draftId && !confirmDiscard()) return;
    try {
      const d = await api(`/api/drafts/${id}`);
      state.builder = { title: d.name, category: d.category || "", addDividers: d.add_dividers, chapters: d.chapters, draftId: d.id, dirty: false, savedAt: d.updated_at };
      state.panelOpen = true;
      saveBuilder(false);
      state.showDrafts = false;
      const missing = d.chapters.reduce((n, c) => n + c.slides.filter((s) => s.missing).length, 0);
      render();
      if (missing) showToast(`${missing} slide${missing === 1 ? " is" : "s are"} no longer in the library (shown as Missing; skipped on export).`, "error");
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  async function deleteDraft(id) {
    const d = state.drafts.find((x) => x.id === id);
    if (!confirm(`Delete saved deck “${d ? d.name : id}”? This can't be undone.`)) return;
    try {
      await api(`/api/drafts/${id}`, { method: "DELETE" });
      state.drafts = state.drafts.filter((x) => x.id !== id);
      if (state.builder.draftId === id) { state.builder.draftId = null; saveBuilder(); }
      render();
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  function newDeck() {
    if (!confirmDiscard()) return;
    state.builder = emptyBuilder();
    saveBuilder(false);
    render();
  }

  async function doExport() {
    if (state.builder.chapters.every((c) => c.slides.length === 0)) {
      showToast("Add at least one slide before exporting.", "error");
      return;
    }
    showToast("Building your PowerPoint…");
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: state.builder.title || "New Deck",
          add_dividers: state.builder.addDividers,
          chapters: state.builder.chapters.map((c) => ({
            name: c.name,
            slides: c.slides.map((s) => ({ file_id: s.file_id, slide_index: s.slide_index })),
          })),
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Export failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = (state.builder.title || "New Deck").replace(/\.pptx$/i, "") + ".pptx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      const missing = state.builder.chapters.reduce((n, c) => n + c.slides.filter((s) => s.missing).length, 0);
      showToast("Downloaded " + a.download + " — native slides came in editable, PDF-sourced slides as images." +
        (missing ? ` ${missing} missing slide${missing === 1 ? " was" : "s were"} skipped.` : ""));
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  // -------------------------------------------------------------- startup --
  (async function init() {
    applyTheme();
    applyLayout();
    document.getElementById("app").innerHTML = `<div style="padding:40px;color:var(--text-secondary);">Loading your library…</div>`;
    try {
      await Promise.all([refreshDomains(), refreshDecks(), refreshSources(), refreshDrafts().catch(() => {}),
        api("/api/health").then((h) => { state.health = h; }).catch(() => {})]);
    } catch (err) {
      document.getElementById("app").innerHTML = `<div style="padding:40px;color:var(--red-text);">Could not reach the server: ${esc(String(err.message || err))}</div>`;
      return;
    }
    ensureSourcesPolling();
    render();
  })();
})();
