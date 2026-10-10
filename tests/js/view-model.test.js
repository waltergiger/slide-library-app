const test = require("node:test");
const assert = require("node:assert/strict");
const V = require("../../static/view-model.js");

test("stepZoom moves one step and stops at both ends", () => {
  assert.equal(V.stepZoom(100, 1), 125);
  assert.equal(V.stepZoom(100, -1), 80);
  assert.equal(V.stepZoom(300, 1), 300);
  assert.equal(V.stepZoom(25, -1), 25);
});

test("stepZoom from a typed value between steps goes to the neighbouring step", () => {
  assert.equal(V.stepZoom(110, 1), 125);
  assert.equal(V.stepZoom(110, -1), 100);
  assert.equal(V.stepZoom(90, -1), 80);
});

test("normalizeZoom rejects garbage and clamps typed values", () => {
  assert.equal(V.normalizeZoom(null), 100);
  assert.equal(V.normalizeZoom("abc"), 100);
  assert.equal(V.normalizeZoom(undefined), 100);
  assert.equal(V.normalizeZoom("150"), 150);
  assert.equal(V.normalizeZoom(9999), 300);
  assert.equal(V.normalizeZoom(-5), 25);
  assert.equal(V.normalizeZoom("140%"), 140);
  assert.equal(V.normalizeZoom(" 87 % "), 87);
  assert.equal(V.normalizeZoom(140.6), 141);
});

