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
    save: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/></svg>`,
    starFill: `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 2.7 5.9 6.3.7-4.7 4.4 1.3 6.2L12 17.3 6.4 20.2l1.3-6.2-4.7-4.4 6.3-.7Z"/></svg>`,
  };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- state --
  const BUILDER_KEY = "slidelib-builder";
  const THEME_KEY = "slidelib-theme";

  // The Builder is auto-kept in localStorage as a working copy (survives a
  // reload); "Save" additionally stores it server-side as a named deck that
  // can be reopened from any browser. `dirty` = edits since the last Save.
  const emptyBuilder = () => ({ title: "New Deck", addDividers: true, chapters: [], draftId: null, dirty: false, savedAt: null });

  function loadBuilder() {
    try {
      const raw = localStorage.getItem(BUILDER_KEY);
      if (raw) return { ...emptyBuilder(), ...JSON.parse(raw) };
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
    builderQuery: "",
    builderResults: [],
    dragging: null,
    dropTarget: null,
    showDrafts: false,
    drafts: [],
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
    app.innerHTML = html + (state.view === "builder" && state.showDrafts ? renderDraftsModal() : "") + renderToast();
    attachHandlers();
    if (pendingFocus) {
      const target = [...app.querySelectorAll(".chapter-slide")].find(
        (el) => el.dataset.chapter === pendingFocus.chapterId && Number(el.dataset.slideIndex) === pendingFocus.index);
      if (target) target.focus();
      pendingFocus = null;
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

  function renderFavoriteSlides() {
    const slides = state.favSlides;
    if (!slides.length) {
      const msg = state.query ? `No favorite slides match "${esc(state.query)}".` : "No favorite slides yet — star a few slides in a deck first.";
      return { count: 0, unit: "slide", html: `<div class="empty-state">${ICON.starFill}<span style="font-size:14.5px;">${msg}</span></div>` };
    }
    const groups = new Map();
    slides.forEach((f) => { if (!groups.has(f.domain)) groups.set(f.domain, []); groups.get(f.domain).push(f); });
    const html = [...groups].map(([domain, items]) => `<section class="fav-group">
      <div class="fav-group-head"><span class="tag">${esc(domain)}</span><span class="count">${items.length} slide${items.length === 1 ? "" : "s"}</span></div>
      <div class="fav-grid">${items.map((f) => {
        const b = badgeFor(f.ext);
        return `<div class="fav-tile">
          <div class="slide-card" data-action="openDeck" data-id="${f.file_id}" role="button" tabindex="0" aria-label="${esc(f.title)}, from ${esc(f.deck_title)}, slide ${f.slide_index + 1}">
            ${f.thumb_url ? `<img src="${esc(f.thumb_url)}" alt="">` : `<div class="title">${esc(f.title)}</div>`}
            <button type="button" class="star-btn active" data-action="toggleFavorite" data-file-id="${f.file_id}" data-index="${f.slide_index}" data-favorite="1" aria-label="Remove from favorites" aria-pressed="true">${ICON.starFill}</button>
            <div class="slide-index">${f.slide_index + 1}</div>
          </div>
          <div class="fav-caption"><div class="t">${esc(f.title)}</div><div class="d"><span class="badge-mini ${b.cls}">${b.label}</span>${esc(f.deck_title)}</div></div>
        </div>`;
      }).join("")}</div>
    </section>`).join("");
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
        ${filterRow()}
        <div class="heading-row"><h1>${esc(state.selectedDomain)}</h1><span class="count">${count} ${unit}${count === 1 ? "" : "s"}</span></div>
        ${html}
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
      <div class="source-card" draggable="true" data-drag="source" data-source-index="${i}">
        ${ICON.dots}
        <div class="mini-thumb">${r.thumb_url ? `<img src="${esc(r.thumb_url)}" alt="" draggable="false">` : ""}</div>
        <div class="info">
          <div class="t">${esc(r.title)}</div>
          <div class="d">${esc(r.deck_title)}</div>
        </div>
        <button type="button" class="star-btn inline ${r.favorite ? "active" : ""}" data-action="toggleFavorite" data-file-id="${r.file_id}" data-index="${r.slide_index}" data-favorite="${r.favorite ? "1" : "0"}" aria-label="${r.favorite ? "Remove from favorites" : "Mark as favorite"}" aria-pressed="${!!r.favorite}">${r.favorite ? ICON.starFill : ICON.star}</button>
      </div>`).join("");

    const chaptersHtml = state.builder.chapters.map((ch) => {
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

    const totalSlides = builderSlideCount();
    const st = builderStatus();

    return `<div class="builder-topbar">
      <div class="row">
        <div style="display:flex;align-items:center;gap:14px;min-width:0;">
          <a href="#" class="icon-btn sm" data-action="goto" data-view="library" aria-label="Back to library">${ICON.chevronLeft}</a>
          <input class="title-input" value="${esc(state.builder.title)}" data-bind="builderTitle" aria-label="Deck title">
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          ${themeToggleButton()}
          <button type="button" class="btn btn-secondary btn-sm" data-action="newDeck">${ICON.plus} New</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="openSavedDecks">${ICON.folder} Open</button>
          <button type="button" class="btn btn-secondary btn-sm" data-action="saveDraft" ${state.saving ? "disabled" : ""}>${ICON.save} Save</button>
          <button type="button" class="btn btn-primary" data-action="exportDeck">${ICON.download} Export to PowerPoint</button>
        </div>
      </div>
      <span class="builder-summary"><span id="saveStatus" class="save-status ${st.cls}">${st.text}</span> ·
        ${state.builder.chapters.length} chapter${state.builder.chapters.length === 1 ? "" : "s"} · ${totalSlides} slide${totalSlides === 1 ? "" : "s"} so far ·
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
        <div class="hint">Drag slides in from the left, between chapters, or within a chapter to set the order — drag a chapter by its grip to reorder chapters. Keyboard: focus a slide and press Alt + arrow keys.</div>
        ${chaptersHtml}
        <div class="new-chapter-row">
          <input class="input input-sm" type="text" placeholder="New chapter name…" data-bind="newChapterName">
          <button type="button" class="btn btn-secondary btn-sm" data-action="addChapter">${ICON.plus} Add chapter</button>
        </div>
      </div>
    </div>`;
  }

  function renderDraftsModal() {
    const rows = state.drafts.map((d) => `
      <div class="draft-row ${d.id === state.builder.draftId ? "current" : ""}">
        <div class="body">
          <div class="name">${esc(d.name)}${d.id === state.builder.draftId ? ` <span class="tag">Open now</span>` : ""}</div>
          <div class="meta">${d.chapter_count} chapter${d.chapter_count === 1 ? "" : "s"} · ${d.slide_count} slide${d.slide_count === 1 ? "" : "s"} · Updated ${new Date(d.updated_at).toLocaleString()}</div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" data-action="openDraft" data-id="${d.id}">Open</button>
        <button type="button" class="icon-btn sm" data-action="deleteDraft" data-id="${d.id}" aria-label="Delete saved deck ${esc(d.name)}" style="color:var(--red-text);">${ICON.trash}</button>
      </div>`).join("");
    return `<div class="modal-backdrop" data-action="closeDrafts">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Saved decks" tabindex="-1">
        <div class="modal-head"><h2>Saved decks</h2><button type="button" class="icon-btn sm" data-action="closeDrafts" aria-label="Close">${ICON.x}</button></div>
        <div class="modal-body">${rows || `<div class="footnote">No saved decks yet — build a deck and press Save.</div>`}</div>
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
  }

  // ------------------------------------------------------- drag and drop --
  // Dragging never re-renders (that would cancel the drag): indicators are
  // toggled as CSS classes, the drop target is remembered in state.dropTarget
  // and the model change + render happen once, on drop.
  function onDragStart(e, el) {
    const kind = el.dataset.drag;
    if (kind === "source") state.dragging = { kind, slide: state.builderResults[Number(el.dataset.sourceIndex)] };
    else if (kind === "slide") state.dragging = { kind, chapterId: el.dataset.chapter, index: Number(el.dataset.slideIndex) };
    else state.dragging = { kind: "chapter", chapterId: el.dataset.chapter };
    e.dataTransfer.effectAllowed = kind === "source" ? "copy" : "move";
    e.dataTransfer.setData("text/plain", "slide-library"); // Firefox won't start a drag without data
    const visual = kind === "chapter" ? el.closest(".chapter") : el;
    if (kind === "chapter") e.dataTransfer.setDragImage(visual, 16, 16);
    setTimeout(() => visual.classList.add("dragging"), 0); // after the drag image is captured
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
    } else if (d.kind === "source" && t.kind === "slide" && d.slide) {
      changed = !!BuilderModel.insertSlide(chapters, t.chapterId, t.slot, slideRef(d.slide));
    }
    if (changed) saveBuilder();
    render();
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
    if (action === "saveDraft") return saveDraft();
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
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s" && state.view === "builder") {
      e.preventDefault();
      saveDraft();
      return;
    }
    if (e.key === "Escape" && state.showDrafts) { state.showDrafts = false; render(); return; }
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

  async function saveDraft() {
    if (state.saving) return;
    const b = state.builder;
    const body = JSON.stringify({
      name: (b.title || "").trim() || "Untitled deck",
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
      showToast(`Saved “${saved.name}”.`);
    } catch (err) {
      state.saving = false;
      showToast(String(err.message || err), "error");
    }
  }

  async function openSavedDecks() {
    try { state.drafts = await api("/api/drafts"); }
    catch (err) { showToast(String(err.message || err), "error"); return; }
    state.view = "builder";
    state.showDrafts = true;
    render();
  }

  async function openDraft(id) {
    if (id !== state.builder.draftId && !confirmDiscard()) return;
    try {
      const d = await api(`/api/drafts/${id}`);
      state.builder = { title: d.name, addDividers: d.add_dividers, chapters: d.chapters, draftId: d.id, dirty: false, savedAt: d.updated_at };
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
