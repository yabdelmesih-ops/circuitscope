# CircuitScope

**Draw a DC circuit in the browser, solve it with Modified Nodal Analysis, and see *why* every node has its voltage.**

CircuitScope is an interactive circuit solver and teaching tool. You place resistors, sources and op amps on a canvas and wire them together. A Python engine then builds and solves the circuit's system of equations. The result is drawn back onto the schematic as current arrows, highlighted nodes and a step-by-step KCL explanation.

![Inverting op-amp amplifier solved in CircuitScope, with current arrows and node explanation](docs/images/inverting-amplifier.png)
*An inverting amplifier (gain −2). The selected node is Vout. Arrows show the solved branch currents, and the side panel explains each one.*

**[Live demo](https://LINK-TO-YOUR-STREAMLIT-APP)** · Built with Python, NumPy, Streamlit and vanilla JavaScript/SVG

---

## Features

- **Schematic editor.** Drag-and-drop parts, click-to-route wires with manual corners, branch junctions, rotation, undo, and JSON save/load.
- **Modified Nodal Analysis solver** for resistors, independent voltage/current sources and **ideal op amps** with negative feedback.
- **Analyses:** node voltage, open-circuit output voltage, branch current, component power, and **Thévenin / Norton equivalents** between any two nodes.
- **Click-to-explain lessons.** Click any wire or terminal to see the node highlighted, numbered current arrows, the symbolic KCL equation, and a numerical check that currents balance.
- **Input validation** with readable errors for floating nodes, missing ground, shorted sources, conflicting labels, missing op-amp feedback, and outputs that would saturate.
- **Verification suite.** Nine reference circuits are checked against independent hand calculations, plus KCL and power-conservation checks.

---

## How it works

```
 Canvas (JS/SVG)  ──drawing JSON──▶  topology.py  ──netlist──▶  engine.py  ──solution──▶  teaching.py
 parts + wires                      union-find on              build & solve             lessons, arrows,
 with positions                     wired terminals            A·x = b (NumPy)           KCL equations
```

**1. Drawing → netlist (`topology.py`).** Each wire connects two terminal IDs, such as `R1:2` and `U1:1`. A **union-find (disjoint-set)** structure groups connected terminals into electrical nodes, and every ground symbol merges into node `0`. Positions never enter the math: crossing lines don't connect, and moving a part doesn't change the circuit.

**2. Netlist → equations (`engine.py`).** The unknown vector holds every non-ground node voltage, plus one current for each voltage source and each op-amp output. Each component *stamps* its contribution into the matrix `A` and the vector `b`:

| Component | Stamp |
|---|---|
| Resistor | Adds conductance `1/R` to its two node rows (KCL) |
| Current source | Adds its current to `b` at its two nodes |
| Voltage source | Adds a current unknown, plus the constraint row `V(n1) − V(n2) = Vs` |
| Ideal op amp | Adds an output-current unknown at OUT only, plus the constraint row `V(+) − V(−) = 0`. No current enters either input. |

`numpy.linalg.solve` returns all voltages and source currents at once. A singular matrix is reported as "no unique DC solution" instead of silently returning garbage.

**3. Equivalent circuits.** For Thévenin, the engine solves the open-circuit voltage with the load removed. It then deactivates the independent sources (V → short, I → open), injects a 1 A test current across the port, and reads the resulting voltage as R<sub>th</sub>. Op amps stay active during this step, so feedback amplifiers correctly give R<sub>th</sub> = 0.

**4. Op-amp safety checks (`circuit_model.py`).** Before solving, a graph search confirms that each op amp's output reaches its − input through resistors (negative feedback) and does *not* reach its + input. After solving, the output is checked against its rail limits. If it would saturate, the app says so instead of reporting an invalid linear result.

**5. Teaching layer (`teaching.py`).** The lesson is built from the solved circuit. It writes the KCL equation symbolically, separates truly known voltages (set by grounded sources) from coupled unknowns, and checks that current entering the node equals current leaving.

![Loaded resistor bridge with node Va selected](docs/images/resistor-bridge.png)
*A loaded Wheatstone-style bridge. Va and Vb are coupled through R5, so they must be solved together.*

---

## Verification

Every reference answer is a fixed value **derived by hand**, never taken from the solver's own output. `verification.py` runs each circuit through the full pipeline (drawing → topology → engine) and checks node voltages, signed branch currents, KCL at every node, total power balance, and the Thévenin/Norton port.

| Reference circuit | Key result |
|---|---|
| Parallel paths | Va = 7.2 V, R<sub>th</sub> = 2000/3 Ω |
| Voltage divider | Va = 8 V |
| Current source + resistor | Va = 6 V |
| Floating voltage source (supernode) | Va = 2 V, Vb = −4 V |
| Loaded resistor bridge | Va = 36/7 V, V<sub>th</sub> = 3 V, R<sub>th</sub> = 4000/3 Ω |
| Inverting op amp | Vout = −2 V |
| Non-inverting op amp | Vout = 3 V |
| Voltage follower | Vout = 2 V with zero output current |
| Unloaded resistor output | Vout = 12 V with zero current |

Hand derivations for each case are in [`docs/reference-cases.md`](docs/reference-cases.md). The automated tests also feed deliberately wrong solver results to the verifier, which confirms that it catches them.

---

## Getting started

Requires Python 3.10+.

```bash
git clone https://github.com/yabdelmesih-ops/circuitscope.git
cd circuitscope
pip install -r requirements.txt
streamlit run drawing_app.py
```

On Windows you can also double-click `RUN_CIRCUITSCOPE.bat`.

**Try it:** open *Example circuits and solver checks* and load **Op amp · inverting amplifier**. Choose *Explain node* in the inventory and click the output wire. See the [user guide](docs/user-guide.md) for all editor controls.

### Running the tests

```bash
python -m unittest discover -s tests -v   # Python: topology, engine, op amps, lessons, app
npm install && npm test                   # JavaScript: wiring geometry and editor DOM (jsdom)
```

---

## Project structure

```
drawing_app.py       Streamlit app: questions, results, lesson display
engine.py            MNA matrix construction, solve, Thévenin/Norton
circuit_model.py     Shared conventions + op-amp feedback validation
topology.py          Drawing → netlist (union-find), input validation
teaching.py          Node lessons: KCL equations, current directions
examples.py          Reference circuits with hand-derived answers
opamp_examples.py    Op-amp reference circuits
verification.py      Compares engine output to reference answers
canvas/              Schematic editor (HTML/CSS/JS, Streamlit component)
tests/               Python unittest + Node test suites
docs/                Architecture, op-amp model, reference cases, user guide
```

**Further reading:** [architecture](docs/architecture.md) · [op-amp model](docs/op-amp-model.md) · [reference cases](docs/reference-cases.md) · [user guide](docs/user-guide.md)

---

## Scope and limitations

CircuitScope models **linear DC circuits**: resistors, independent ideal sources, and ideal op amps with resistive negative feedback. It does not simulate capacitors, inductors, AC or transient behavior, dependent sources, comparators, saturation waveforms, or real op-amp imperfections such as offset, bias current or slew rate. It is an educational tool and has not been validated against SPICE.

## Roadmap

- [ ] Cross-check reference circuits against LTspice
- [ ] Capacitors and inductors (DC steady state, then transient)
- [ ] Voltage-controlled dependent sources
- [ ] AC phasor analysis with complex MNA

---

**Youssef Abdelmesih** · Electrical Engineering, UMass Amherst · [LinkedIn](https://www.linkedin.com/in/youssef-abdelmesih-848a5738a)
