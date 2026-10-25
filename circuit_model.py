"""Shared electrical conventions; probes never become solver branches."""
from math import isfinite


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

    Mixed positive feedback, active feedback and comparators are unsupported.
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
        low, high = amp.get('v_min', -15), amp.get('v_max', 15)
        if not all(isinstance(v, (int, float)) and isfinite(v) for v in (low, high)) or low >= high:
            raise ValueError(f"{amp['name']}: output limits must be finite, with minimum below maximum.")
        plus, minus, output = component_nodes(amp)
        if plus == minus:
            raise ValueError(f"{amp['name']}: + and − are wired together; the output would be undetermined. Keep inputs separate.")
        reached, todo = set(), [output] if output not in fixed else []
        while todo:
            node = todo.pop()
            if node not in reached:
                reached.add(node)
                todo.extend(graph.get(node, set()) - reached)
        if minus not in reached:
            raise ValueError(f"{amp['name']}: connect output to the − input directly or through resistors for negative feedback. Open-loop operation is not supported.")
        if plus in reached:
            raise ValueError(f"{amp['name']}: positive or mixed feedback is outside this ideal linear DC model.")
