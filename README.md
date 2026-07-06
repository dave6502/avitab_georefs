# Avitab Georef Management for UK AIP Charts

## Overview

This project provides a set of Python scripts for downloading, organising, and helping to manage the georeferencing of UK NATS AIP  chart PDFs for use with Avitab. It is designed for maintaining a local library of UK aeronautical charts that can be updated cycle by cycle.

The workflow is built around AIRAC cycles, which are updated every 28 days. The scripts help you:

- download the latest UK AIRAC chart package
- reorganise the downloaded PDFs into a consistent folder structure
- reuse existing georeferencing metadata when chart content has not changed
- identify which changed charts are likely to need manual georeferencing
- package georeferences for distribution

This repository is aimed at UK airspace data (EG region) and is intended for users who want to keep Avitab-compatible chart georeferences current.

The recommended release strategy is to release a pair of AIRAC cycles each month - e.g. 2607_2608. 2607 contains all georefs for 2607. 2608 contains only georefs for updated PDFs. Releases overlap, so the next release would be 2608_2609. This allow a 28 day AIRAC 2608 window in which the latest 2608_2609 release can be georeferenced and uploaded such that Avitab users always have the relevant georef metadata for the current AIRAC cycle.

## Quick start

Clone the git repo:
```bash
git clone https://github.com/dave6502/avitab_georefs
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The easiest way to begin is to use the main update workflow script:

```bash
python scripts/start_update.py 2608
```

This script performs the following steps for the requested AIRAC cycle:

1. downloads the previous AIRAC cycle
2. reorganises the previous charts
3. copies matching georeferences from the previous cycle
4. downloads the new AIRAC cycle
5. reorganises the new charts
6. copies matching georeferences to the new cycle
7. starts the interactive similar-chart review tool if any charts still need manual review
8. shows the current georeference status

If you run start_update.py, it will fetch georeference data from the TeamAvitab GitHub repository automatically, so there is no need to obtain a separate georef bundle elsewhere before using this workflow.

## Requirements

### Supported environments

Tested on WSL2, but the Python is OS-agnostic so Windows, macOS and Linux should also work. WSL2 is recommended due to its native GUI support. WSL 1 (with e.g. XServer setup) is not recommended for the copy_similar_georefs_gui.py script. The MinGW environment that can be used for building Avitab itself is not supported.

### Python

- Python 3.7 or newer is recommended

### Third-party Python libraries

The scripts depend on the following packages:

- requests
- beautifulsoup4
- pymupdf
- Pillow

Install them with:

```bash
pip install -r requirements.txt
```

## Folder structure

The repository is organised as follows:

```text
charts/
    EG_AIRAC_2606/
    EG_AIRAC_2607/
    EG_AIRAC_2608/
    ...

scripts/
    download.py
    reorganise.py
    copy_matching_georefs.py
    copy_similar_georefs_gui.py
    status.py
    package.py
    start_update.py
    pdf2png.py

src/
    __init__.py
    airac.py
    utils.py

georefs/
    TeamAvitab...
```

### charts/

This folder contains the chart data organised by AIRAC cycle. Each cycle directory contains the downloaded and reorganised chart tree, including subfolders for aerodromes and chart types. This is created on first run.

### scripts/

This folder contains the executable workflow scripts. These are the main entry points for downloading, reorganising, copying georeferences, checking status, packaging, and running the full update workflow.

### src/

This folder contains shared Python modules used by the scripts:

- airac.py — AIRAC cycle parsing and date logic
- utils.py — shared helpers for hashing PDFs and JSON files, working with directories, and downloading/extracting zips

### georefs/

This folder is used for packaged georeference output. The generated bundles are typically grouped by AIRAC range and prepared for Avitab-compatible use. This is created on first packaging run.

## Scripts

The scripts have a shebang, so on appropriately configured Unix environments, they can be run directly without the 'python' call. If this doesn't work, check that line endings are (Linux) LF rather than (Windows) CRLF.

### scripts/download.py

Downloads the AIRAC ZIP package for a given cycle  from the UK NATS AIP and extracts it into the expected chart directory.

Usage example:

```bash
python scripts/download.py 2607
```

### scripts/reorganise.py

Reorganises the chart files into a standard structure grouped by aerodrome and chart type with PDFs renamed more descriptively.

The downloaded AIRAC charts from UK NATS require reorganisation since the raw downloaded PDFs have unhelpful numeric names (e.g. 123456.pdf). Also, organising charts in a deeply structured directory layout (by ICAO code, aerodrome, and chart type) makes the number of files/folders shown in an Avitab page smaller. It's thus quicker to scroll/select through the folder hierarchy when using the Avitab folder browser.

When the PDFs are reorganised/renamed, the aerodrome HTML files are also relinked in the local unzipped UK NATS AIP website. So this can still be browsed offline as normal. 

Usage example:

```bash
python scripts/reorganise.py charts/EG_AIRAC_2607
```

### scripts/copy_matching_georefs.py

Copies georeferencing JSON files from one cycle to another when the PDF content hash matches. This is the automatic, hash-based reuse step.

Usage example:

```bash
python scripts/copy_matching_georefs.py charts/EG_AIRAC_2607 charts/EG_AIRAC_2608````

