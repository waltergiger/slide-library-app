const test = require("node:test");
const assert = require("node:assert/strict");
const M = require("../../static/builder-model.js");

const mk = () => [
  { id: "a", name: "A", slides: ["a0", "a1", "a2"].map((t) => ({ t })) },
  { id: "b", name: "B", slides: [{ t: "b0" }] },
  { id: "c", name: "C", slides: [] },
];
const titles = (chs, id) => chs.find((c) => c.id === id).slides.map((s) => s.t);

test("moveSlide forward within a chapter: slot is in the original list", () => {
  const chs = mk();
  assert.deepEqual(M.moveSlide(chs, { chapterId: "a", index: 0 }, { chapterId: "a", slot: 3 }), { chapterId: "a", index: 2 });
  assert.deepEqual(titles(chs, "a"), ["a1", "a2", "a0"]);
});

test("moveSlide backward within a chapter", () => {
  const chs = mk();
  M.moveSlide(chs, { chapterId: "a", index: 2 }, { chapterId: "a", slot: 0 });
  assert.deepEqual(titles(chs, "a"), ["a2", "a0", "a1"]);
});

test("dropping a slide onto its own slot or the slot right after it is a no-op", () => {
  const chs = mk();
  assert.equal(M.moveSlide(chs, { chapterId: "a", index: 1 }, { chapterId: "a", slot: 1 }), null);
  assert.equal(M.moveSlide(chs, { chapterId: "a", index: 1 }, { chapterId: "a", slot: 2 }), null);
  assert.deepEqual(titles(chs, "a"), ["a0", "a1", "a2"]);
});

test("moveSlide between chapters, into the middle, an empty chapter and the end", () => {
  const chs = mk();
  M.moveSlide(chs, { chapterId: "a", index: 1 }, { chapterId: "b", slot: 0 });
  assert.deepEqual([titles(chs, "a"), titles(chs, "b")], [["a0", "a2"], ["a1", "b0"]]);
  M.moveSlide(chs, { chapterId: "a", index: 0 }, { chapterId: "c", slot: 0 });
  assert.deepEqual(titles(chs, "c"), ["a0"]);
  M.moveSlide(chs, { chapterId: "b", index: 0 }, { chapterId: "c", slot: 99 }); // clamped
  assert.deepEqual(titles(chs, "c"), ["a0", "a1"]);
});

test("moving the last slide out leaves an empty chapter, slide count is conserved", () => {
  const chs = mk();
  M.moveSlide(chs, { chapterId: "b", index: 0 }, { chapterId: "a", slot: 1 });
  assert.equal(chs[1].slides.length, 0);
  assert.equal(chs.reduce((n, c) => n + c.slides.length, 0), 4);
});

test("moveSlide rejects unknown chapters and bad indexes without mutating", () => {
  const chs = mk();
  assert.equal(M.moveSlide(chs, { chapterId: "zz", index: 0 }, { chapterId: "a", slot: 0 }), null);
  assert.equal(M.moveSlide(chs, { chapterId: "a", index: 7 }, { chapterId: "b", slot: 0 }), null);
  assert.equal(M.moveSlide(chs, { chapterId: "a", index: 0 }, { chapterId: "zz", slot: 0 }), null);
  assert.deepEqual(titles(chs, "a"), ["a0", "a1", "a2"]);
});

test("insertSlide at a slot, clamped, unknown chapter", () => {
  const chs = mk();
  assert.deepEqual(M.insertSlide(chs, "a", 1, { t: "new" }), { chapterId: "a", index: 1 });
  assert.deepEqual(titles(chs, "a"), ["a0", "new", "a1", "a2"]);
  M.insertSlide(chs, "c", 50, { t: "x" });
  assert.deepEqual(titles(chs, "c"), ["x"]);
  assert.equal(M.insertSlide(chs, "nope", 0, { t: "y" }), null);
});

test("moveChapter forward, backward and no-op", () => {
  const chs = mk();
  assert.equal(M.moveChapter(chs, "a", 3), true);
  assert.deepEqual(chs.map((c) => c.id), ["b", "c", "a"]);
  assert.equal(M.moveChapter(chs, "a", 0), true);
  assert.deepEqual(chs.map((c) => c.id), ["a", "b", "c"]);
  assert.equal(M.moveChapter(chs, "b", 1), false);
  assert.equal(M.moveChapter(chs, "b", 2), false);
  assert.equal(M.moveChapter(chs, "zz", 0), false);
});

test("stepSlide: left/right within chapter, up/down across chapters, boundaries", () => {
  const chs = mk();
  assert.deepEqual(M.stepSlide(chs, { chapterId: "a", index: 1 }, "left"), { chapterId: "a", index: 0 });
  assert.deepEqual(titles(chs, "a"), ["a1", "a0", "a2"]);
  assert.deepEqual(M.stepSlide(chs, { chapterId: "a", index: 1 }, "right"), { chapterId: "a", index: 2 });
  assert.deepEqual(titles(chs, "a"), ["a1", "a2", "a0"]);
  assert.equal(M.stepSlide(chs, { chapterId: "a", index: 0 }, "left"), null);
  assert.equal(M.stepSlide(chs, { chapterId: "a", index: 2 }, "right"), null);
  assert.equal(M.stepSlide(chs, { chapterId: "a", index: 0 }, "up"), null);
  assert.deepEqual(M.stepSlide(chs, { chapterId: "a", index: 2 }, "down"), { chapterId: "b", index: 0 });
  assert.deepEqual(titles(chs, "b"), ["a0", "b0"]);
  assert.deepEqual(M.stepSlide(chs, { chapterId: "b", index: 1 }, "up"), { chapterId: "a", index: 2 });
  assert.equal(M.stepSlide(chs, { chapterId: "c", index: 0 }, "down"), null);
});
