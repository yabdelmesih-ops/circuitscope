# Circuits I methods

Open **Circuits I method examples** to load a reference drawing. Open **Circuits I methods · explain this circuit**, choose a method, and press **Explain selected method**. These tools also analyze your own supported drawings. They do not replace the ordinary Solve drawing controls.

## Supernodes

The app finds chains of ideal voltage sources whose nodes are not tied through another voltage source to ground. It highlights those nodes and source components, adds the boundary KCL equation and displays the source-voltage constraints. Internal source currents and internal resistor currents cancel from boundary KCL. A grounded voltage-source chain fixes voltages directly. Ideal amplifier input equality does not make a physical supernode.

Try **Supernode · floating source**: Va/1000 + Vb/2000 = 0 and Va − Vb = 6 give Va = 2 V, Vb = −4 V. The existing modified nodal engine solves this configuration; the new tool makes the supernode reasoning explicit.

## Superposition

Choose a voltage difference or signed branch current. The table solves one independent source at a time, shows the contribution and compares the signed sum with the full solution. Inactive voltage sources are 0 V shorts; inactive current sources are 0 A opens. Ideal negative-feedback amplifiers remain active. A separate preview displays each contribution without changing the main drawing.

Try **Superposition · voltage and current sources**: the 12 V source contributes 8 V at Va; the 2 mA source contributes 4/3 V. Total: 28/3 V.

Do not add powers. Open-loop comparators are nonlinear and are rejected. The full solution must fit the amplifier output limits. Individual contributions are mathematical terms in the ideal linear model; their rail limits are not enforced separately. If a contribution exceeds a rail, it is not a prediction of that physical circuit operating alone.

## Source transformations

The tool detects a voltage source in series with a resistor only when their private junction has no other branch or probe. It also detects an independent current source in parallel with a resistor. Review the transformed diagram and checked external-node voltages before pressing **Load transformed circuit**. Loading creates a fresh editable drawing, so save the original first.

A source with voltage Vs and series resistance R becomes a current source Vs/R in parallel with R; its current points toward the positive output terminal. The reverse transformation uses Vs = IsR. The source orientation and sign are preserved. These are equivalent at the outer terminals; internal source/resistor voltages, currents and powers generally change. No transformation is offered for controlled sources or amplifier outputs. A generated preview is limited to 24 components, including probes.

Try **Voltage divider and source transformation**: the 12 V source and series 1 kΩ resistor become a 12 mA Norton source in parallel with 1 kΩ. With the 2 kΩ load retained, Va stays 8 V.

## Voltage dividers

Select the upper and lower resistors. For a supported parallel load across the lower resistor, select it explicitly. The tool checks that no additional current-carrying branch loads the midpoint, combines the lower parallel resistance and displays the divider equation. Ideal amplifier input terminals do not draw current.

The unloaded example gives 8 V. **Loaded voltage divider** adds a 2 kΩ load across the 2 kΩ lower resistor: their equivalent is 1 kΩ and Va becomes 6 V. If endpoint voltages are not fixed by grounded sources, the tool labels them as values from the full solve; the local divider identity cannot independently determine those unknown endpoints.

## Supported negative feedback

The feedback tool identifies the direct wire or passive resistor path from each output to its − input and highlights it. It checks the complete DC solution against configured output limits. Supported examples include inverting/non-inverting gain stages, a follower, the two summing networks below, and a feed-forward cascade where each amplifier has its own valid loop.

**Supported feedback · follower then gain stage** produces 1 V at the follower and 3 V at the second output. Positive or mixed feedback, hysteresis, oscillators and closed-loop saturation remain unsupported. A passive DC path check is not an AC stability analysis. Keep op-amp inputs electrically separate; equality comes from the ideal linear constraint.

## Summing amplifiers

**Summing amplifier · inverting** uses Vin1 = 1 V, R1 = 10 kΩ, Vin2 = 2 V, R2 = 20 kΩ and Rf = 20 kΩ. With the + input grounded, Vout = −Rf(Vin1/R1 + Vin2/R2) = −4 V. The walkthrough shows each weighted term and the full solver result. A nonzero reference uses Vout = Vref + Rf Σ(Vref − Vi)/Ri.

**Summing amplifier · non-inverting** connects 1 V and 3 V through equal 10 kΩ resistors to +. Their weighted average is 2 V. A feedback gain of 2 gives Vout = 4 V. The general weighted average is V+ = Σ(Vi/Ri)/Σ(1/Ri).

The recognizer handles these supported resistor networks and zero ideal input currents. It declines to apply a textbook sum formula when extra branches invalidate its assumptions. Other supported circuits can still use full modified nodal analysis.

## Implementation and checks

- **course_methods.py**: supernode boundaries, source contributions, transformations, dividers, feedback paths and summing formulas.
- **course_examples.py**: seven example drawings with fixed hand answers.
- **course_ui.py**: example loading, method controls, results and checked transformation loading.
- **diagram_import.py**: explicit wiring from a netlist and a safe SVG preview, shared with screenshot review.

The original numerical engine and original eleven external SPICE reference drawings are unchanged. **Check course examples** separately verifies seven course drawings against hand values and KCL. Method overlays clear immediately after a local edit; a changed electrical signature prevents the old method result from being shown. Drawing moves preserve the electrical signature.

References used in the existing teaching material:
https://openstax.org/books/university-physics-volume-2/pages/10-3-kirchhoffs-rules
https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/22_op_amps1/
