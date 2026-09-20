# LocateAnything

A Windows desktop app that finds objects in photos using natural-language prompts — powered by a locally-running, quantized vision-language model (no cloud, no API keys, fully offline).

> **Built on top of [locate-anything.cpp](https://github.com/mudler/locate-anything.cpp) by [mudler](https://github.com/mudler)** — the underlying C++ inference engine and CLI are their work. This repo adds a Python + PySide6 desktop GUI on top of that engine. The original engine's license is preserved in [LICENSE](./LICENSE); please refer to the upstream repo for the engine's own documentation and license terms.

![Python](https://img.shields.io/badge/python-3.11-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Offline](https://img.shields.io/badge/inference-100%25%20local-orange)

---

## What it does

Type what you're looking for — a person, an object, an item of clothing, almost any short phrase — and LocateAnything finds it in your photo(s) and draws a bounding box around it. Works on a single image, or an entire folder at once.

**Example use cases:**
- Find lost items — scan room photos for "keys", "wallet", "remote"
- Home security — scan camera snapshots for "person" or "vehicle"
- Retail shelf audits — batch-scan shelf photos for a product name
- Safety compliance — scan site photos for "helmet" to spot missing gear
- Event photo sorting — group photos by "cake", "banner", etc.
- Parking/crowd counting — batch-scan for "car" or "person" counts
- Accessibility mapping — locate "staircase", "ramp", or "door" in photos

## Features

- 🔍 **Custom prompts** — search for anything, not just a fixed object list
- 🖼️ **Single image mode** — pick one photo, get an annotated result instantly
- 📁 **Batch folder mode** — scan an entire folder at once, with live progress and a total detection count, saving annotated copies to a `detections_output` subfolder
- ⚡ **Automatic image resizing** — large photos are safely downscaled before inference (and detection coordinates are rescaled back to full resolution), preventing memory crashes on high-res images
- 🎨 **Dark themed UI** with a one-time welcome/use-case screen
- 💻 **Runs entirely on CPU** — no GPU required (tested on Intel i5-10210U, 8GB RAM)

## Screenshots

*(Add a screenshot or two here — e.g. the welcome screen and a detection result)*

## Tech stack

- **Model:** LocateAnything-3B, quantized (Q4_K / GGUF format)
- **Inference engine:** `locate-anything.cpp` (compiled C++ CLI)
- **GUI:** Python 3.11 + PySide6 (Qt)
- **Image handling:** Pillow

## How it works (architecture)

```
GUI (PySide6)
   │
   ▼
locate_engine.py  ──subprocess──▶  locate-anything-cli.exe  ──▶  GGUF model
   │
   ▼
JSON detections → scaled back to original image size → drawn with Pillow
```

The GUI never talks to the model directly — it calls a small, reusable Python wrapper (`locate_engine.py`) that launches the CLI as a subprocess, parses its JSON output, and hands back clean detection data. This separation means the same engine function powers both single-image and batch modes without duplicating logic.

## Installation

**Requirements:** Windows, Python 3.10+, a compiled `locate-anything.cpp` build with a GGUF model (see the main repo for build instructions).

```powershell
cd python-app
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install pillow PySide6
```

Update the two path constants at the top of `locate_engine.py` to match your local paths for the compiled `.exe` and `.gguf` model file.

## Usage

```powershell
python main_app.py
```

- **Single image:** Choose Image → type a prompt → Run Detection
- **Batch folder:** Choose Folder → type a prompt → Run Batch Detection

## A real debugging story

Early on, running detection on a high-resolution phone photo (~8MB) silently returned zero detections in the default mode, and crashed outright with a ~41GB memory allocation request in `--mode slow`. The cause: the model performs best on images resized to a moderate resolution (≤1024px) — feeding it a much larger image either produced poor results or triggered excessive memory use.

**Fix:** `locate_engine.py` now automatically downscales any image over 1024px before inference, then mathematically rescales the returned bounding box coordinates back to match the original image's full resolution — so detection stays reliable regardless of input photo size, with zero extra work required from the caller.

A second issue surfaced during batch processing: running detection back-to-back across many images with no pause pinned the CPU long enough to starve a low-level Windows display-power thread, triggering a `WIN32K_POWER_WATCHDOG_TIMEOUT` (bugcheck `0x19C`) system crash. Batch mode now uses a reduced thread count and a short cooldown pause between images to keep the system stable during long runs.

## Known limitations

- This is a **grounding model** (find *this specific thing*), not a general image classifier — it won't spontaneously describe everything in a photo; you always provide the search term.
- CPU-only inference is slow on lower-end hardware; batch mode intentionally trades speed for system stability.

## Roadmap / ideas

- [ ] Multi-prompt scanning (comma-separated list of search terms in one run)
- [ ] Packaging as a standalone `.exe` (PyInstaller)
- [ ] Background threading so the UI stays fully responsive during batch runs

## License

*(Add your license here — e.g. MIT, or match the base repo's license)*
