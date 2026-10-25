# Architecture

CircuitScope keeps three concerns separate: **drawing**, **topology** and **numerical analysis**. A drawing is converted to a netlist, the netlist is solved, and the solution is turned into a lesson that is drawn back onto the canvas.

```
canvas/editor.js ──drawing──▶ topology.py ──netlist──▶ engine.py ──solution──▶ teaching.py ──lesson──▶ canvas/editor.js
                                                │
                                                └──▶ spice_export.py ──▶ .cir netlist (LTspice / ngspice)
```

| Module | Responsibility |
|---|---|
| `canvas/editor.js` | Schematic editor: symbols, wires, undo, lesson overlays |
| `topology.py` | Drawing → netlist via union-find; drawing validation |
| `circuit_model.py` | Shared node/current conventions; op-amp topology checks |
| `engine.py` | MNA construction and solve; comparator iteration; Thévenin/Norton |
| `teaching.py` | Node lessons: symbolic KCL, current directions, balance check |
| `practice.py`, `practice_ui.py` | Guided-practice questions, grading and UI |
| `spice_export.py`, `spice_validate.py` | SPICE netlist export; optional ngspice validation runner |
| `examples.py`, `opamp_examples.py`, `verification.py` | Reference circuits and hand-calculation checks |
| `drawing_app.py` | Streamlit app tying everything together |

## 1. Drawing model

A component in a drawing has an ID, a type, a position, a rotation, a value and optional node labels:

```json
{ "id": "R1", "type": "R", "x": 480, "y": 180, "rotation": 0, "value": 1000, "label1": "", "label2": "" }
```

`pins()` in `canvas/editor.js` computes where each terminal is drawn. Terminals are identified by stable IDs such as `R1:1` and `R1:2`, so moving or rotating a symbol changes its pin coordinates but not its identity.

A wire connects two terminal IDs:

```json
{ "id": "w1", "a": "V1:1", "b": "R1:1", "bend": "vh" }
```

`bend` and the optional `via` list of corner points only affect how the wire is drawn. Because wires reference terminal IDs rather than coordinates, they follow components when they move, and **crossing lines never create a connection**. When a new wire deliberately ends on an existing wire, the editor inserts a junction item, splits the existing wire in two, and connects all three segments to the junction terminal as one undoable edit.

An in-progress wire (its start, corners and preview) lives in local UI state. Only a completed connection is committed to the model and sent to Python, so dragging does not trigger re-solves.

## 2. Topology: drawing → netlist (`topology.py`)

`compile_drawing()` determines which terminals share an electrical node using **union-find (disjoint-set)**:

```python
parent[pin] = pin                      # every terminal starts in its own set

def connect(first, second):
    parent[find(second)] = find(first) # a wire merges two sets
```

`find()` uses path compression. After all wires are processed, each set is one electrical node.

Node naming:

- The set containing any ground terminal becomes node `0`. All ground symbols are merged, even if drawn apart.
- An optional label such as `Va` names its set. Two different labels on the same node, or one label on two separate nodes, is reported as an error.
- Remaining sets receive generated names `N1`, `N2`, …

The output is a coordinate-free netlist:

```python
{"name": "R1", "type": "R", "node1": "Vb", "node2": "Va", "value": 1000.0}
```

Op amps add `node3` (OUT), output limits `v_min` / `v_max`, and a `mode` of `feedback` or `open_loop`. Output probes (`PORT`) produce no netlist entry: they are ideal voltmeters with infinite resistance whose two terminals are never joined.

`validate_for_solving()` catches common drawing errors before the matrix is built: no components, no ground, floating nodes (nodes not reachable from ground through resistors or voltage sources), shorted voltage sources, and unsupported op-amp feedback.

## 3. Numerical analysis (`engine.py`)

`solve_circuit()` builds a Modified Nodal Analysis system `A·x = b`. The unknown vector is:

```
x = [ node voltages (excluding ground) | voltage-source currents | op-amp output currents ]
```

Each component stamps its contribution:

- **Resistor:** conductance `1/R` on its two diagonal entries and `−1/R` on the off-diagonals.
- **Current source:** its value into `b` at its two nodes. Positive current flows from `node1` to `node2`.
- **Voltage source:** an extra current unknown in the KCL rows of its nodes, plus a constraint row `V(node1) − V(node2) = value`.
- **Ideal op amp:** an extra unknown for the current *into* OUT, appearing only in OUT's KCL row. No current is stamped at either input. The constraint row depends on the mode: `V(+) − V(−) = 0` for feedback, or `V(OUT) = selected level` for an open-loop comparator.

`numpy.linalg.solve` returns every voltage and source current at once. A singular matrix is reported as "no unique DC solution", which usually means a floating node, missing feedback, or conflicting ideal sources.

### Comparator iteration

A comparator's output level depends on its solved inputs, so the solve is iterated. Every comparator starts at its LOW level. After each solve, the solved input differences are compared, and any output level that disagrees is updated in `b`. The loop ends when every output agrees with its own comparison. A feed-forward chain of N comparators settles in at most N + 1 solves. A repeated set of output levels means no consistent DC state exists, and inputs within ±1 nV of each other after settling are reported as an undefined decision. See [op-amp-model.md](op-amp-model.md) for details.

The public interface is:

```python
voltages = get_voltages(components)               # {node: volts}
vth, rth = thevenin(components, node1, node2, load_name)
```

### Thévenin and Norton

`thevenin()` first removes the selected load and solves for the open-circuit port voltage. It then deactivates independent sources (voltage sources become shorts, current sources become opens), injects a 1 A test current between the port nodes, and reads the resulting voltage as R<sub>th</sub>. Op amps stay active during this step, which is why a feedback amplifier's output correctly yields R<sub>th</sub> = 0. The 1 A source is an algebraic probe, not a physical operating point, so output-limit checks are skipped for that solve only.

