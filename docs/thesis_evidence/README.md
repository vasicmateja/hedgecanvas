# Thesis Evidence Package

Product evidence for later Chapter 6 integration, prepared during the
final QA/presentation-polish pass on commit `70039a7` and after.
**This directory contains no thesis prose and no raw research datasets.**

## Contents

| File | What it is |
|---|---|
| [`QA_LOG.md`](QA_LOG.md) | Exact values, timestamps, and states observed live during final QA against the real public Deribit API and the real canonical historical artifacts. |
| [`MANUAL_SCREENSHOT_CHECKLIST.md`](MANUAL_SCREENSHOT_CHECKLIST.md) | Step-by-step instructions to capture the 6-7 representative application-state screenshots as real image files (see below for why no `.png` files are included here). |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Concise, as-implemented architecture description with a Mermaid diagram of the two hard-separated data paths (live and historical). |

## Screenshot status: MANUAL CHECKLIST PREPARED

No `.png` files are included in this package. The internal browser tool
used during QA can render and inspect the running app, but has no
mechanism to export a screenshot as a file on this machine's disk --
only as an inline image within that tool session. Rather than add a
browser-automation dependency to this project purely to solve image
export, every required state was instead verified live (see
`QA_LOG.md` for the exact recorded values) and a precise manual
checklist was prepared so a person with an ordinary desktop screenshot
tool can reproduce each image in a few minutes.

## Live vs. historical evidence

Anything captured from the **Live Designer** is a product demonstration
against real, currently-changing Deribit market data -- it is not
reproducible research evidence, and a later capture will show different
numbers. Anything captured from **Historical Backtest** reflects the
frozen 2020-01 to 2024-12 production sample (Run ID
`0cc87d60337032ec493534d312fc84734c5a4ae6a34b5687424f0761937d6132`) and
should be identical on any future capture against the same canonical
artifacts, verifiable via the "Verified frozen thesis evidence" badge
and the provenance expander shown in the app itself.

## No secrets, no raw datasets

This package intentionally excludes: the canonical CSV files themselves
(see the main README's Phase 4 section for where a reader should place
them locally), any API keys (none exist in this project), and any
personal or account information (none exists in this project -- Deribit
access is public-only).
