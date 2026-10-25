"""Build circuit-specific explanations from the solved circuit and device modes.

Equations use unknown voltages first. Solved numbers are used separately to
check them, so an unknown neighbor is never presented as a given voltage.
"""
from hashlib import sha256
import json
from circuit_model import branch_nodes, branch_current, opamp_mode, comparator_state


def circuit_signature(components):
    return sha256(json.dumps(sorted(components, key=lambda p: p['name']), sort_keys=True).encode()).hexdigest()


def number(value):
    return f'{0.0 if value == 0 else value:.6g}'


def current_label(value):
    magnitude = abs(value)
    if magnitude >= 1:
        return f'{number(magnitude)} A'
    if magnitude >= .001:
        return f'{number(magnitude * 1000)} mA'
    if magnitude >= .000001:
        return f'{number(magnitude * 1e6)} µA'
    return f'{number(magnitude)} A'


def math_number(value):
    text = number(value)
    if 'e' not in text.lower():
        return text
    mantissa, exponent = text.lower().split('e')
    return mantissa + r'\times 10^{' + str(int(exponent)) + '}'


def symbol(node):
    if node == '0':
        return '0'
    text = node[1:] if node.startswith('V') and len(node) > 1 else node
    return r'V_{\mathrm{' + text.replace('_', r'\_') + '}}'


def current_symbol(name):
    return r'I_{\mathrm{' + name.replace('_', r'\_') + '}}'


def join_terms(terms):
    result = ''
    for sign, term in terms:
        result += (' - ' if sign < 0 else ' + ' if result else '') + term
    return result or '0'


def kcl_equation(components, node):
    terms = []
    for p in components:
        a, b = branch_nodes(p)
        if a == b or node not in (a, b):
            continue
        sign = 1 if a == node else -1
        other = b if sign == 1 else a
        if p['type'] == 'R':
            terms.append((1, r'\frac{' + symbol(node) + '-' + symbol(other) + '}{' + math_number(p['value']) + '}'))
        elif p['type'] == 'I':
            outward = sign * p['value']
            if outward:
                terms.append((1 if outward > 0 else -1, math_number(abs(outward))))
        else:
            terms.append((sign, current_symbol(p['name'])))
    return join_terms(terms) + ' = 0'


def known_from_sources(components):
    """Only voltages implied by grounded voltage-source chains are givens."""
    known = {'0': 0.0}
    while True:
        before = len(known)
        for p in components:
            if p['type'] != 'V':
                continue
            if p['node2'] in known and p['node1'] not in known:
                known[p['node1']] = known[p['node2']] + p['value']
            if p['node1'] in known and p['node2'] not in known:
                known[p['node2']] = known[p['node1']] - p['value']
        if len(known) == before:
            return known


