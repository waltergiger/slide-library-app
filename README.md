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
a deck to see its slides, select slides (or "Add all") to send them to the
**Builder**, add chapters, drag slides from the search panel into them, and
**Export to PowerPoint** when the deck is ready.

### Favorites

Click the star on any slide — in a deck, or in the Builder's search
results — to mark it a favorite; click it again to unmark it. Favorites
survive re-indexing (matched by slide text, so reordering or inserting slides
doesn't move them; a slide edited in place keeps its star while the slide
count is unchanged), so they won't disappear when files change on disk. Back in the library, use the **PPTX** / **PDF**
/ **★ Favorites** toggles above the deck grid to narrow what you're
browsing — turn off a file type to hide it, or turn on Favorites to see
only decks that contain at least one starred slide.

## Running it day to day

```
source .venv/bin/activate
python run.py
```
Leave it running in a terminal (or terminal tab) while you use it in the
browser; close the terminal (or Ctrl+C) to stop it. Your index and
thumbnails persist in `data/` between runs — nothing needs reindexing
unless the files themselves changed.

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
python -m pytest
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
tests/          pytest suite (db, pptx copy, exporter, API)
static/         Frontend (no build step — plain HTML/CSS/JS)
scripts/        make_samples.py — generates a try-it-now sample library
data/           Created at runtime: library.db + thumbnails/ (gitignored)
```
