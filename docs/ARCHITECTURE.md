# Architecture

## Drawing to equations

`canvas/editor.js` handles placement, wiring, selection and Undo. It sends a JSON
drawing through Streamlit's component interface to `drawing_app.py`.
`topology.py` groups terminals connected by explicit wires into electrical nodes,
then produces a component list: type, name, value and terminal nodes. Labels name
nodes; matching labels alone do not connect them. Wire crossings need a junction.
Ground is node 0. Output probes measure two nodes without joining them.

## Modified nodal analysis

`engine.py` builds a linear system A x = b. The unknown vector contains every
non-ground node voltage, followed by independent voltage-source currents and
op-amp output currents. Each node row expresses Kirchhoff's current law.

A resistor between a and b contributes (Va − Vb)/R to node a and the opposite
current to node b. In the matrix this adds 1/R to both diagonal entries and
−1/R to the two cross entries. A current source from a to b subtracts its value
from b[a] and adds it to b[b]. A voltage source adds an unknown current and a
constraint Va − Vb = Vs. Ground's voltage is known, so it has no unknown column.
`numpy.linalg.solve` solves the assembled system. A singular matrix produces an
error rather than a guessed answer.

An ideal feedback op amp draws zero input current and adds V+ − V− = 0 as its
constraint. `circuit_model.py` checks supported passive negative-feedback paths.
The output must remain within its configured limits; closed-loop saturation is
rejected. In comparator mode the constraint instead fixes the output HIGH or
LOW. Feed-forward stages are re-solved until their output levels agree with
their input comparisons. Inputs within 1 nV are treated as undefined.

## Results and methods

`circuit_model.py` calculates branch currents using shared sign conventions.
Resistor current is (V1 − V2)/R; signed power is terminal voltage times current.
An op-amp output current is positive into OUT, with an implicit supply return.

For Thévenin analysis, `engine.py` first solves the unloaded port voltage. It then
zeros independent sources, keeps feedback amplifiers active and injects 1 A
into the port. The resulting port voltage gives resistance. Norton current is
Vth/Rth where finite. Comparator circuits are excluded because they are nonlinear.

`teaching.py` derives node KCL notes from the solved branches. `course_methods.py`
handles supernodes, superposition, source transformations, dividers and supported
feedback/summing networks. `course_ui.py` displays them; `circuit_layout.py`
builds editable method previews. A circuit signature hides stale results after
an electrical edit. Streamlit keeps the canvas in a stable container to preserve
Undo, and each editor render cleans up its previous listeners.
