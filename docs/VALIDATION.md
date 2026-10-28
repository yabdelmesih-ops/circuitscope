# SPICE validation and tests

## Electrical comparison

`validation/spice_report.json` records an ngspice-42 run: 29 configurations and
293 numerical comparisons, all passing. The configurations use the original
11 reference circuits, their applicable open-port cases and 1 A resistance tests.
The seven additional Circuits I examples have fixed hand-calculation and KCL
checks; they are not part of that ngspice report.

The largest voltage difference was about 6 nV. This is a voltage metric;
the 293 comparisons also include currents and resistance. SPICE approximates
an ideal feedback amp with gain 1e9, while CircuitScope imposes infinite-gain
input equality. Comparator threshold equality is undefined in CircuitScope.
Neither model establishes real amplifier behavior.

The report records source hashes and tolerances. The app hides it if its
relevant sources change. The original solver/export/reference files are unchanged
in this version. To rerun after installing ngspice:

```powershell
py spice_validate.py --ngspice "C:\path\to\ngspice.exe"
```

This rewrites the report and decks in `validation/spice/ngspice` and
`validation/spice/ltspice`. Only ngspice was run; the LTspice decks are exports.
No numerical solver mismatch was documented in that run.

## Automated checks

This version passed 112 Python tests (two optional native ngspice tests skipped),
39 JavaScript tests and all 16 live browser workflow checks.

From the project folder, with Python, Node.js and Edge installed:

```powershell
py -m unittest discover -s tests -q
npm install
npm test
npm run test:browser
```

The Python tests cover numerical results, topology, invalid circuits, methods,
exports and Streamlit integration. Optional native ngspice tests skip when its
executable is absent. JavaScript tests cover editor state and DOM interaction.

The Playwright browser suite starts a local Streamlit server, uses real mouse,
keyboard and drag-and-drop interactions, checks displayed answers and downloads,
and writes `validation/browser_report.json`. It defaults to Edge on Windows and
Chrome elsewhere. Set `CIRCUITSCOPE_BROWSER_CHANNEL` or
`CIRCUITSCOPE_BROWSER_EXECUTABLE` for another installed Chromium browser.
Node dependencies are needed only for developer tests.

Browser testing exposed duplicated listeners after rerenders, lost Undo history
when conditional controls remounted the editor, layout overflow and moving
terminal targets during wire gestures. The fixes retire old listeners, preserve
a stable canvas position, bound its height and defer layout changes during a
wire gesture. These were interface bugs, not numerical solver corrections.

The browser report includes platform, browser version and source hashes. Its
headless Linux run and narrow-window checks do not establish native Windows,
physical touch, Safari or Firefox behavior. Reports cover the tested cases,
not every possible circuit.
