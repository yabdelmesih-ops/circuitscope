# Op-amp model

CircuitScope models ideal op amps at DC in two modes:

- **Feedback (default).** Linear operation under negative feedback.
- **Open loop (comparator).** An ideal two-level output that selects HIGH or LOW by comparing the inputs.

Both modes keep the input currents at zero. They differ in the extra equation each one adds to the MNA system.

## Pins and conventions

| Pin | Netlist field | Role |
|---|---|---|
| + | `node1` | Non-inverting input |
| − | `node2` | Inverting input |
| OUT | `node3` | Output |

Positive op-amp current is defined as current flowing **into** OUT. A negative value means the amplifier is sourcing current into the external circuit. Each amplifier has output limits `v_min` / `v_max` (default −15 V and +15 V) and a `mode` of `feedback` or `open_loop`. Drawings saved before comparator support have no `mode` and load as feedback.

## MNA formulation

Each op amp adds one unknown, the output current. It is stamped only into OUT's KCL row. Neither input receives a current stamp, which enforces `I+ = I− = 0`. The extra constraint row depends on the mode:

| Mode | Constraint row |
|---|---|
| Feedback | `V(+) − V(−) = 0` |
| Open loop | `V(OUT) = selected output level` |

## Feedback mode

### Ideal rules

```
I+ = I− = 0          (infinite input resistance)
V+ = V−              (feedback drives the input difference to zero)
```

These are two separate statements. The inputs are **not** connected internally. An inverting amplifier's − input sits at a *virtual ground*: it is held at 0 V by feedback, yet no current flows from it into ground or into the amplifier.

The output voltage is not specified directly. It is whatever value satisfies the constraint together with KCL across the feedback network. Solving the full system gives the output voltage and output current together. The output can source or sink whatever current the circuit requires, drawing energy from implicit supply rails, and its ideal output resistance is zero.

### Feedback validation

Before solving, `validate_opamps()` in `circuit_model.py` checks the topology:

1. Nodes fixed by ground or by voltage-source chains connected to ground are excluded.
2. Starting from OUT, it searches through resistors.
3. The − input must be reachable, directly or through resistors. Otherwise there is no negative feedback, and the user is directed to choose open-loop mode instead.
4. The + input must not be reachable. Positive or mixed feedback is rejected.
5. Tied inputs and invalid output limits are rejected.

This is a conservative DC structural check, not an AC stability analysis.

### Saturation

After solving, each output voltage is compared with its limits. If the required output is outside them, the amplifier would saturate and `V+ = V−` no longer holds. The solver reports this instead of clamping the output and presenting an invalid operating point. A feedback amplifier never switches into comparator mode on its own.

### Worked examples

**Inverting amplifier.** Vin = 1 V, Rin = 10 kΩ, Rf = 20 kΩ, + grounded. KCL at the − input (held at 0 V):

```
(0 − 1)/10000 + (0 − Vout)/20000 = 0   →   Vout = −2 V
```

With a 10 kΩ load, 0.3 mA flows into OUT: 0.1 mA from the feedback path plus 0.2 mA from the load. With the load removed, 0.1 mA still flows through Rf.

**Non-inverting amplifier.** Vin = 1 V drives +, with Rg = 10 kΩ to ground and Rf = 20 kΩ from OUT to −:

```
V− = Vout · Rg/(Rg + Rf) = Vin   →   Vout = (1 + Rf/Rg)·Vin = 3 V
```

The feedback divider draws 0.1 mA even with no external load.

**Voltage follower.** OUT wired directly to −, with + at 2 V. Vout = 2 V, and with no load the output current is zero. A voltage can exist without any current.

## Open-loop (comparator) mode

### Model

```
V+ − V− >  1 nV   →   Vout = v_max   (HIGH)
V+ − V− < −1 nV   →   Vout = v_min   (LOW)
otherwise         →   undefined: reported as an error
```