test("every step is reachable from the default in both directions", () => {
  let z = V.DEFAULT_ZOOM;
  const seen = new Set([z]);
  for (let i = 0; i < 20; i++) seen.add((z = V.stepZoom(z, 1)));
  assert.equal(z, V.ZOOM_MAX);
  for (let i = 0; i < 20; i++) seen.add((z = V.stepZoom(z, -1)));
  assert.equal(z, V.ZOOM_MIN);
  assert.deepEqual([...seen].sort((a, b) => a - b), V.ZOOM_STEPS);
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

test("fileUrl: POSIX paths keep separators and encode everything else", () => {
  assert.equal(V.fileUrl("/Users/wgi/Decks/Plan.pptx"), "file:///Users/wgi/Decks/Plan.pptx");
  assert.equal(V.fileUrl("/Users/wgi/My Decks/Q3 #2 (final) 100%.pptx"), "file:///Users/wgi/My%20Decks/Q3%20%232%20(final)%20100%25.pptx");
  assert.equal(V.fileUrl("/Volumes/Share/Projekt Atlas – Kickoff.pptx"), "file:///Volumes/Share/Projekt%20Atlas%20%E2%80%93%20Kickoff.pptx");
  assert.equal(V.fileUrl("/a/b?c=1.pdf"), "file:///a/b%3Fc%3D1.pdf"); // ? must not start a query string
});

test("fileUrl: Windows drive and UNC paths", () => {
  assert.equal(V.fileUrl("C:\\Decks\\My Deck.pptx"), "file:///C:/Decks/My%20Deck.pptx");
  assert.equal(V.fileUrl("d:/x/y.pdf"), "file:///d:/x/y.pdf");
  assert.equal(V.fileUrl("\\\\fileserver\\Architecture\\v3.pptx"), "file://fileserver/Architecture/v3.pptx");
});

test("fileUrl tolerates empty and relative input", () => {
  assert.equal(V.fileUrl(""), "file:///");
  assert.equal(V.fileUrl(null), "file:///");
  assert.equal(V.fileUrl("rel/a b.pdf"), "file:///rel/a%20b.pdf");
});

test("parseTagInput splits on commas, trims and drops empties", () => {
  assert.deepEqual(V.parseTagInput(" Q3, board   pack,, "), ["Q3", "board pack"]);
  assert.deepEqual(V.parseTagInput(""), []);
  assert.equal(V.parseTagInput("x".repeat(99))[0].length, V.MAX_TAG_LEN);
});

test("mergeTags ignores case duplicates and keeps the existing spelling", () => {
  assert.deepEqual(V.mergeTags(["Board"], ["board", "Q3", "q3"]), ["Board", "Q3"]);
  assert.deepEqual(V.mergeTags(undefined, ["a"]), ["a"]);
});

test("groupByTag puts a slide in every tag section, sorts A-Z, Untagged last", () => {
  const a = { title: "a", tags: ["zeta", "Alpha"] }, b = { title: "b", tags: ["alpha"] }, c = { title: "c", tags: [] };
  const g = V.groupByTag([a, b, c]);
  assert.deepEqual(g.map((x) => x.label), ["Alpha", "zeta", "Untagged"]);
  assert.deepEqual(g[0].items, [a, b]);        // "Alpha" and "alpha" are one section
  assert.deepEqual(g[2].items, [c]);
  assert.deepEqual(V.groupByTag([a]).map((x) => x.key), ["tag:alpha", "tag:zeta"]); // no empty Untagged
});

test("groupByDate groups by local day, newest first, undated last", () => {
  const now = new Date(2026, 9, 3, 15, 0);
  const iso = (y, m, d, h) => new Date(y, m, d, h).toISOString();
  const t1 = { favorited_at: iso(2026, 9, 3, 9) }, t2 = { favorited_at: iso(2026, 9, 3, 14) };
  const y = { favorited_at: iso(2026, 9, 2, 23) }, old = { favorited_at: iso(2026, 7, 1, 8) };
  const none = { favorited_at: null }, bad = { favorited_at: "garbage" };
  const g = V.groupByDate([old, t1, none, y, t2, bad], now);
  assert.deepEqual(g.map((x) => x.label.slice(0, 9)), ["Today", "Yesterday", g[2].label.slice(0, 9), "Earlier ("]);
  assert.deepEqual(g[0].items, [t2, t1]);       // newest star first within a day
  assert.deepEqual(g[2].items, [old]);
  assert.deepEqual(g[3].items, [none, bad]);
});

test("groupByDate can group on any timestamp field", () => {
  const now = new Date(2026, 9, 5, 12);
  const a = { added_at: new Date(2026, 9, 5, 9).toISOString() }, b = { added_at: new Date(2026, 9, 1, 9).toISOString() };
  const g = V.groupByDate([b, a], now, "added_at");
  assert.equal(g[0].label, "Today");
  assert.deepEqual(g.map((x) => x.items), [[a], [b]]);
});

test("groupByDomain sorts sections and decks naturally, ignoring case", () => {
  const d = (domain, title) => ({ domain, title });
  const g = V.groupByDomain([d("strategy", "Deck 10"), d("Architecture", "b"), d("strategy", "Deck 9"), d("Architecture", "A")]);
  assert.deepEqual(g.map((x) => x.label), ["Architecture", "strategy"]);
  assert.deepEqual(g[0].items.map((x) => x.title), ["A", "b"]);
  assert.deepEqual(g[1].items.map((x) => x.title), ["Deck 9", "Deck 10"]);
});

test("previewSequence mirrors the export: dividers per chapter, missing slides skipped", () => {
  const s = (t, missing) => ({ title: t, missing });
  const chapters = [{ name: "Intro", slides: [s("a"), s("gone", true), s("b")] }, { name: "  ", slides: [] }, { name: "End", slides: [s("c")] }];
  const withDiv = V.previewSequence(chapters, true);
  assert.deepEqual(withDiv.pages.map((p) => (p.kind === "divider" ? "#" + p.chapter : p.slide.title)),
    ["#Intro", "a", "b", "#Untitled chapter", "#End", "c"]);
  assert.equal(withDiv.skipped, 1);
  assert.deepEqual(V.previewSequence(chapters, false).pages.map((p) => p.slide.title), ["a", "b", "c"]);
  assert.deepEqual(V.previewSequence([], true), { pages: [], skipped: 0 });
});
