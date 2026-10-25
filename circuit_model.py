"""Shared electrical conventions; probes never become solver branches."""
from math import isfinite

# Numerical guard at the ideal comparator's discontinuous threshold. This is
# neither hysteresis nor an input offset; we refuse to guess inside this band.
OPEN_LOOP_EPS = 1e-9


def opamp_mode(part):
    return part.get('mode', 'feedback')


def comparator_state(part, voltages):
    difference = voltages[part['node1']] - voltages[part['node2']]
    return 'HIGH' if difference > OPEN_LOOP_EPS else 'LOW' if difference < -OPEN_LOOP_EPS else 'UNDEFINED'


def component_nodes(part):
    return (part['node1'], part['node2'], part['node3']) if part['type'] == 'OPAMP' else (part['node1'], part['node2'])


def branch_nodes(part):
    # Output current INTO the amplifier; implicit ground/supply return.
    return (part['node3'], '0') if part['type'] == 'OPAMP' else (part['node1'], part['node2'])


def branch_current(part, voltages, index, sources, solution):
    a, b = branch_nodes(part)
    if part['type'] == 'R':
        return (voltages[a] - voltages[b]) / part['value']
    if part['type'] == 'I':
        return part['value']
    return float(solution[len(index) + sources.index(part)])


def without_load(circuit, load=None):
    if load is not None:
        selected = next((p for p in circuit if p['name'] == load), None)
        if selected is None or selected['type'] != 'R':
            raise ValueError('Select an external load resistor to remove.')
    return [p.copy() for p in circuit if p['name'] != load]


def validate_opamps(components):
    """Conservative DC passive-feedback check, not an AC stability test.

    Open-loop comparators must have no path from output back to either input,
    including through another amplifier. This is not an AC stability test.
    """
    amps = [p for p in components if p['type'] == 'OPAMP']
    if not amps:
        return
    fixed = {'0'}
    while True:
        old = len(fixed)
        for p in components:
            if p['type'] == 'V' and fixed.intersection(component_nodes(p)):
                fixed.update(component_nodes(p))
        if len(fixed) == old:
            break
    graph = {}
    for p in components:
        if p['type'] == 'R':
            a, b = component_nodes(p)
            if a not in fixed and b not in fixed:
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)
    for amp in amps:
        mode = opamp_mode(amp)
        if mode not in ('feedback', 'open_loop'):
            raise ValueError(f"{amp['name']}: choose feedback or open_loop mode.")
        low, high = amp.get('v_min', -15), amp.get('v_max', 15)
        if not all(isinstance(v, (int, float)) and isfinite(v) for v in (low, high)) or low >= high:
            raise ValueError(f"{amp['name']}: output limits must be finite, with minimum below maximum.")
        plus, minus, output = component_nodes(amp)
        if plus == minus:
            if mode == 'open_loop':
                raise ValueError(f"{amp['name']}: equal inputs make the ideal open-loop output undefined. Choose different input voltages.")
            raise ValueError(f"{amp['name']}: + and − are wired together; the output would be undetermined. Keep inputs separate.")
        if mode == 'open_loop':
            # Passive voltage dependencies are bidirectional. Other amplifiers
            # propagate an input change toward their output, including cascades.
            # Exclude this amplifier's own input-to-output edges when looking
            # for an external route that would close its loop.
            dependencies = {n: set(edges) for n, edges in graph.items()}
            for p in components:
                if p['type'] == 'V':
                    a, b = component_nodes(p)
                    if a not in fixed and b not in fixed:
                        dependencies.setdefault(a, set()).add(b)
                        dependencies.setdefault(b, set()).add(a)
            for other in amps:
                if other is not amp:
                    for pin in (other['node1'], other['node2']):
                        if pin not in fixed and other['node3'] not in fixed:
                            dependencies.setdefault(pin, set()).add(other['node3'])
            reached, todo = set(), [output]
            while todo:
                node = todo.pop()
                if node not in reached:
                    reached.add(node)
                    todo.extend(dependencies.get(node, set()) - reached)
            if output in fixed:
                raise ValueError(f"{amp['name']}: do not short the comparator output to ground or an ideal voltage source.")
            if plus in reached or minus in reached:
                raise ValueError(f"{amp['name']}: open-loop mode requires no feedback from OUT to either input. Remove that path or choose negative-feedback mode. Latches and hysteresis are not supported.")
            continue
        reached, todo = set(), [output] if output not in fixed else []
        while todo:
            node = todo.pop()
            if node not in reached:
                reached.add(node)
                todo.extend(graph.get(node, set()) - reached)
        if minus not in reached:
            raise ValueError(f"{amp['name']}: connect output to the − input directly or through resistors for negative feedback, or select Open loop (comparator) in its properties.")
        if plus in reached:
            raise ValueError(f"{amp['name']}: positive or mixed feedback is outside this ideal linear DC model.")