def build_lesson(components, node, reference, node_index, voltage_sources, solution):
    voltages = {'0': 0.0, **{n: float(solution[i]) for n, i in node_index.items()}}
    branches = []
    for p in components:
        a, b = branch_nodes(p)
        voltage = voltages[a] - voltages[b]
        current = branch_current(p, voltages, node_index, voltage_sources, solution)
        touching = node in (a, b)
        # A self-loop contributes no net current to KCL at its single node.
        outward = 0.0 if a == b else current if a == node else -current if b == node else 0.0
        start, end = (a, b) if current >= 0 else (b, a)
        if touching:
            count = sum(b['touching'] for b in branches) + 1
        else:
            count = None
        if p['type'] == 'OPAMP':
            action = 'into' if current > 0 else 'out of' if current < 0 else 'at'
            if opamp_mode(p) == 'open_loop':
                why = f"{p['name']}: open-loop {comparator_state(p, voltages)} output at {number(voltages[p['node3']])} V. V+ is {number(voltages[p['node1']])} V and V− is {number(voltages[p['node2']])} V; they are not forced equal. {current_label(current)} flows {action} OUT. Both input currents are zero; output energy comes through implicit supplies."
            else:
                why = f"{p['name']}: {current_label(current)} {action} the output. Both input currents are zero. Negative feedback makes V+ = V− in this linear solution; the inputs remain separate nodes. Power comes through implicit supply terminals."
        elif current == 0:
            why = f"{p['name']}: no current flows in this solved branch."
            if p['type'] == 'R':
                why += f" Both ends are at {number(voltages[p['node1']])} V, so the voltage difference is zero."
        elif p['type'] == 'R':
            why = (f"{p['name']}: {current_label(current)} flows from {start} ({number(voltages[start])} V) "
                   f"to {end} ({number(voltages[end])} V). A resistor carries conventional current from higher to lower voltage; I = ΔV/R.")
        elif p['type'] == 'I':
            why = f"{p['name']}: its specified current is {current_label(current)}, from {start} to {end}. An ideal current source sets current; its voltage is determined by the rest of the circuit."
        else:
            power = voltage * current
            action = 'supplies energy' if power < 0 else 'absorbs energy' if power > 0 else 'transfers no power'
            why = f"{p['name']}: holds {p['node1']} − {p['node2']} at {number(p['value'])} V. Its {current_label(current)} current flows from {start} to {end}; this source {action}. Voltage-source current comes from the circuit equations."
        branches.append({**p, 'branch_node1': a, 'branch_node2': b, 'current': current, 'voltage': voltage, 'outward': outward,
                         'touching': touching, 'number': count, 'direction': 1 if current > 0 else -1 if current < 0 else 0,
                         'label': current_label(current), 'why': why})

    incident = [b for b in branches if b['touching']]
    incoming = sum(-b['outward'] for b in incident if b['outward'] < 0)
    outgoing = sum(b['outward'] for b in incident if b['outward'] > 0)
    residual = outgoing - incoming
    known = known_from_sources(components)
    equations = [{'label': f'KCL at {n}', 'latex': kcl_equation(components, n)} for n in node_index]
    for p in voltage_sources:
        if p['type'] == 'OPAMP' and opamp_mode(p) == 'open_loop':
            state = comparator_state(p, voltages)
            relation = '>' if state == 'HIGH' else '<'
            equations.append({'label': f"Open-loop {state} decision from {p['name']}",
                'latex': symbol(p['node1']) + relation + symbol(p['node2']) + r'\quad\Rightarrow\quad' + symbol(p['node3']) + '=' + math_number(voltages[p['node3']]) + r'\ \mathrm{V}'})
        else:
            equations.append({'label': f"{'Linear feedback' if p['type'] == 'OPAMP' else 'Constraint'} from {p['name']}", 'latex': symbol(p['node1']) + '-' + symbol(p['node2']) + '=' + ('0' if p['type'] == 'OPAMP' else math_number(p['value']))})
    algebra = []
    if node in known:
        algebra.append({'text': 'Ground and connected voltage sources already set this node voltage.',
                        'latex': symbol(node) + '=' + math_number(known[node]) + r'\ \mathrm{V}'})
    else:
        resistors = [p for p in components if p['type'] == 'R' and p['node1'] != p['node2'] and node in (p['node1'], p['node2'])]
        has_voltage_branch = any(p['type'] in ('V', 'OPAMP') and node in branch_nodes(p) for p in components)
        neighbors = [(p, p['node2'] if p['node1'] == node else p['node1']) for p in resistors]
        if neighbors and not has_voltage_branch and all(other in known for _, other in neighbors):
            conductance = sum(1 / p['value'] for p in resistors)
            source_out = sum((p['value'] if p['node1'] == node else -p['value'])
                             for p in components if p['type'] == 'I' and p['node1'] != p['node2'] and node in (p['node1'], p['node2']))
            rhs = sum(known[other] / p['value'] for p, other in neighbors) - source_out
            algebra.append({'text': 'Substitute voltages fixed by ground and sources, then collect the selected-node terms. Conductances are in siemens and the right side is in amperes.',
                            'latex': math_number(conductance) + r'\,' + symbol(node) + '=' + math_number(rhs)})
            algebra.append({'text': 'Divide to get the node voltage relative to ground.',
                            'latex': symbol(node) + r'=\frac{' + math_number(rhs) + '}{' + math_number(conductance) + '}=' + math_number(rhs / conductance) + r'\ \mathrm{V}'})
        else:
            algebra.append({'text': 'Neighboring unknown voltages and voltage-source currents must be solved together. The full equation set below shows those dependencies.', 'latex': ''})
    tolerance = 1e-12 + 1e-8 * max(incoming, outgoing)
    feedback_amps = [p for p in components if p['type'] == 'OPAMP' and opamp_mode(p) == 'feedback']
    open_amps = [p for p in components if p['type'] == 'OPAMP' and opamp_mode(p) == 'open_loop']
    amp_notes = [f"{p['name']}: I+ = I− = 0. Feedback holds V({p['node1']}) = V({p['node2']}) = {number(voltages[p['node1']])} V. Equal voltage does not mean a wire joins the inputs. Output is {number(voltages[p['node3']])} V within {p.get('v_min', -15):g} to {p.get('v_max', 15):g} V limits."
                 for p in feedback_amps]
    for p in open_amps:
        state = comparator_state(p, voltages)
        difference = voltages[p['node1']] - voltages[p['node2']]
        amp_notes.append(f"{p['name']} OPEN LOOP: V+ = {number(voltages[p['node1']])} V, V− = {number(voltages[p['node2']])} V; difference = {number(difference)} V. The {'positive' if state == 'HIGH' else 'negative'} difference selects {state}, the configured {'maximum' if state == 'HIGH' else 'minimum'} output of {number(voltages[p['node3']])} V. I+ = I− = 0. No feedback means V+ = V− does not apply. This is an ideal DC comparator decision, not a switching-time simulation.")
    if feedback_amps:
        algebra.insert(0, {'text': 'Use zero input currents and V+ = V− together with KCL. These ideal rules apply here because negative feedback is connected and the output is within its limits.', 'latex': r'I_+=I_-=0,\qquad V_+=V_-'})
    if open_amps:
        algebra.insert(0, {'text': 'For open-loop devices, compare the input voltages and select the configured output limit. Do not use the feedback equality rule. KCL still applies, with zero input currents.',
            'latex': r'V_{out}=\begin{cases}V_{high}&V_+>V_-\\V_{low}&V_+<V_-\end{cases},\qquad I_+=I_-=0'})
    return {'node': node, 'reference': reference, 'node_voltage': voltages[node],
            'reference_voltage': voltages[reference], 'answer': voltages[node] - voltages[reference],
            'voltages': voltages, 'branches': branches, 'incident': incident,
            'incoming': incoming, 'outgoing': outgoing, 'residual': residual, 'balanced': abs(residual) <= tolerance,
            'kcl': kcl_equation(components, node), 'equations': equations, 'algebra': algebra,
            'givens': {name: value for name, value in known.items() if name != '0'},
            'notes': [
                [f"Highlighted wires and terminals form node {node}. Ideal connected wires share one voltage: {number(voltages[node])} V relative to ground.",
                 'Ground is the 0 V reference, not a place where current disappears. Current needs a complete path through the circuit.',
                 f"The requested voltage is V({node}) − V({reference}) = {number(voltages[node] - voltages[reference])} V."] + amp_notes,
                [b['why'] for b in incident] + amp_notes + ['Arrows show conventional current. Electron motion in a metal is opposite. Arrow length does not represent charge speed.'],
                ['Treat currents leaving the selected node as positive. A negative term means that branch actually brings current into the node.',
                 'For a resistor, the outward current is (selected-node voltage − other-node voltage) / resistance. Voltage-source currents are separate unknowns.',
                 'Charge does not accumulate at an ideal steady-state node, so the signed sum of its branch currents is zero.'] + amp_notes,
                [f"Entering: {current_label(incoming)}. Leaving: {current_label(outgoing)}. Their difference is {number(residual)} A.",
                 'Current divides across available branches according to the full circuit. Resistors transfer electrical energy into heat; they do not consume charge.']
            ]}
