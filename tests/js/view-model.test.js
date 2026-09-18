const test = require("node:test");
const assert = require("node:assert/strict");
const V = require("../../static/view-model.js");

test("stepZoom moves one step and stops at both ends", () => {
  assert.equal(V.stepZoom(100, 1), 125);
  assert.equal(V.stepZoom(100, -1), 80);
  assert.equal(V.stepZoom(200, 1), 200);
  assert.equal(V.stepZoom(50, -1), 50);
});

test("stepZoom from a value between steps snaps first, so +/- never skip or stall", () => {
  assert.equal(V.stepZoom(110, 1), 125);   // 110 -> 100 -> 125
  assert.equal(V.stepZoom(90, -1), 65);    // 90 -> 80 -> 65
});

test("normalizeZoom rejects garbage and snaps stored values", () => {
  assert.equal(V.normalizeZoom(null), 100);
  assert.equal(V.normalizeZoom("abc"), 100);
  assert.equal(V.normalizeZoom(undefined), 100);
  assert.equal(V.normalizeZoom("150"), 150);
  assert.equal(V.normalizeZoom(9999), 200);
  assert.equal(V.normalizeZoom(-5), 50);
});

test("every step is reachable from the default in both directions", () => {
  let z = V.DEFAULT_ZOOM;
  for (let i = 0; i < 20; i++) z = V.stepZoom(z, 1);
  assert.equal(z, 200);
  for (let i = 0; i < 20; i++) z = V.stepZoom(z, -1);
  assert.equal(z, 50);
});

test("clampPanelWidth respects min, max and the space the library needs", () => {
  assert.equal(V.clampPanelWidth(100, 1600), 300);
  assert.equal(V.clampPanelWidth(5000, 1600), 900);
  assert.equal(V.clampPanelWidth(450, 1600), 450);
  assert.equal(V.clampPanelWidth(800, 1000), 376);   // 1000 - 624 leaves room for sidebar + grid
  assert.equal(V.clampPanelWidth(400.6, 1600), 401);
});

test("on a tiny viewport the panel never drops below its minimum", () => {
  assert.equal(V.maxPanelWidth(500), 300);
  assert.equal(V.clampPanelWidth(900, 500), 300);
});

test("clampPanelWidth falls back to the default for non-numbers", () => {
  assert.equal(V.clampPanelWidth("x", 1600), 400);
  assert.equal(V.clampPanelWidth(undefined, 1600), 400);
});

test("empty string and null are treated as 'nothing stored'", () => {
  assert.equal(V.normalizeZoom(""), 100);
  assert.equal(V.normalizeZoom("  "), 100);
  assert.equal(V.clampPanelWidth(null, 1600), 400);
  assert.equal(V.clampPanelWidth("", 1600), 400);
});
