/* Slide Library — client. Talks to the FastAPI backend in ../app/main.py.
 * No build step, no framework: one state object, a render() per view, and
 * a click-delegation dispatcher keyed by data-action attributes. */

(() => {
  "use strict";

  // ---------------------------------------------------------------- icons --
  const ICON = {
    search: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg>`,
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
    starFill: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 2.7 5.9 6.3.7-4.7 4.4 1.3 6.2L12 17.3 6.4 20.2l1.3-6.2-4.7-4.4 6.3-.7Z"/></svg>`,
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- state --
  const BUILDER_KEY = "slidelib-builder";
  const THEME_KEY = "slidelib-theme";

  function loadBuilder() {
    try {
      const raw = localStorage.getItem(BUILDER_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* ignore corrupt storage */ }
    return { title: "New Deck", addDividers: true, chapters: [] };
  }
  function saveBuilder() {
    try { localStorage.setItem(BUILDER_KEY, JSON.stringify(state.builder)); } catch (e) { /* storage full/blocked */ }
  }

  const state = {
    view: "library",
    theme: (() => { try { return localStorage.getItem(THEME_KEY) || "dark"; } catch (e) { return "dark"; } })(),
    domains: [{ name: "All domains", count: 0 }],
    selectedDomain: "All domains",
    query: "",
    filters: { pptx: true, pdf: true, favoritesOnly: false },
    decks: [],
    currentDeck: null,
    slideSelection: new Set(),
    sources: [],
    showSourceForm: false,
    sourceForm: { path: "", domain: "" },
    browsing: false,
    builder: loadBuilder(),
    builderQuery: "",
    builderResults: [],
    dragging: null,
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
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  async function refreshDomains() { state.domains = await api("/api/domains"); }
  async function refreshDecks() {
    const params = new URLSearchParams();
    if (state.selectedDomain && state.selectedDomain !== "All domains") params.set("domain", state.selectedDomain);
    if (state.query.trim()) params.set("q", state.query.trim());
    if (state.filters.favoritesOnly) params.set("favorites_only", "true");
    state.decks = await api(`/api/decks?${params}`);
  }
  async function refreshSources() { state.sources = await api("/api/sources"); }
  async function loadDeck(id) {
    state.currentDeck = await api(`/api/decks/${id}`);
    state.slideSelection = new Set();
  }
  async function runBuilderSearch() {
    const q = state.builderQuery.trim();
    state.builderResults = q ? await api(`/api/search?q=${encodeURIComponent(q)}`) : [];
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

  function badgeFor(ext) { return ext === "pdf" ? { cls: "pdf", label: "PDF" } : { cls: "pptx", label: "PPT" }; }

  function findOrCreateChapter(name) {
    let ch = state.builder.chapters.find((c) => c.name === name);
    if (!ch) {
      ch = { id: "ch" + Date.now() + Math.random().toString(36).slice(2, 6), name, slides: [] };
      state.builder.chapters.push(ch);
    }
    return ch;
  }

  function addSlideToChapter(chapterId, slide) {
    const ch = state.builder.chapters.find((c) => c.id === chapterId);
    if (!ch) return;
    ch.slides.push({
      file_id: slide.file_id,
      slide_index: slide.slide_index,
      title: slide.title,
      deck_title: slide.deck_title,
      thumb_url: slide.thumb_url,
    });
    saveBuilder();
  }

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
    state.builderResults.forEach((r) => { if (r.file_id === fileId && r.slide_index === slideIndex) r.favorite = nextValue; });
    if (!nextValue && state.filters.favoritesOnly && state.view === "library") {
      await refreshDecks();
    }
    render();
  }

  // -------------------------------------------------------------- render --
  function render() {
    applyTheme();
    const app = document.getElementById("app");
    if (state.view === "deck" && !state.currentDeck) { app.innerHTML = `<div style="padding:40px">Loading…</div>`; return; }
    let html;
    if (state.view === "library") html = renderLibrary();
    else if (state.view === "deck") html = renderDeck();
    else if (state.view === "builder") html = renderBuilder();
    else html = renderSources();
    app.innerHTML = html + renderToast();
    attachHandlers();
  }

  function renderToast() {
    if (!state.toast) return "";
    return `<div class="toast ${state.toast.kind === "error" ? "error" : ""}">
      <span style="font-size:13px;line-height:1.4;">${esc(state.toast.message)}</span>
      <button type="button" data-action="dismissToast" aria-label="Dismiss" style="opacity:0.75;">${ICON.x}</button>
    </div>`;
  }

  function renderLibrary() {
    const domainsHtml = state.domains.map((d) => {
      const active = d.name === state.selectedDomain;
      return `<button type="button" class="nav-item ${active ? "active" : ""}" data-action="selectDomain" data-value="${esc(d.name)}">
        <span class="left">${ICON.folder}${esc(d.name)}</span>
        <span class="nav-count">${d.count}</span>
      </button>`;
    }).join("");

    const typeVisible = (ext) => (ext === "pdf" ? state.filters.pdf : state.filters.pptx);
    const noTypeSelected = !state.filters.pptx && !state.filters.pdf;
    const visibleDecks = noTypeSelected ? [] : state.decks.filter((d) => typeVisible(d.ext));

    const decksHtml = visibleDecks.map((d) => {
      const b = badgeFor(d.ext);
      return `<a href="#" class="deck-card" data-action="openDeck" data-id="${d.id}">
        <div class="deck-card-top">
          <div class="badge ${b.cls}">${b.label}</div>
          <span class="tag">${esc(d.domain)}</span>
        </div>
        <div class="deck-title">${esc(d.title)}</div>
        <div class="deck-meta">${d.slide_count} slides</div>
      </a>`;
    }).join("");

    const emptyMessage = noTypeSelected
      ? "No file type selected — turn on PPTX or PDF above to see decks."
      : (state.filters.favoritesOnly
          ? "No favorited slides match these filters yet — star a few slides in a deck first."
          : (state.query ? `No decks match "${esc(state.query)}".` : "No decks indexed yet — add a source directory to get started."));

    const body = visibleDecks.length
      ? `<div class="deck-grid">${decksHtml}</div>`
      : `<div class="empty-state">${ICON.search}<span style="font-size:14.5px;">${state.decks === null ? "Loading…" : emptyMessage}</span></div>`;

    const filterChip = (key, label, iconHtml) => `<label class="filter-chip ${state.filters[key] ? "active" : ""}">
      <input type="checkbox" data-bind="filter-${key}" ${state.filters[key] ? "checked" : ""}>
      ${iconHtml || ""}${label}
    </label>`;
    const filterRow = `<div class="filter-row">
      ${filterChip("pptx", "PPTX")}
      ${filterChip("pdf", "PDF")}
      ${filterChip("favoritesOnly", "Favorites", ICON.starFill)}
    </div>`;

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
          <a href="#" class="link-row" data-action="goto" data-view="sources">${ICON.plus} Manage sources</a>
        </div>
      </div>
      <div class="main">
        <div class="top-row">
          <div class="search-wrap" style="flex-grow:1;max-width:420px;">
            ${ICON.search.replace("<svg", '<svg class="search-icon"')}
            <label for="librarySearch" class="sr-only">Search the library</label>
            <input id="librarySearch" class="input" type="text" placeholder="Search decks, slides, or text inside slides…" value="${esc(state.query)}" data-bind="query">
          </div>
          <div class="actions">
            ${themeToggleButton()}
            <button type="button" class="btn btn-primary" data-action="goto" data-view="builder">${ICON.plus} New deck</button>
          </div>
        </div>
        ${filterRow}
        <div class="heading-row"><h1>${esc(state.selectedDomain)}</h1><span class="count">${visibleDecks.length} deck${visibleDecks.length === 1 ? "" : "s"}</span></div>
        ${body}
      </div>
    </div>`;
  }

  function renderDeck() {
    const deck = state.currentDeck;
    const b = badgeFor(deck.ext);
    const slidesHtml = deck.slides.map((s) => {
      const selected = state.slideSelection.has(s.index);
      return `<div class="slide-card ${selected ? "selected" : ""}" data-action="toggleSlide" data-index="${s.index}" role="button" tabindex="0" aria-pressed="${selected}" aria-label="${esc(s.title)}, slide ${s.index + 1}">
        ${s.thumb_url
          ? `<img src="${esc(s.thumb_url)}" alt="">`
          : `<div class="title">${esc(s.title)}</div>`}
        <button type="button" class="star-btn ${s.favorite ? "active" : ""}" data-action="toggleFavorite" data-file-id="${deck.id}" data-index="${s.index}" data-favorite="${s.favorite ? "1" : "0"}" aria-label="${s.favorite ? "Remove from favorites" : "Mark as favorite"}" aria-pressed="${!!s.favorite}">${s.favorite ? ICON.starFill : ICON.star}</button>
        <div class="slide-indicator">${selected ? ICON.check : ""}</div>
        <div class="slide-index">${s.index + 1}</div>
      </div>`;
    }).join("");

    const count = state.slideSelection.size;
    const bar = count > 0 ? `<div class="floating-bar">
      <span style="font-size:13.5px;font-weight:500;">${count} slide${count === 1 ? "" : "s"} selected</span>
      <button type="button" class="go-btn" data-action="addSelectionToBuilder">Add to Builder ${ICON.arrowRight}</button>
    </div>` : "";

    return `<div style="padding:24px 32px 0;">
      <a href="#" class="back-link" data-action="goto" data-view="library">${ICON.chevronLeft} Back to library</a>
      <div class="deck-header">
        <div class="left">
          <div class="deck-icon badge-${b.cls}" style="background:${b.cls === "pdf" ? "var(--pdf-badge)" : "var(--pptx-badge)"};">${b.label}</div>
          <div>
            <h1 style="margin:0 0 4px;font-size:21px;font-weight:700;">${esc(deck.title)}</h1>
            <div style="font-size:13px;color:var(--text-secondary);">${deck.slide_count} slides · ${deck.ext.toUpperCase()} · ${esc(deck.domain)}</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${themeToggleButton()}
          <button type="button" class="btn btn-secondary" data-action="addAllToBuilder">Add all ${deck.slide_count} to new deck</button>
        </div>
      </div>
      <div class="divider" style="margin-top:20px;"></div>
    </div>
    <div style="padding:20px 32px 110px;">
      <div class="slide-grid">${slidesHtml}</div>
    </div>
    ${bar}`;
  }

  function renderBuilder() {
    const resultsHtml = state.builderResults.map((r, i) => `
      <div class="source-card" draggable="true" data-action="dragSource" data-source-index="${i}">
        ${ICON.dots}
        <div class="mini-thumb">${r.thumb_url ? `<img src="${esc(r.thumb_url)}" alt="">` : ""}</div>
        <div class="info">
          <div class="t">${esc(r.title)}</div>
          <div class="d">${esc(r.deck_title)}</div>
        </div>
        <button type="button" class="star-btn inline ${r.favorite ? "active" : ""}" data-action="toggleFavorite" data-file-id="${r.file_id}" data-index="${r.slide_index}" data-favorite="${r.favorite ? "1" : "0"}" aria-label="${r.favorite ? "Remove from favorites" : "Mark as favorite"}" aria-pressed="${!!r.favorite}">${r.favorite ? ICON.starFill : ICON.star}</button>
      </div>`).join("");

    const chaptersHtml = state.builder.chapters.map((ch) => {
      const slidesHtml = ch.slides.map((s, i) => `
        <div class="chapter-slide">
          <div class="thumb">${s.thumb_url ? `<img src="${esc(s.thumb_url)}" alt="">` : ""}</div>
          <button type="button" class="remove" data-action="removeChapterSlide" data-chapter="${ch.id}" data-slide-index="${i}" aria-label="Remove slide">${ICON.xSmall}</button>
          <div class="t">${esc(s.title)}</div>
        </div>`).join("");
      return `<div class="chapter" data-action="chapterDropZone" data-chapter="${ch.id}">
        <div class="chapter-head">
          <div class="left">
            ${ICON.dots}
            <input class="chapter-name" value="${esc(ch.name)}" data-bind="chapterName" data-chapter="${ch.id}" style="width:${Math.max(6, ch.name.length)}ch">
            <span class="chapter-count">${ch.slides.length}</span>
          </div>
          <button type="button" aria-label="Remove chapter" style="color:var(--text-tertiary);padding:4px;" data-action="removeChapter" data-chapter="${ch.id}">${ICON.x}</button>
        </div>
        ${ch.slides.length ? `<div class="chapter-slides">${slidesHtml}</div>` : `<div class="chapter-empty">Drag slides here</div>`}
      </div>`;
    }).join("");

    const totalSlides = state.builder.chapters.reduce((n, c) => n + c.slides.length, 0);

    return `<div class="builder-topbar">
      <div class="row">
        <div style="display:flex;align-items:center;gap:14px;min-width:0;">
          <a href="#" class="icon-btn sm" data-action="goto" data-view="library" aria-label="Back to library">${ICON.chevronLeft}</a>
          <input class="title-input" value="${esc(state.builder.title)}" data-bind="builderTitle" aria-label="Deck title">
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${themeToggleButton()}
          <button type="button" class="btn btn-primary" data-action="exportDeck">${ICON.download} Export to PowerPoint</button>
        </div>
      </div>
      <span class="builder-summary">${state.builder.chapters.length} chapter${state.builder.chapters.length === 1 ? "" : "s"} · ${totalSlides} slide${totalSlides === 1 ? "" : "s"} so far ·
        <label style="cursor:pointer;"><input type="checkbox" data-bind="addDividers" ${state.builder.addDividers ? "checked" : ""} style="vertical-align:-2px;"> chapter divider slides</label>
      </span>
    </div>
    <div class="builder-body">
      <div class="source-panel">
        <div class="nav-label">Add slides from your library</div>
        <div class="search-wrap">
          ${ICON.search.replace("<svg", '<svg class="search-icon"')}
          <input class="input input-sm" type="text" placeholder="Search all decks & slides…" value="${esc(state.builderQuery)}" data-bind="builderQuery">
        </div>
        <div class="list">${resultsHtml || `<div style="font-size:12.5px;color:var(--text-secondary);padding:8px 2px;">Search to find slides from your indexed decks.</div>`}</div>
      </div>
      <div class="canvas">
        <div class="hint">Drag a slide from the left into a chapter below — or add a chapter first, then drag slides in.</div>
        ${chaptersHtml}
        <div class="new-chapter-row">
          <input class="input input-sm" type="text" placeholder="New chapter name…" data-bind="newChapterName">
          <button type="button" class="btn btn-secondary btn-sm" data-action="addChapter">${ICON.plus} Add chapter</button>
        </div>
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

    app.querySelectorAll('[data-action="dragSource"]').forEach((el) => {
      el.addEventListener("dragstart", (e) => {
        const idx = Number(el.dataset.sourceIndex);
        state.dragging = state.builderResults[idx];
        e.dataTransfer.effectAllowed = "copy";
      });
    });
    app.querySelectorAll('[data-action="chapterDropZone"]').forEach((el) => {
      el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("drag-over"); });
      el.addEventListener("dragleave", () => el.classList.remove("drag-over"));
      el.addEventListener("drop", (e) => {
        e.preventDefault();
        el.classList.remove("drag-over");
        if (state.dragging) {
          addSlideToChapter(el.dataset.chapter, state.dragging);
          state.dragging = null;
          render();
        }
      });
    });
  }

  function onBind(name, e, el) {
    const v = el.type === "checkbox" ? el.checked : el.value;
    if (name === "query") { state.query = v; debounce("decks", () => { refreshDecks().then(render); }); }
    else if (name === "builderTitle") { state.builder.title = v; saveBuilder(); }
    else if (name === "addDividers") { state.builder.addDividers = v; saveBuilder(); }
    else if (name === "builderQuery") { state.builderQuery = v; debounce("builder", () => { runBuilderSearch().then(render); }); }
    else if (name === "newChapterName") { state._newChapterName = v; }
    else if (name === "chapterName") {
      const ch = state.builder.chapters.find((c) => c.id === el.dataset.chapter);
      if (ch) { ch.name = v; saveBuilder(); }
    } else if (name === "sourcePath") { state.sourceForm.path = v; }
    else if (name === "sourceDomain") { state.sourceForm.domain = v; }
    else if (name.startsWith("filter-")) {
      const key = name.slice("filter-".length);
      state.filters[key] = v;
      if (key === "favoritesOnly") refreshDecks().then(render);
      else render();
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
      state.view = "builder";
      return render();
    }

    if (action === "addChapter") {
      const name = (state._newChapterName || "").trim() || "New chapter";
      state.builder.chapters.push({ id: "ch" + Date.now(), name, slides: [] });
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
      showToast("Downloaded " + a.download + " — native slides came in editable, PDF-sourced slides as images.");
    } catch (err) {
      showToast(String(err.message || err), "error");
    }
  }

  // -------------------------------------------------------------- startup --
  (async function init() {
    applyTheme();
    document.getElementById("app").innerHTML = `<div style="padding:40px;color:var(--text-secondary);">Loading your library…</div>`;
    try {
      await Promise.all([refreshDomains(), refreshDecks(), refreshSources()]);
    } catch (err) {
      document.getElementById("app").innerHTML = `<div style="padding:40px;color:var(--red-text);">Could not reach the server: ${esc(String(err.message || err))}</div>`;
      return;
    }
    ensureSourcesPolling();
    render();
  })();
})();
