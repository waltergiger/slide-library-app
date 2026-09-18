/* Pure sizing rules for the library zoom and the resizable deck panel, kept
 * free of DOM so they can be unit-tested with plain Node (tests/js). */
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

  const api = { fileUrl, ZOOM_STEPS, DEFAULT_ZOOM, PANEL, normalizeZoom, stepZoom, maxPanelWidth, clampPanelWidth };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ViewModel = api;
})(typeof self !== "undefined" ? self : this);
