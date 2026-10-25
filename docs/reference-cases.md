# Reference circuits and validation

Each reference circuit can be loaded in the app from **Example circuits and solver checks**, and all nine are checked together with **Run solver checks**.

The reference values are fixed results from the hand calculations below. They are not obtained by running the solver and treating its output as the answer key. Verification runs `engine.py` and compares its results with these fixed values.

| Circuit | Loaded-circuit node voltages | Reference Thévenin port | Vth | Rth |
| --- | --- | --- | --- | --- |
| Original parallel-path example | Va = 7.2 V; Vb = 12 V | Va → ground, remove R2 | 12 V | 2000/3 Ω |
| Voltage divider | Va = 8 V; Vs = 12 V | Va → ground, keep both resistors | 8 V | 2000/3 Ω |
| Current source and resistor | Va = 6 V | Va → ground, keep resistor | 6 V | 2000 Ω |
| Floating voltage source | Va = 2 V; Vb = −4 V | Va → ground, keep resistors | 2 V | 2000/3 Ω |
| Loaded resistor bridge | Va = 36/7 V; Vb = 27/7 V; Vs = 9 V | Va → Vb, remove R5 | 3 V | 4000/3 Ω |
| Inverting op amp | Vin = 1 V; Vm = 0 V; Vout = −2 V | Vout → ground, remove RL | −2 V | 0 Ω |
| Non-inverting op amp | Vin = Vm = 1 V; Vout = 3 V | Vout → ground, no external load | 3 V | 0 Ω |
| Voltage follower | Vin = Vout = 2 V | Vout → ground, no load | 2 V | 0 Ω |
| Unloaded resistor output | Vin = Vout = 12 V | Vout → ground, no load | 12 V | 1000 Ω |

Ground is 0 V in every case. For nonzero Rth, the port's Norton current is Vth/Rth in the listed port direction. Ideal op-amp outputs have Rth = 0, so no finite Norton-current check is performed for them. Values for a loaded circuit and an equivalent circuit with its load removed describe different configurations.

## Hand calculations

1. **Parallel paths:** R1 ∥ R3 = (1000 × 2000)/(1000 + 2000) = 2000/3 Ω. With R2 = 1000 Ω, Va = 12 × 1000/(1000 + 2000/3) = 7.2 V. R1 carries 4.8 mA into Va and R3 carries 2.4 mA into Va; R2 carries 7.2 mA out. R3's pin-1-to-pin-2 current is −2.4 mA. Removing R2 gives Vth = 12 V.

2. **Divider:** I = 12/(1000 + 2000) = 4 mA, so Va = (4 mA)(2000 Ω) = 8 V. With an external port at Va and both resistors retained, deactivating the source gives Rth = 1000 ∥ 2000 = 2000/3 Ω.

3. **Current source:** Va/2000 − 0.003 = 0, hence Va = 6 V. The current source is directed from ground into Va. It supplies 18 mW, while the resistor absorbs 18 mW. Deactivating the ideal current source opens it, leaving Rth = 2000 Ω.

4. **Floating voltage source:** Va/1000 + Vb/2000 = 0 gives 2Va + Vb = 0. The source imposes Va − Vb = 6. Solving these two equations gives Va = 2 V and Vb = −4 V. The source current is −2 mA in its pin-1-to-pin-2 reference. A voltage source between two unknown nodes does not fix either node's ground-referenced voltage by itself.

5. **Bridge:** (Va − 9)/1000 + Va/2000 + (Va − Vb)/1000 = 0 and (Vb − 9)/2000 + Vb/1000 + (Vb − Va)/1000 = 0 reduce to 5Va − 2Vb = 18 and −2Va + 5Vb = 9. Solving gives Va = 36/7 V and Vb = 27/7 V. The loaded bridge current through R5 is (Va − Vb)/1000 = 9/7000 A. After R5 is removed, the two divider outputs become 6 V and 3 V, giving Vth = 3 V. Deactivating the source gives Rth = (1000 ∥ 2000) + (2000 ∥ 1000) = 4000/3 Ω and In = 2.25 mA.

6. **Inverting op amp:** I+ = I− = 0 and Vm = 0. KCL at Vm gives (0 − 1)/10000 + (0 − Vout)/20000 = 0, hence Vout = −2 V. With RL = 10 kΩ connected, 0.3 mA enters the amplifier output; without RL, 0.1 mA enters through feedback. Rth = 0 for the ideal output.

7. **Non-inverting op amp:** Vm = Vin = 1 V and Vm = Vout × 10000/(10000 + 20000), hence Vout = 3 V. The feedback divider draws 0.1 mA even without an external load. Rf is oriented Vm → Vout in the drawing, so its signed current is −0.1 mA.

8. **Follower:** OUT is wired to −, and + is held at 2 V. Therefore Vout = 2 V. With no load or feedback resistors, both source and output currents are zero.

9. **Open resistor output:** KCL at Vout gives (Vout − 12)/1000 = 0. Thus Vout = 12 V while the resistor and source currents are zero. The infinite-resistance probe contributes no branch.

## What Run solver checks verifies

- Every expected node voltage and signed component current.
- KCL at each node, including ground: currents leaving minus currents entering must be zero.
- Conservation of power: the total signed branch power must be zero. Positive power is absorbed; negative power is supplied.
- Thévenin voltage and resistance, with the exact port and load stated above, plus Norton current where Rth is nonzero. Amplifier power balance uses its output branch and implicit supply/ground return; supply currents are not modeled.

There are 125 numerical comparisons across the nine examples, including the ideal input voltage constraints. Comparisons use a relative tolerance of 1e−8 and an absolute tolerance of 1e−10. The signed-power residual is normalized by total absolute power before comparison. A PASS report covers these nine examples; it does not establish correctness for every possible circuit.

The automated tests also inject incorrect solver and equivalent-circuit results to check that the verifier reports failures. Reports are displayed per example so one failure does not prevent the remaining circuits from being checked. The reference checks never alter the active drawing.

## Remaining validation

The numerical comparisons and Streamlit startup paths have automated coverage. DOM tests exercise the drawing logic. Full native-browser mouse behavior, visual layout on Windows, and comparison with an external SPICE simulator still need independent checking. Supported models are resistors, independent ideal DC sources and ideal op amps with supported negative feedback. These checks do not cover real amplifier dynamics or saturation.
