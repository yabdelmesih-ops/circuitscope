# SPICE export and independent validation

CircuitScope can export any checked circuit as a `.cir` netlist for LTspice or ngspice. The same exporter is used to validate the solver against **ngspice-42**: all **29 DC configurations** pass **293 comparisons**, with a maximum voltage deviation of about **6 × 10⁻⁹ V**.

## What was validated

The 29 configurations come from the 11 reference circuits:

| Configuration | Count | Purpose |
|---|---|---|
| `drawing` | 11 | The full reference circuit, including its load |
| `open_port` | 9 | The selected external load removed, everything else active |
| `resistance_test` | 9 | Load removed, independent sources deactivated, 1 A injected into the port. Port voltage ÷ 1 A = R<sub>th</sub> |

The two comparator circuits have no resistance test, because a switching input/output relationship has no global Thévenin equivalent.

For each configuration, `spice_validate.py` compares node voltages and branch currents from ngspice against both CircuitScope's solution and the fixed hand-calculated references.

| Quantity | Relative tolerance | Absolute tolerance |
|---|---|---|
| Voltage, resistance | 10⁻⁶ | 10⁻⁸ |
| Current | 10⁻⁶ | 10⁻¹⁰ A |

Resistor currents are computed from SPICE's solved node voltages. Current-source currents are their specified values. Voltage-source and amplifier output currents come from SPICE's branch-current unknowns.

## Evidence in the repository

- `validation/spice_report.json`: simulator version, environment, models, tolerances, every individual check, and SHA-256 hashes of the solver, topology, example, export and validation sources.
- `validation/spice/ngspice/`: the 29 decks that were run.
- `validation/spice/ltspice/`: the same 29 configurations in LTspice syntax. These are provided for inspection; LTspice itself was not run.

The app shows the report under **Show independent SPICE verification**, but only while the recorded source hashes match the current code. Any change to a relevant source file hides the report until validation is run again.

## Model mapping

| CircuitScope element | SPICE element |
|---|---|
| Resistor, V source, I source | `R`, `V`, `I` with the same values and directions |
| Feedback op amp | `E` voltage-controlled voltage source with gain 10⁹ |
| Open-loop comparator | `B` behavioral source selecting the configured HIGH or LOW level (`if(...)` in LTspice, ternary in ngspice) |
| Output probe | Nothing. Probes add no branch |

Two model differences matter when comparing results:

- **Finite vs. infinite gain.** CircuitScope imposes V+ = V− exactly, while the exported E source has gain 10⁹. Small numerical differences are expected, and they account for the nanovolt-level deviations. The E source also does not clip, so output limits are checked by CircuitScope before export.
- **Threshold handling.** CircuitScope reports an error when comparator inputs are equal or within ±1 nV. The raw B expression selects LOW at equality and has no guard, so results at or near a switching threshold need separate interpretation.

## Exporting a circuit

**Export for LTspice / ngspice**, below the canvas, offers two configurations:

- **Full drawing:** every drawn electrical part.
- **Current solved circuit:** the circuit for the active question, with any selected external load removed and feedback networks retained. Thévenin/Norton questions export the open-port circuit, not the source-deactivated resistance test.

Node names are mapped to safe tokens: ground becomes `0`, and other nodes become `n1`, `n2`, …. This prevents labels such as `GND` from being interpreted as SPICE aliases. Comments in the file and a mapping table in the app relate each token to its original label. Element names carry the SPICE prefix and the part ID, such as `R_R1`, `V_V1`, `E_U1` or `B_U1`.

Before writing a deck, the exporter runs the same DC checks as the solver. Floating inputs, missing feedback, invalid output limits and ambiguous comparator thresholds produce an error instead of a misleading netlist.

## Reproducing the validation

ngspice is optional and is not needed to run the app. With ngspice installed:

```bash
python spice_validate.py --ngspice /path/to/ngspice   # or omit --ngspice if it is on PATH
```

This rewrites the report and both sets of decks in `validation/`, lists any failing configuration individually, and exits nonzero on failure. Use `--output another-folder` to keep the committed report unchanged.

## Scope

These are educational DC models with implicit supplies, not manufacturer device models. The validation does not cover switching delay, frequency response, noise, output current limits or physical device behavior. It is a regression check on the reference circuits, not proof of correctness for every possible drawing.

## References

- [LTspice netlist syntax reference (Analog Devices)](https://analogdevicesinc.github.io/ltspice-reference/ai_ref/SPICE-SYNTAX-REFERENCE.html)
- [LTspice circuit element reference (Analog Devices)](https://analogdevicesinc.github.io/ltspice-reference/ai_ref/CIRCUIT-ELEMENTS-REFERENCE.html)
- [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
