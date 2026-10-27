# Browser tests

`tests/browser-smoke.mjs` is an end-to-end suite that drives the real Streamlit app in Chromium using Playwright. It uses real mouse clicks, keyboard input and HTML drag-and-drop, then reads the answers computed by Python and the files the app downloads. Nothing is mocked, and no prebuilt drawing is injected into the editor.

The committed report, `validation/browser_report.json`, records **19/19 workflow checks passing** in headless Linux Chromium, with no client-side JavaScript errors.

## What is covered

- Empty startup, with the editor staying inside its allotted space
- Dragging parts from the inventory and wiring terminals, with the drawing reaching Python
- Explain-node clicks producing a live visual lesson
- Property edits and Undo invalidating and recalculating results
- Wire branching creating a single junction, and an unloaded probe reading its voltage
- Cancelling a pending wire, clearing, and Undo without losing the saved drawing
- The SPICE download containing the current full circuit
- A feedback op amp with a removed load, solved through the browser
- Open-loop HIGH, LOW and equal-input handling with no stale result
- Inspecting the independent SPICE report
- Lesson and op-amp property panels staying in bounds at tablet and phone widths (1024 and 390 px)
- Guided practice: unit handling, a hint request, an equivalent answer in millivolts, optional reveal, signed current in milliamps, and grading disabled after a component value changes
- Circuits I methods: supernode highlighting and invalidation after an edit, source contributions, divider and source-transformation loading, both summing amplifiers and a feedback cascade
- Screenshot import: uploading a valid PNG and using the offline review demo to check required approval and editable loading (no live vision API call)
- No client-side JavaScript errors across all workflows

## Bugs found and fixed

Running the suite against the live app exposed four issues that unit and DOM tests had missed:

1. **Duplicate event listeners.** Each Streamlit update attached another set of canvas listeners, so one click could reach several handlers. The editor now stores its cleanup on the root element and uses an `AbortController` to remove the previous listeners and cancel any queued animation frame before rendering new data.
2. **Lost undo history.** Conditional question and lesson widgets could shift the canvas to a different Streamlit element position, which remounted it and discarded local history. Those controls now live in one stable container.
3. **Editor overflow.** A percentage height inside Streamlit's auto-height wrapper let the editor grow past its space. It now stays within its configured 820 px height and scrolls where needed.
4. **Coordinate shift mid-gesture.** A collapsing property form or an incoming lesson panel could change the SVG coordinate transform while a wire was being dragged. The editor now holds that layout steady until the gesture ends.

## Running it

```bash
pip install -r requirements.txt
npm install
npm test               # unit and DOM tests
npm run test:browser   # end-to-end browser suite
```

The browser command starts its own Streamlit server on a free port and stops it when finished. It overwrites `validation/browser_report.json` with the result of the run. To test an already-running server, use `npm run test:browser -- --url http://localhost:8501`.

No browser is downloaded. On Windows the suite defaults to the `py` launcher and Microsoft Edge. Environment variables override the defaults:

| Variable | Effect |
|---|---|
| `CIRCUITSCOPE_PYTHON` | Python executable used to start Streamlit |
| `CIRCUITSCOPE_BROWSER_CHANNEL` | Installed browser channel, e.g. `chrome` |
| `CIRCUITSCOPE_BROWSER_EXECUTABLE` | Explicit browser path |

## Report and limits

The report records the browser version, platform, time, each named check with its duration, any client errors, and SHA-256 hashes of the app and test sources. A failing run names the failing check.

The recorded run is headless Linux Chromium. Native Windows behavior, physical touch input, Safari and Firefox are not covered, and the 390 px check is a narrow viewport rather than a real phone.
