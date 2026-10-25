# Independent DC verification

The included `spice_report.json` records an actual ngspice-42 run. All 29 configurations pass 293 comparisons with CircuitScope and the applicable fixed hand references. The report records its generation time, source hashes, model assumptions, simulator/environment versions and tolerances.

- `spice/ngspice/`: 29 ngspice-format operating-point decks that were run.
- `spice/ltspice/`: 29 LTspice-format decks for the same configurations. LTspice itself was not run.
- `drawing`: original reference circuit, including its load.
- `open_port`: remove the selected external load, keep the remaining circuit active.
- `resistance_test`: remove the selected load, deactivate independent V/I sources and inject 1 A into the port. Port voltage divided by 1 A is the equivalent resistance.

Feedback amps use gain 1e9 in SPICE rather than the app's infinite-gain constraint. Both keep zero input current and zero output resistance. Comparator B expressions preserve the HIGH/LOW levels, but raw SPICE equality handling differs from CircuitScope's threshold guard. No manufacturer models or physical amplifier dynamics are covered.

The app displays this report only while its relevant source hashes match. To refresh it after a solver/reference/export change, run `py spice_validate.py --ngspice PATH_TO_YOUR_EXECUTABLE` from the project folder. This rewrites the report and decks. The app does not require a simulator installation and never launches one from the web page.

See [`docs/spice-validation.md`](../docs/spice-validation.md) for export controls, comparison tolerances and limitations.

The separate **browser_report.json** records real headless Chromium workflows against the live Streamlit app, with browser/platform information and source hashes. See [`docs/browser-tests.md`](../docs/browser-tests.md) for reproduction and limits. This report does not establish native Windows or physical touch behavior.
