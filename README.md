# Slide Library

A local application for a personal or team slide repository: point it at the
folders where your PowerPoint/PDF decks live, it full-text indexes every
slide and renders a real thumbnail for each one, lets you browse by domain
and search across everything, and lets you drag slides from any deck into
chapters of a brand-new deck — then exports that as a real .pptx. Native
PowerPoint slides come in fully editable; PDF-sourced slides (and any
PowerPoint slide with a chart, SmartArt or embedded object the exporter
can't safely rebuild) come in as a full-bleed image of that slide instead.

It runs entirely on your own machine — nothing is uploaded anywhere. The
index (a SQLite database) and slide thumbnails live in `data/`.

## 1. Install

You need Python 3.10+ and LibreOffice (free) — LibreOffice is what actually
renders slide thumbnails and re-lays-out a PowerPoint file so its pages can
be rasterized; there's no way to draw a slide's real layout, or copy one
slide's exact formatting into another deck, without an engine that
understands the format.

**macOS**
```
brew install --cask libreoffice
```
(or download from libreoffice.org — either way, this installs the `soffice`
command the app calls)

**Windows**
Download and install LibreOffice from https://www.libreoffice.org/download/ .
Make sure the installer adds it to your PATH, or note the install folder
(typically `C:\Program Files\LibreOffice\program`) — if `soffice` isn't on
your PATH, add that folder to it.

**Linux**
```
sudo apt install libreoffice        # Debian/Ubuntu
sudo dnf install libreoffice        # Fedora
```

Then, from this folder:
```
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Try it with sample data (optional but recommended)

```
python scripts/make_samples.py
python run.py
```
This opens your browser at http://127.0.0.1:8420 . Go to **Manage sources**
→ **Add directory** and add the three folders the script printed (each as
its own domain: Strategy, Architecture, Projects) to see indexing,
thumbnails, search and export all work end to end before pointing it at
your real files.

## 3. Point it at your real slide library

In **Manage sources**, add each top-level domain folder from your file
share (one directory + one domain name per entry — e.g.
`/Volumes/Shares/Strategy` → domain `Strategy`, or on Windows
`\\fileshare\Architecture` → domain `Architecture`). Click **Browse…** to
pick the folder from a native folder picker instead of typing the path —
this opens a normal OS dialog because the app and your browser tab are
running on the same machine. If **Browse…** reports it can't open a picker
(most likely on Linux without `python3-tk` installed, or Homebrew Python on
macOS — `brew install python-tk`), just type or paste the path instead;
everything else still works. Indexing runs in the background; the folder's
status chip shows progress and flips to **Indexed** when done. Click
**Re-index** any time after files change on disk — only new or changed
files are reprocessed, so it's fast after the first run.

Then: browse by domain, search across every deck's actual slide text, open
a deck to see its slides, then drag slides (from a deck, from search hits
or from your favorites) straight into the **deck panel** on the right, and
**Export .pptx** when the deck is ready.

### Favorites

Click the star on any slide — in a deck, in search hits or in the favorites
list — to mark it a favorite; click it again to unmark it. Favorites
survive re-indexing (matched by slide text, so reordering or inserting slides
doesn't move them; a slide edited in place keeps its star while the slide
count is unchanged), so they won't disappear when files change on disk.

The **★ Favorites** toggle above the deck grid has two modes:

- **Favorites alone** (no file type selected) lists the starred slides
  themselves, grouped by domain. Click a slide to open its deck, or its star
  to unmark it. The sidebar domain and the search box still apply.
- **Favorites plus PPTX and/or PDF** lists the decks of that type that
  contain at least one starred slide.

Turning Favorites on clears the type toggles (and restores them when you turn
it off again if you haven't picked a type in the meantime).

## Running it day to day

```
source .venv/bin/activate
python run.py
```
Leave it running in a terminal (or terminal tab) while you use it in the
browser; close the terminal (or Ctrl+C) to stop it. Your index and
thumbnails persist in `data/` between runs — nothing needs reindexing
unless the files themselves changed.

## Zoom and layout

The **− 100% +** control in the top bar scales the thumbnails and cards in the
library and deck views (50–200%, in steps); click the percentage to reset to
100%. The **divider** between the library and the deck panel can be dragged
with the mouse (or focused and moved with ← / →, Shift for larger steps;
double-click resets it to the default width). Both settings are remembered in
your browser, and the panel width is limited so the library always keeps a
usable area.

## Building and saving decks

The **deck panel** on the right of the library (toggle it with **New deck** /
**Hide deck**) is where a new deck takes shape, so you can drag slides
directly from what you're browsing on the left:

- **Where to drag from:** slide thumbnails in an open deck (click several to
  select them, then drag any one to move the whole selection), the
  **Matching slides** shown above the decks when you search, and the starred
  slides in the Favorites view. "Add to deck" / "Add all" do the same without
  dragging.
- **Where to drop:** onto a slide in a chapter to insert before/after it, onto
  a chapter's empty area to append, or onto **Drop slides here for a new
  chapter** to create a chapter named after the source deck.
- **Reordering:** drag slides within a chapter or into another chapter, and
  drag a chapter by its grip (⠿) to reorder chapters. Keyboard: focus a slide
  and press **Alt + ←/→** to move it within its chapter, **Alt + ↑/↓** to send
  it to the previous/next chapter.

**Name your deck** in the field at the top of the panel and optionally give it
a **category**; **Save** (or Ctrl/Cmd+S) then stores it server-side in
`data/library.db` — saving is refused until the deck has a name. **Open
saved** lists your saved decks, **New** starts a blank one. The status shows
*Saved*, *Unsaved changes* or *Not saved yet*. Between saves the panel keeps a
working copy in your browser, so a reload never loses edits.

In **Saved decks** (also in the sidebar) decks are grouped by category, with
filter chips to show one category. The pencil renames a deck and changes its
category (pick an existing one or type a new one; leave it empty for
*Uncategorized*) without touching its slides; each deck has at most one
category.

A saved deck stores *references* to library slides, not copies. Opening it
always shows the current thumbnails and titles; if a slide's source file was
removed or shortened since, that slide appears as **Missing** and is skipped
on export (the rest of the deck is unaffected).

## What to know about fidelity

- **PDF-sourced slides always export as an image.** There's no reliable
  general way to reconstruct a PDF page back into editable PowerPoint text
  boxes and shapes — the mockup you saw first, and this app, both made that
  trade-off deliberately rather than attempting a flaky reconstruction.
- **Native PowerPoint slides export fully editable** — text, images,
  tables, positioning and most formatting carry over exactly. Two things
  don't: (1) a slide with a chart, SmartArt diagram, or embedded object
  (e.g. an embedded Excel range) falls back to an image, because safely
  reproducing those would mean copying their separate data parts too, and a
  half-copied chart is worse than a clean image; (2) if a slide leans
  entirely on its original template's master/theme for styling it never set
  explicitly (an inherited background or placeholder color), that specific
  inherited styling won't carry over — everything the slide sets itself
  does.
- **The full-text index** covers every text box, table cell, and (for PDFs)
  extracted page text. It does not OCR text baked into images.

## Security notes

The server binds to 127.0.0.1 only and rejects requests whose `Host` is not
`localhost`/`127.0.0.1`/`::1` (DNS-rebinding defence) and state-changing
requests carrying a foreign `Origin` (CSRF defence) — the API can register
arbitrary folders and open native dialogs, so other browser tabs must not be
able to drive it. To reach it under another hostname (e.g. via a reverse
proxy), set `SLIDELIB_ALLOWED_HOSTS=name1,name2`.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest                    # backend
node --test tests/js/*.test.js      # deck-panel reorder logic (Node 18+, no npm install)
```
Tests use throwaway databases and never touch `data/`; LibreOffice is stubbed
so they run without it.

## Project layout

```
app/            FastAPI backend
  main.py         API routes + serves the frontend
  db.py           SQLite schema and queries (data/library.db)
  indexer.py      Walks folders, extracts text, renders thumbnails
  pptx_copy.py    Low-level native slide copy (OOXML)
  exporter.py     Builds the exported .pptx from chapters
  drafts.py       Resolves saved Builder decks against the live index
  folder_picker.py  Native folder dialog, run out-of-process
tests/          pytest suite (db, pptx copy, exporter, API, drafts) + tests/js
static/         Frontend (no build step — plain HTML/CSS/JS)
  builder-model.js  Pure chapter/slide reorder logic (unit-tested)
  view-model.js     Pure zoom steps and panel-width clamping (unit-tested)
scripts/        make_samples.py — generates a try-it-now sample library
data/           Created at runtime: library.db + thumbnails/ (gitignored)
```
