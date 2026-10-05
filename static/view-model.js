/* Pure view rules (library zoom, resizable deck panel, favorites grouping),
 * kept free of DOM so they can be unit-tested with plain Node (tests/js). */
(function (root) {
  "use strict";

  // Discrete steps keep +/- predictable and avoid odd fractional grid widths.
  const ZOOM_STEPS = [50, 65, 80, 100, 125, 150, 175, 200];
  const DEFAULT_ZOOM = 100;

  const PANEL = { min: 300, max: 900, def: 400 };
  // Space the library must keep when the panel grows: sidebar (264) + a usable grid column area.
  const LIBRARY_RESERVED = 264 + 360;

  // Number(null) is 0 and Number("") is 0: neither is a real stored value.
  function toNumber(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : null;
    if (typeof value === "string" && value.trim() !== "") {
      const n = Number(value);
      return Number.isFinite(n) ? n : null;
    }
    return null;
  }

  /** Snap any stored/foreign value to the nearest allowed zoom step. */
  function normalizeZoom(value) {
    const n = toNumber(value);
    if (n === null) return DEFAULT_ZOOM;
    return ZOOM_STEPS.reduce((best, z) => (Math.abs(z - n) < Math.abs(best - n) ? z : best), ZOOM_STEPS[0]);
  }

  /** Next zoom in the direction (+1 / -1); stays put at either end. */
  function stepZoom(current, direction) {
    const i = ZOOM_STEPS.indexOf(normalizeZoom(current));
    return ZOOM_STEPS[Math.max(0, Math.min(ZOOM_STEPS.length - 1, i + Math.sign(direction)))];
  }

  /** Largest panel width that still leaves the library usable at this viewport width. */
  function maxPanelWidth(viewportWidth) {
    return Math.max(PANEL.min, Math.min(PANEL.max, viewportWidth - LIBRARY_RESERVED));
  }

  function clampPanelWidth(width, viewportWidth) {
    const n = toNumber(width);
    if (n === null) return PANEL.def;
    return Math.round(Math.max(PANEL.min, Math.min(maxPanelWidth(viewportWidth), n)));
  }

  /** file:// URL for a local path, so "copy link address" gives something valid.
   *  Handles POSIX, Windows drive and UNC paths; every segment is percent-encoded
   *  (spaces, #, ?, %, non-ASCII) so the name can't be mistaken for URL syntax. */
  function fileUrl(path) {
    const p = String(path == null ? "" : path);
    const encode = (s) => s.split("/").map(encodeURIComponent).join("/");
    const drive = /^([A-Za-z]:)[\\/](.*)$/.exec(p);
    if (drive) return "file:///" + drive[1] + "/" + encode(drive[2].replace(/\\/g, "/"));
    if (p.startsWith("\\\\")) return "file://" + encode(p.slice(2).replace(/\\/g, "/")); // \\server\share\x -> file://server/share/x
    return "file://" + (p.startsWith("/") ? "" : "/") + encode(p);
  }

  // ---- favorites: tags and grouping --------------------------------------

  const MAX_TAG_LEN = 40; // mirrors app/db.py so the UI never shows a tag the server would cut

  const cleanTag = (t) => String(t == null ? "" : t).split(/\s+/).filter(Boolean).join(" ").slice(0, MAX_TAG_LEN);

  /** "Q3, board  pack," -> ["Q3", "board pack"]: commas let several tags be typed at once. */
  function parseTagInput(text) {
    return String(text == null ? "" : text).split(",").map(cleanTag).filter(Boolean);
  }

  /** Appends tags not already present, ignoring case; existing spelling wins. */
  function mergeTags(existing, added) {
    const out = [...(existing || [])];
    const seen = new Set(out.map((t) => t.toLowerCase()));
    (added || []).forEach((t) => { if (!seen.has(t.toLowerCase())) { seen.add(t.toLowerCase()); out.push(t); } });
    return out;
  }

  /** One section per tag (a slide with two tags appears in both), A–Z, then "Untagged". */
  function groupByTag(slides) {
    const groups = new Map();
    const untagged = [];
    (slides || []).forEach((s) => {
      const tags = s.tags || [];
      if (!tags.length) { untagged.push(s); return; }
      tags.forEach((t) => {
        const key = "tag:" + t.toLowerCase();
        if (!groups.has(key)) groups.set(key, { key, label: t, items: [] });
        groups.get(key).items.push(s);
      });
    });
    const out = [...groups.values()].sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
    if (untagged.length) out.push({ key: "untagged", label: "Untagged", items: untagged });
    return out;
  }

  const pad = (n) => String(n).padStart(2, "0");
  const localDayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  function dayLabel(date, now) {
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const diff = Math.round((today - day) / 86400000); // rounding absorbs DST-shortened days
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  }

  /** One section per local calendar day of `field` (default: when the star was
   *  set), newest first. Items without a timestamp (e.g. stars from before dates
   *  were recorded) go last. */
  function groupByDate(slides, now, field) {
    now = now || new Date();
    field = field || "favorited_at";
    const groups = new Map();
    const undated = [];
    (slides || []).forEach((s) => {
      const d = s[field] ? new Date(s[field]) : null;
      if (!d || Number.isNaN(d.getTime())) { undated.push(s); return; }
      const key = "date:" + localDayKey(d);
      if (!groups.has(key)) groups.set(key, { key, label: dayLabel(d, now), items: [] });
      groups.get(key).items.push(s);
    });
    const out = [...groups.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
    out.forEach((g) => g.items.sort((a, b) => (a[field] < b[field] ? 1 : a[field] > b[field] ? -1 : 0)));
    if (undated.length) out.push({ key: "date:none", label: "Earlier (no date recorded)", items: undated });
    return out;
  }

  /** One section per domain, A–Z, decks A–Z inside. */
  function groupByDomain(decks) {
    const groups = new Map();
    (decks || []).forEach((d) => {
      const key = "domain:" + d.domain;
      if (!groups.has(key)) groups.set(key, { key, label: d.domain, items: [] });
      groups.get(key).items.push(d);
    });
    const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });
    const out = [...groups.values()].sort((a, b) => byName(a.label, b.label));
    out.forEach((g) => g.items.sort((a, b) => byName(a.title, b.title)));
    return out;
  }

  const api = {
    fileUrl, ZOOM_STEPS, DEFAULT_ZOOM, PANEL, normalizeZoom, stepZoom, maxPanelWidth, clampPanelWidth,
    MAX_TAG_LEN, parseTagInput, mergeTags, groupByTag, groupByDate, groupByDomain, dayLabel,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ViewModel = api;
})(typeof self !== "undefined" ? self : this);