### scripts/copy_similar_georefs_gui.py

Runs the interactive GUI-based tool for reviewing charts whose content is similar but not identical. This is the manual review step for charts that might still be compatible with old georeferences. See below for further information about how to use the GUI.

Usage:

```bash
python scripts/copy_similar_georefs_gui.py charts/EG_AIRAC_2607 charts/EG_AIRAC_2608`
```

### scripts/status.py

Checks the georeferencing status of the charts in a cycle or cycles and reports which PDFs are missing JSON georeference files or have hash mismatches.

Usage:

```bash
python scripts/status.py charts/EG_AIRAC_2608
```

### scripts/package.py

Packages selected georeference JSON files into a distributable archive.

Usage:

```bash
python scripts/package.py charts/EG_AIRAC_2607 charts/EG_AIRAC_2608
```

### scripts/start_update.py

Runs the complete update workflow for a new AIRAC cycle. This is the recommended entry point for regular updates.

Usage:

```bash
python scripts/start_update.py 2608
```

### scripts/pdf2png.py

Converts a PDF chart to PNG. This is a smaller helper script and is not part of the main workflow. It can be useful if some drawing on the top of a PNG chart helps the Avitab manual calibration process. 
Usage:

```bash
python scripts/pdf2png.py some_chart.pdf
```

## How to operate the copy_similar_georefs_gui.py script

The copy-similar tool is used after the automatic hash-based copy step. It helps you decide whether georeferencing metadata from an older chart can be reused for a newer chart when the chart content has changed slightly.

### When to use it

Use this tool when:

- the automatic hash-based copy did not copy all georeferencing
- you want to review borderline cases manually before calibrating a chart from scratch

### How to launch it

From the repository root, run:

```bash
python scripts/copy_similar_georefs_gui.py charts/EG_AIRAC_2607 charts/EG_AIRAC_2608
```

The first argument is the previous cycle directory, and the second argument is the current cycle directory.

### What the tool does

For each chart pair, the tool compares the old and new chart images and presents:

- a difference view
- the previous chart
- the new chart

It then suggests whether the old georeferencing is likely to be acceptable for the new chart.

### How to interpret the display

The tool shows the current chart pair, the current image view, and a suggestion. The 3 images are shown one at a time as a clickable slideshow, rather than side by side.

- Diff view: highlights the visual differences between the old and new chart
- Old view: shows the previous chart version
- New view: shows the current chart version

### Keyboard controls

Use the following keys while the tool is running:

- Left/Right arrow keys — move between the diff, old, and new views
- a — accept the old georeferencing for the new chart
- r — reject and leave the chart for manual calibration
- s — skip the current chart pair for now
- Enter — use the current suggestion
- q — quit the tool

### Decision guidance

- If the charts are very similar and the diff view is mostly dark or minimal, accepting the old georeferencing is usually reasonable.
- If the charts have changed significantly, or the chart geometry has shifted, reject the match as suggested and plan for manual calibration later.
- If the suggestion is Unknown, it is not possible to [Enter]. The user must decide to accept or reject. It is recommended to switch between previous and current charts to make a decision.
- If the page size or chart layout has changed substantially, the old georeferencing is unlikely to transfer correctly.
- In the majority of cases, it is sufficient to use [Enter] to use the suggestion. However, it is possible to override this by using accept or reject. This will back off to an Unknown suggestion, where it is necessary to resubmit accept or reject.

## Notes

- All scripts use relative paths by default, assuming they are run from the repository root
- Charts are downloaded from the NATS official distribution. Internet access is required for the download phase.
- UK NATS AIP only serves the .zip files for 3 AIRAC cycles at a time - current, next and next + 1. Older .zips are typically not made available. It is essential to update while the 2 (previous and new update cycles) are available on UK NATS AIP.
- The project is specifically oriented to UK (EG) aeronautical charts. However, the scripts could be adapted/refactored for use with other country's AIP charts.
