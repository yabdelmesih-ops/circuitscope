# Op amps and open outputs

This update adds an ideal linear DC amplifier model, educational material, three amplifier drawings and an unloaded resistor output. The canvas still starts empty. All previous R/V/I drawings retain their component conventions.

## Use it

1. Stop the old app with Ctrl+C. Extract the complete new ZIP and open that folder in VS Code.
2. Run `py -m streamlit run drawing_app.py`. Refresh the browser with Ctrl+F5.
3. Open **Example circuits and solver checks** and load an amplifier example. Open **Op-amp material** for its gain derivation.
4. To measure an unloaded output, choose **Open-circuit voltage**. Select the drawn **OUT1** probe, or choose two nodes manually. Remove only an external load such as **RL**, or select **None** if already unloaded.
5. Solve. The displayed voltage is V(+) − V(−). Probe current is always zero. A removed load appears as an OPEN switch for the calculation; the saved circuit still contains it. The feedback network stays connected.

Drag **Op amp** and **Output probe** from the inventory for your own circuit. Select an amplifier to label OUT or edit its default −15 to +15 V output limits. R/V/I use SI units, including amperes and ohms rather than mA or kΩ.

## Why the ideal rules work

In the supported negative-feedback linear model, the amplifier adjusts its output until its two input voltages are equal. Its infinite input resistance means both input currents are zero. These are two different statements: the input nodes are not connected internally. An inverting amplifier's grounded + input can hold − at a virtual ground while current flows between its input resistor and feedback resistor, with no current entering −.

For the inverting example, Vin = 1 V, Rin = 10 kΩ and Rf = 20 kΩ. At the − input, (0 − 1)/10000 + (0 − Vout)/20000 = 0, giving Vout = −2 V. The output supplies or absorbs the feedback/load current using energy from implicit supplies. Removing RL leaves the feedback current intact.

For the non-inverting example, Vin = 1 V and the feedback divider forces Vm = Vout/3 = Vin, so Vout = 3 V. For a follower, OUT is wired to −, so Vout = Vin. With no load, the follower can hold a voltage with zero output current.

An open external port does not imply zero voltage. The 12 V resistor example has zero load current, so its resistor voltage drop is zero and Vout = 12 V. A truly floating terminal is different: without a constraining electrical path, its voltage cannot be determined, and the solver reports an error.

## What changed in the code

**topology.py** gives an amplifier three independent terminal groups: node1 (+), node2 (−), node3 (OUT). PORT has two terminal groups and no solver branch. The pins are joined only by explicit wires.

**engine.py** keeps the R/V/I modified nodal analysis stamps. For U1 it adds one unknown, the current entering OUT. The output's KCL equation contains that current. The amplifier's extra equation is V(node1) − V(node2) = 0. Neither input gets a current stamp. Solving the whole matrix determines the output voltage and output current together.

For example, with a loaded inverting amplifier, the unknown vector contains Vin, Vm, Vout, the input source current and the amplifier output current. Ground has no voltage unknown. Resistor equations connect Vm and Vout; feedback equality fixes Vm to zero. KCL then fixes Vout and the amplifier's output current.

**circuit_model.py** defines shared node/current conventions and checks the supported feedback structure. It looks for a direct or passive resistor path from OUT to −, excluding ground and nodes clamped by independent voltage-source chains. It rejects a passive output path to +, tied inputs and missing feedback. This is a conservative DC topology check, not proof of AC stability or support for arbitrary active/mixed feedback.

**thevenin()** retains the amplifier when deactivating independent V/I sources. Its 1 A test source is an algebraic resistance probe; output operating limits are skipped for that artificial test only. The normal open-circuit operating point still checks the limits. Ideal op-amp output resistance is zero. A finite Norton current cannot represent that ideal voltage port, so the UI reports that explicitly.

**teaching.py** includes input equality in the symbolic equation set, excludes input currents from KCL, and draws current arrows only at OUT. Amplifier positive current is INTO its output. Negative current means it sources current into the external circuit. Output power uses an implicit ground/supply return; individual supply currents and consumption are not calculated.

**drawing_app.py** removes the selected external load in a copied netlist, validates the remaining port, solves it and supplies a measurement overlay. **canvas/editor.js** draws the probe reading and opens the removed load symbol. Local edits clear those annotations immediately. Probe pins themselves never short or load the circuit.

## Limits of this model

The output limits specify the allowed linear range, with implicit supply connections. If the required output exceeds them, the app reports saturation and refuses to apply V+ = V− to that invalid operating point. It does not simply clamp the output and claim a valid solution. Real supply headroom, input common-mode limits, offset, bias currents, output current limits, frequency response, transients and comparator behavior are not simulated.

There are 97 automated tests (63 Python and 34 JavaScript), plus 125 hand-reference comparisons across nine circuits through the in-app check button. Numerical, Streamlit AppTest and DOM interaction checks pass. Native Windows browser layout, hit testing and the browser-to-Streamlit transport still require checking on your machine; no external SPICE validation has been claimed.

## Learn and explain it yourself

Change Rin from 10 kΩ to 20 kΩ in the inverting example. Predict Vout before solving: the gain becomes −1 and Vout should be −1 V. Then remove RL and compare amplifier current while keeping Rf. Finally increase Vin enough to demand an output beyond the limits and read why the ideal linear rule stops applying. Being able to trace those changes through KCL and the extra matrix equation is the core of explaining this addition in an interview.

Primary learning reference: [MIT OpenCourseWare, Introduction to Electronics — Op Amps I](https://ocw.mit.edu/courses/6-071j-introduction-to-electronics-signals-and-measurement-spring-2006/resources/22_op_amps1/).
