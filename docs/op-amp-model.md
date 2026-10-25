# Op-amp model

CircuitScope models an **ideal op amp operating linearly under negative feedback** at DC. This document describes the assumptions, how the model enters the MNA system, and its limits.

## Ideal rules

With negative feedback and the output inside its limits:

```
I+ = I− = 0          (infinite input resistance)
V+ = V−              (feedback drives the input difference to zero)
```

These are two separate statements. The inputs are **not** connected internally. An inverting amplifier's − input sits at a *virtual ground*: it is held at 0 V by feedback, yet no current flows from it into ground or into the amplifier.

The output can source or sink whatever current the external circuit requires, drawing energy from implicit supply rails. Its ideal output resistance is zero.

## Pins and conventions

| Pin | Netlist field | Role |
|---|---|---|
| + | `node1` | Non-inverting input |
| − | `node2` | Inverting input |
| OUT | `node3` | Output |

Positive op-amp current is defined as current flowing **into** OUT. A negative value means the amplifier is sourcing current into the external circuit. Output limits default to −15 V and +15 V and can be edited per amplifier.

## MNA formulation

Each op amp adds one unknown, the output current, and one equation:

- **Output current:** stamped only into OUT's KCL row. Neither input receives a current stamp, which enforces `I+ = I− = 0`.
- **Constraint row:** `V(node1) − V(node2) = 0`.

The output voltage is not specified directly. It is whatever value satisfies the constraint together with KCL across the feedback network. Solving the full system yields the output voltage and output current together.

## Feedback validation

Before solving, `validate_opamps()` in `circuit_model.py` checks the topology:

1. Nodes fixed by ground or by voltage-source chains connected to ground are excluded.
2. Starting from OUT, it searches through resistors.
3. The − input must be reachable, directly or through resistors. Otherwise the circuit is open-loop and rejected.
4. The + input must not be reachable. Positive or mixed feedback is rejected.
5. Tied inputs (+ and − on the same node) and invalid output limits are rejected.

This is a conservative DC structural check. It is not an AC stability analysis.

## Saturation

After solving, each output voltage is compared with its limits. If the required output is outside them, the amplifier would saturate and `V+ = V−` no longer holds. The solver reports this instead of clamping the output and presenting an invalid operating point. Saturated behavior itself is not simulated.

## Worked examples

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

## Open-circuit outputs and probes

An **Output probe** is an ideal voltmeter with infinite resistance. It adds no branch to the netlist, and its two terminals are never joined.

An open output is not the same as a floating node. A 12 V source in series with a 1 kΩ resistor ending at an unloaded output carries zero current, so the resistor drops 0 V and the output is 12 V. A truly floating node, with no constraining path, has no defined voltage, and the solver reports an error.

For **Open-circuit voltage** and **Thévenin** questions, the selected external load is removed from a copy of the netlist. Feedback and divider resistors stay in place, and the saved drawing is unchanged.

## Equivalent circuits

During the Thévenin resistance test, independent sources are deactivated but op amps remain active. An ideal feedback amplifier output therefore gives R<sub>th</sub> = 0, and no finite Norton current exists for that port.

## Not modeled

Supply headroom, input common-mode limits, offset voltage, bias currents, output current limits, finite gain, frequency response, slew rate, transients and comparator operation.

## Reference

MIT OpenCourseWare, 6.071J *Introduction to Electronics, Signals, and Measurement*: [Op Amps I](https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/22_op_amps1/)