Norton current is `Vth / Rth`. For an ideal op-amp output (R<sub>th</sub> = 0) the app reports that no finite Norton equivalent exists. Thévenin and Norton are rejected when a comparator is present, because its switching input/output relationship is nonlinear.

## 4. Shared conventions (`circuit_model.py`)

- `component_nodes()` returns the terminals a part connects to. `branch_nodes()` returns the two nodes its branch current flows between. For an op amp that is OUT and an implicit ground/supply return.
- `branch_current()` gives a signed current: Ohm's law for resistors, the specified value for current sources, and the solved unknown for voltage sources and op amps.
- `validate_opamps()` performs a conservative DC topology check. It searches the resistor graph from each op amp's output, excluding ground and nodes fixed by voltage-source chains.
  - **Feedback mode:** the − input must be reachable (negative feedback), and the + input must not be (positive or mixed feedback is rejected).
  - **Open-loop mode:** neither input may be reachable. The search also follows floating voltage sources and other amplifiers' input-to-output paths, so a loop closed through another stage is caught. This rejects latches and oscillators.
  - Tied inputs, a comparator output shorted to a fixed node, and invalid output limits are also rejected.
- `comparator_state()` classifies a comparator's solved inputs as HIGH, LOW or UNDEFINED using the ±1 nV guard.

After solving, each op amp's output voltage is compared with its limits. If a feedback amplifier would exceed them, the solve fails with a saturation message rather than returning an invalid linear result.

## 5. Teaching layer (`teaching.py`)

`build_lesson()` uses the solved circuit to explain one selected node:

- **Branch currents.** Each incident branch is labeled entering or leaving the node. Negative current simply reverses the drawn arrow.
- **Symbolic KCL.** Currents leaving the node are taken as positive. Resistor terms are written as `(V_node − V_neighbor) / R` before any numbers are substituted.
- **Known vs. unknown voltages.** Only ground and voltage-source chains connected to ground count as given voltages. If a node's neighbors are themselves unknown, or a floating voltage source is involved, the lesson shows the full simultaneous equation set instead of implying a neighbor's voltage was known.
- **Balance check.** Entering and leaving currents are summed and compared within a numerical tolerance.

The lesson payload (branch signs, notes, equations, voltages) is sent to `canvas/editor.js`, which draws numbered current arrows and highlights the selected node. Ideal wire segments are not assigned individual currents.

## 6. App integration (`drawing_app.py`)

The canvas is a Streamlit custom component (`st.components.v2`). The editor sends the drawing back with `setStateValue('drawing', ...)`, and the app compiles and solves it.

Stale-result protection:

- Each solved result is stored with a hash of its netlist and question. Changes to wiring, values or the question hide the old answer. Moving a component does not, because coordinates do not enter the netlist.
- Drawing edits carry an increasing revision number. The editor discards annotations from an older revision, and a click-to-explain request from an outdated revision is rejected.
- **Explain node** sends a separate `node_request` (terminal ID, revision, sequence number). Each request is handled once, so changing lesson steps does not re-solve.

Editor lifecycle:

- Streamlit calls the JavaScript renderer again on every update. The editor stores its cleanup function on the root element and calls it before attaching new handlers. An `AbortController` removes the previous listeners and cancels any queued animation frame, so one click always reaches exactly one handler. The model, undo history and drafts are shared across renders.
- The Python question and lesson controls sit in one stable container, so adding or removing a widget never shifts the canvas to a new element position, which would remount it and lose its undo history.
- During a wire gesture, the property panel and incoming lesson layout are held steady, so the SVG coordinate transform can't change while the user is dragging toward a terminal.

These issues were found by the end-to-end browser suite; see [browser-tests.md](browser-tests.md).

## 7. SPICE export (`spice_export.py`, `spice_validate.py`)

`export_spice()` converts a checked netlist into an LTspice or ngspice deck. It runs the full DC solve first, so invalid circuits are rejected before any file is produced. Node labels are mapped to safe tokens (`0`, `n1`, `n2`, …) to avoid SPICE aliases such as `GND`. Feedback op amps become `E` sources with gain 10⁹, and comparators become two-level `B` sources.

`spice_validate.py` is an optional command-line runner. It invokes ngspice on each reference configuration, parses the operating-point output, compares it with CircuitScope and the hand references, and writes a report that records source-file hashes. The app shows that report only while those hashes match the current code. See [spice-validation.md](spice-validation.md).

## 8. Guided practice (`practice.py`, `practice_ui.py`)

Practice questions have fixed, hand-derived answer keys and are never graded by calling the solver. Before grading, the UI compares a signature of the compiled netlist with the question's signature, so an electrically edited circuit can't be graded against a stale key. Moving parts does not change the signature. See [guided-practice.md](guided-practice.md).

## 9. Verification (`examples.py`, `verification.py`)

`examples.py` and `opamp_examples.py` define eleven reference drawings with expected values derived by hand (see [reference-cases.md](reference-cases.md)). New dictionaries are created on each call so loading or testing an example cannot mutate the template.

`verification.py` runs each drawing through the same topology and engine code as the app. It then checks:

- every expected node voltage and signed branch current
- KCL at every node, including ground
- total signed power, normalized by total absolute power
- Thévenin voltage and resistance, and Norton current when R<sub>th</sub> ≠ 0 (skipped for comparator circuits)
- `V(+) = V(−)` for each feedback op amp, and the correct HIGH/LOW decision for each comparator

Together these make 153 comparisons across the eleven circuits.

Tests also inject deliberately wrong solver and equivalent-circuit results to confirm that the verifier reports failures.