The output limits are the comparator's actual output levels and need not be symmetric. For example, 0 / 5 V and −12 / +12 V both work. `V+ = V−` is not imposed in this mode.

The ±1 nV band is a numerical guard around the discontinuous threshold. It is not hysteresis, input offset or memory. Inside it, the solver refuses to pick a rail rather than guessing.

### Iterative solve

Because each comparator's output level depends on its solved inputs, `solve_circuit()` iterates:

1. Start every comparator at its LOW level.
2. Solve the full loaded circuit.
3. Compare each comparator's solved inputs and update any output level that disagrees.
4. Repeat until every output agrees with its own input comparison.

A feed-forward chain of N comparators settles in at most N + 1 solves. Up to eight comparators per drawing are supported. If a set of output levels repeats without settling, the solver reports that no consistent DC state exists. An equal-input comparator is held pending while upstream outputs are still changing, and is reported as undefined only once the circuit has settled.

### Validation

A comparator must have no path from OUT back to either input. Paths are traced through resistors, through floating voltage sources, and through other amplifiers (from their inputs to their outputs), so a loop closed through another stage is also caught. This rejects configurations that could form a latch or an oscillator. A comparator output shorted to ground or to an ideal voltage source is also rejected.

### Worked examples

**Comparator HIGH.** V+ = 3 V, V− = 2 V, output levels 0 / 5 V, 1 kΩ load. The input difference is +1 V, so OUT = 5 V. The load carries 5 mA to ground, so U1's signed current is −5 mA (sourcing). The output branch supplies 25 mW, which the resistor absorbs. Both input-source currents are zero.

**Comparator LOW.** V+ = 1 V, V− = 2 V, output levels −12 / +12 V, 2 kΩ load. The difference is −1 V, so OUT = −12 V. The load's current toward ground is −6 mA, meaning the amplifier sinks 6 mA into OUT, and the output branch supplies 72 mW to the resistor.

### Open loop vs. open output

These are different ideas. *Open loop* means there is no feedback. *Open output* means no external load is attached. A comparator can drive a load, and an open-circuit-voltage question can remove that load: the output voltage stays the same, while the output current becomes zero.

## Open-circuit outputs and probes

An **Output probe** is an ideal voltmeter with infinite resistance. It adds no branch to the netlist, and its two terminals are never joined.

An open output is not the same as a floating node. A 12 V source in series with a 1 kΩ resistor ending at an unloaded output carries zero current, so the resistor drops 0 V and the output is 12 V. A truly floating node, with no constraining path, has no defined voltage, and the solver reports an error.

For **Open-circuit voltage** and **Thévenin** questions, the selected external load is removed from a copy of the netlist. Feedback and divider resistors stay in place, and the saved drawing is unchanged.

## Equivalent circuits

During the Thévenin resistance test, independent sources are deactivated but feedback op amps remain active. An ideal feedback amplifier output therefore gives R<sub>th</sub> = 0, and no finite Norton current exists for that port.

Thévenin and Norton are rejected when a comparator is present. A switching input/output relationship is nonlinear, so source deactivation does not apply, and small-signal equivalents around an operating point are not implemented.

## Not modeled

Finite open-loop gain, frequency response, slew rate, switching delay, hysteresis, oscillation, offset voltage, bias currents, input common-mode range, output current limits, supply headroom, and closed-loop saturation behavior.

## References

- MIT OpenCourseWare, 6.071J *Introduction to Electronics, Signals, and Measurement*: [Op Amps I](https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/22_op_amps1/)
- Analog Devices StudentZone: [Basic Op Amp Configurations](https://www.analog.com/en/resources/analog-dialogue/studentzone/studentzone-may-2019.html)
- Microchip Developer Help: [Open Loop Configuration](https://developerhelp.microchip.com/xwiki/bin/view/products/amplifiers-linear/operational-amplifier-ics/introduction/basic-configurations/open-loop/)
