/* Pure reordering logic for the Builder's chapters, kept free of DOM and
 * state so it can be unit-tested with plain Node (tests/js). Every function
 * mutates the given `chapters` array in place.
 *
 * "Slot" means an insertion position in the ORIGINAL list, 0..length: slot 0
 * is before the first item, slot `length` is after the last. Callers (drag
 * and drop, keyboard) can therefore pass "before/after the item under the
 * cursor" without worrying about index shifts caused by removing the item. */
(function (root) {
  "use strict";

  const findChapter = (chapters, id) => chapters.find((c) => c.id === id);

  const clampSlot = (slot, length) => Math.max(0, Math.min(slot, length));

  /** Insert a new slide object into a chapter. Returns its position or null. */
  function insertSlide(chapters, chapterId, slot, slide) {
    const ch = findChapter(chapters, chapterId);
    if (!ch) return null;
    const index = clampSlot(slot, ch.slides.length);
    ch.slides.splice(index, 0, slide);
    return { chapterId, index };
  }

  /** Insert several slides, in order, starting at a slot. Returns the first one's position or null. */
  function insertSlides(chapters, chapterId, slot, slides) {
    const ch = findChapter(chapters, chapterId);
    if (!ch || !slides.length) return null;
    const start = clampSlot(slot, ch.slides.length);
    ch.slides.splice(start, 0, ...slides);
    return { chapterId, index: start };
  }

  /** Move a slide to a slot in the same or another chapter.
   *  Returns the slide's new position, or null if nothing changed. */
  function moveSlide(chapters, from, to) {
    const src = findChapter(chapters, from.chapterId);
    const dst = findChapter(chapters, to.chapterId);
    if (!src || !dst || from.index < 0 || from.index >= src.slides.length) return null;

    let slot = clampSlot(to.slot, dst.slides.length);
    if (src === dst && slot > from.index) slot -= 1; // removal shifts later slots down
    if (src === dst && slot === from.index) return null;

    const [slide] = src.slides.splice(from.index, 1);
    dst.slides.splice(slot, 0, slide);
    return { chapterId: dst.id, index: slot };
  }

  /** Move a chapter to a slot in the chapter list. Returns true if it moved. */
  function moveChapter(chapters, chapterId, slot) {
    const from = chapters.findIndex((c) => c.id === chapterId);
    if (from < 0) return false;
    let target = clampSlot(slot, chapters.length);
    if (target > from) target -= 1;
    if (target === from) return false;
    const [ch] = chapters.splice(from, 1);
    chapters.splice(target, 0, ch);
    return true;
  }

  /** Keyboard nudge. left/right reorder within the chapter; up/down send the
   *  slide to the end of the previous / start of the next chapter.
   *  Returns the new position, or null at a boundary. */
  function stepSlide(chapters, pos, direction) {
    const ci = chapters.findIndex((c) => c.id === pos.chapterId);
    if (ci < 0) return null;
    const ch = chapters[ci];
    if (direction === "left" && pos.index > 0) {
      return moveSlide(chapters, pos, { chapterId: ch.id, slot: pos.index - 1 });
    }
    if (direction === "right" && pos.index < ch.slides.length - 1) {
      return moveSlide(chapters, pos, { chapterId: ch.id, slot: pos.index + 2 });
    }
    if (direction === "up" && ci > 0) {
      const prev = chapters[ci - 1];
      return moveSlide(chapters, pos, { chapterId: prev.id, slot: prev.slides.length });
    }
    if (direction === "down" && ci < chapters.length - 1) {
      return moveSlide(chapters, pos, { chapterId: chapters[ci + 1].id, slot: 0 });
    }
    return null;
  }

  const api = { insertSlide, insertSlides, moveSlide, moveChapter, stepSlide };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BuilderModel = api;
})(typeof self !== "undefined" ? self : this);
