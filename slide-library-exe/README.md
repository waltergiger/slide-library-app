# Slide Library as a Windows .exe

Packages the app into a single `SlideLibrary.exe` (PyInstaller). Nothing is
copied from the main project: the spec builds from `../app` and `../static`,
so keep this folder inside the repository.

## Get the .exe

**A) Build on any Windows machine** (Python 3.10+ from python.org):
```
cd slide-library-exe
build.bat            :: single file  -> dist\SlideLibrary.exe
build.bat onedir     :: folder       -> dist\SlideLibrary\SlideLibrary.exe (starts faster, fewer antivirus false positives)
```

**B) Let GitHub build it** (no Windows machine needed — PyInstaller cannot
cross-compile, so an .exe can only be produced on Windows):
push the repo, open **Actions → Build Windows EXE → Run workflow**, and download
the `SlideLibrary-windows` artifact. The workflow also smoke-tests the exe
(starts it, checks the API and bundled UI) before publishing it.

## Running it

Double-click `SlideLibrary.exe`. A console window opens and shows the address;
your browser opens at http://127.0.0.1:8420. **Close the console window (or
Ctrl+C) to quit.** Starting it a second time just opens the browser on the
running instance.

| | |
|---|---|
| **Index, thumbnails, saved decks** | `%LOCALAPPDATA%\SlideLibrary\data\` (survives updates — replace the exe freely) |
| **LibreOffice** | Required for thumbnails and the image fallback; **not** bundled (it's ~350 MB). Install it from libreoffice.org — the app finds it in `Program Files` automatically. Without it the app still runs and indexes text, and shows a warning banner. |
| **Port / paths** | env vars: `SLIDELIB_PORT` (default 8420), `SLIDELIB_DATA_DIR`, `SLIDELIB_SOFFICE` (path to `soffice.exe`), `SLIDELIB_NO_BROWSER=1` |

## Good to know

- **Unsigned binary.** Windows SmartScreen ("Windows protected your PC" → *More info → Run anyway*) and some antivirus products flag unsigned PyInstaller apps. For anything beyond personal use, sign it with a code-signing certificate; on a managed bank workstation it may also need an allow-listing request.
- **Single-file start-up** unpacks to `%TEMP%` each launch (a few seconds). Use `onedir` if that bothers you.
- The server binds to `127.0.0.1` only and validates Host/Origin headers; it is not reachable from other machines.
- **What was verified where:** the identical spec was built and run as a native macOS binary (static UI, indexing with PyMuPDF and LibreOffice, search, PPTX export incl. the python-pptx template, saved decks, data location). The Windows-specific parts — the PowerShell folder dialog, `os.startfile`, the console behaviour — are covered by unit tests and by the CI smoke test, but were not run on real Windows by the author.
