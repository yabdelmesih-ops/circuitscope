# How a drawn circuit reaches your Python solver

The drawing becomes a netlist for your modified nodal analysis solver. The engine now also models ideal feedback op amps; R/V/I behavior keeps the same conventions.

## 1. A component is still a dictionary

In a drawing, a resistor also has a position and rotation:

```python
{
    "id": "R1",
    "type": "R",
    "x": 480,
    "y": 180,
    "rotation": 0,
    "value": 1000,
    "label1": "",
    "label2": ""
}
```

The JavaScript `pins()` function calculates where its two terminals appear. We name them `R1:1` and `R1:2`. Moving the symbol changes their coordinates, but these terminal IDs stay the same.

## 2. A wire is a pair of terminal IDs

```python
{"id": "w1", "a": "V1:1", "b": "R1:1", "bend": "vh"}
```

This says that V1's positive terminal connects to R1's first terminal. `bend` changes the drawn elbow; it has no electrical effect.

Wires remember terminal IDs rather than only coordinates, so they follow moving components. Wire crossings never silently create connections.

Manual routes additionally contain a **via** list of corner coordinates. Those points change only the drawn route. When a new wire deliberately ends on another wire, JavaScript inserts a junction item, splits that existing wire into two pieces and joins the new branch to the junction's terminal. All three segments then share a terminal ID, which is what makes the branch electrically connected. The whole edit is saved and undone together.

While a wire is being drawn, its start, corners and preview stay in local UI state. Dragging a wire or placing a corner does not rerun Python or add partial items to the model. A completed connection is copied into the circuit and sent once. Escape cancels the draft; Undo first removes unfinished corners.

## 3. Connected terminals form groups

Look at `compile_drawing()` in **topology.py**.

It starts by putting every terminal in its own group:

```python
parent[pin] = pin
```

`find(pin)` follows the group links to a representative terminal. A wire joins two groups:

```python
def connect(first, second):
    parent[find(second)] = find(first)
```

For example, if V1:1 is wired to R1:1, and R1:1 is wired to R3:2, all three terminal IDs end up in one group. That group is one electrical node.

This grouping technique is called **union-find** (or a disjoint-set). It is a graph-connectivity algorithm; it does not use Ohm's law or solve voltages.

## 4. Groups receive node names

The group containing a ground terminal becomes node `0`. All ground symbols are grouped together.

An optional label such as `Va` names another group. Unlabeled groups receive generated names such as `N1` and `N2`. Node labels have to agree if you explicitly connect them together.

Then the code builds your familiar component list:

```python
{
    "name": "R1",
    "type": "R",
    "node1": "Vb",
    "node2": "Va",
    "value": 1000.0
}
```

The drawing coordinates have disappeared. Your solver only needs the circuit's connectivity and values.

## 5. Streamlit passes the drawing between JavaScript and Python

In **canvas/editor.js**, this line sends the changed drawing to Python:

```javascript
setStateValue('drawing', clone(model));
```

In **drawing_app.py**, the corresponding result is read here:

```python
drawing = result.drawing
components, terminal_nodes = compile_drawing(drawing)
```

The raw drawing and its numerical netlist are different objects. Keeping the conversion visible helps debug wiring errors before they reach the equation solver.

## 6. The engine does the electrical analysis

For a node voltage:

```python
voltages = get_voltages(components)
answer = voltages[node1] - voltages[node2]
```

For a Thevenin equivalent:

```python
voltage, resistance = thevenin(components, node1, node2, load_name)
```

These keep your original function interface. Their equations do not depend on where symbols are drawn. The added op-amp constraint and output-current unknown are explained in **OPAMPS_AND_OUTPUTS.md**.

## A short exercise to make this yours

1. Load the example and solve Va: 7.2 V.
2. Move and rotate R3. Solve again: the answer stays 7.2 V, because its pin connections stayed the same.
3. Change R3 from 2000 to 1000 ohms. Va should become 8 V.
4. Inspect the generated component table and identify which entry changed.
5. Remove both of R3's wires. Its isolated terminals now produce a floating-node warning. Removing just one wire instead leaves a dangling branch with zero current; it does not necessarily make the remaining circuit unsolvable.

Being able to explain that sequence demonstrates the separation between drawing, topology and numerical analysis. Add your own comments or feature once you understand the relevant function.

## 7. Teach the selected node

**teaching.py** takes the existing engine's solved voltages and source currents and builds the lesson. It uses Ohm's law for resistor current, the specified value for a current source, and the engine's extra current unknown for a voltage source. A negative current reverses the visual arrow; it is not an error.

For KCL, the lesson uses currents leaving the selected node as positive. If a branch's pin 1 is the selected node, its outward current is its solved current. If pin 2 is the selected node, the sign reverses. Adding those outward currents checks charge conservation.

The symbolic equation is built before inserting solved values. Only ground and voltage-source chains connected to ground supply known voltages. A floating voltage source introduces a current unknown and a voltage constraint, so the explanation displays the full simultaneous system instead of pretending a neighboring voltage was given.

The Python lesson payload includes branch signs, numbered explanations, voltages and equation text. **canvas/editor.js** uses it to overlay current arrows and highlight the selected node. It does not invent currents for individual ideal-wire segments. The notes are deterministic calculations and templates; no model API or API key is needed.

The Explain node tool sends a separate **node_request** state value with the clicked terminal ID, drawing revision and an increasing sequence number. A wire click sends one of that wire's endpoint IDs. Python resolves the terminal's node through the topology map, updates the question controls, and runs the node lesson. It handles each request once, so changing a lesson step does not repeat the solve. A request from an older drawing revision is rejected, and the user can click again. The request is UI state rather than part of the saved circuit drawing.

**drawing_app.py** saves the result with a signature of its component list and question. A change in wiring, values or question makes the old answer ineligible for display. Moving a component preserves the signature, because coordinates do not enter the electrical equations. The editor also hides annotations immediately after a local edit so an older backend response cannot restore misleading arrows.

## 8. Verify the engine against hand calculations

**examples.py** supplies nine drawings (with **opamp_examples.py**) and fixed expected numbers derived from the equations in **REFERENCE_CASES.md**. It creates fresh drawing dictionaries so loading or testing an example cannot mutate the saved template.

**verification.py** compiles each drawing through the same topology layer, calls your engine, and compares its voltages, signed currents and equivalent-circuit values against those expectations. It also sums currents at every node and signed power across all branches. These conservation checks help catch sign errors even when one voltage happens to be right.

The reference checks run separately from the active drawing. The app keeps their results in session state and hides an old report if engine.py changes. Tests intentionally supply incorrect solver outputs and equivalent-circuit answers to ensure the verifier detects failures. Passing these nine cases is a useful regression check, while external SPICE and native-browser testing remain separate work.
