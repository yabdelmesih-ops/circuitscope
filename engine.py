"""Modified nodal analysis: R, independent V/I and ideal feedback op amps.

Unknowns: node voltages, voltage-source currents, op-amp output currents.
"""
import numpy as np
from circuit_model import component_nodes, validate_opamps, without_load


def solve_circuit(components, *, check_rails=True):
    validate_opamps(components)
    nodes = sorted({n for p in components for n in component_nodes(p) if n != '0'})
    node_index = {name: i for i, name in enumerate(nodes)}
    voltage_sources = [p for p in components if p['type'] in ('V', 'OPAMP')]
    size = len(nodes) + len(voltage_sources)
    A, b = np.zeros((size, size)), np.zeros(size)
    for part in components:
        i, j = node_index.get(part['node1']), node_index.get(part['node2'])
        kind, value = part['type'], part.get('value')
        if kind == 'R':
            if not np.isfinite(value) or value <= 0:
                raise ValueError('Resistance must be finite and positive.')
            g = 1 / value
            if i is not None:
                A[i, i] += g
            if j is not None:
                A[j, j] += g
            if i is not None and j is not None:
                A[i, j] -= g
                A[j, i] -= g
        elif kind == 'I':
            # Positive current flows from node1 to node2.
            if i is not None:
                b[i] -= value
            if j is not None:
                b[j] += value
        elif kind in ('V', 'OPAMP'):
            k = len(nodes) + voltage_sources.index(part)
            if kind == 'V':
                if i is not None:
                    A[i, k] += 1
                    A[k, i] += 1
                if j is not None:
                    A[j, k] -= 1
                    A[k, j] -= 1
                b[k] = value
            else:
                # Inputs draw no current: stamp output current only.
                out = node_index.get(part['node3'])
                if out is not None:
                    A[out, k] += 1
                # V+ = V− under negative feedback in the linear region.
                # This constraint does NOT connect the input nodes by a wire.
                if i is not None:
                    A[k, i] += 1
                if j is not None:
                    A[k, j] -= 1
        else:
            raise ValueError(f'Unsupported component type: {kind}.')
    try:
        solution = np.linalg.solve(A, b)
    except np.linalg.LinAlgError as error:
        raise ValueError('No unique DC solution. Check floating nodes, feedback and conflicting or redundant ideal sources.') from error
    if not np.all(np.isfinite(solution)):
        raise ValueError('No finite DC solution.')
    if check_rails:
        for p in components:
            if p['type'] == 'OPAMP':
                output = float(solution[node_index[p['node3']]]) if p['node3'] != '0' else 0.0
                low, high = p.get('v_min', -15), p.get('v_max', 15)
                tolerance = 1e-9 * max(1, abs(low), abs(high))
                if output < low - tolerance or output > high + tolerance:
                    raise ValueError(f"{p['name']} needs {output:.6g} V, outside its {low:g} to {high:g} V output limits. It would saturate; V+ = V− is no longer valid. Reduce the input/gain or change the limits. Saturation is not simulated.")
    return nodes, node_index, voltage_sources, solution


def get_voltages(circuit, *, check_rails=True):
    _, index, _, solution = solve_circuit(circuit, check_rails=check_rails)
    return {'0': 0.0, **{name: float(solution[i]) for name, i in index.items()}}


def open_circuit_voltage(circuit, node1, node2='0', load=None):
    working = without_load(circuit, load)
    present = {n for p in working for n in component_nodes(p)}
    if node1 not in present or node2 not in present:
        raise ValueError('Connect both output terminals to circuit nodes that remain after removing the load. A floating terminal has no defined voltage.')
    voltages = get_voltages(working)
    return voltages[node1] - voltages[node2]


def thevenin(circuit, node1, node2='0', load=None):
    if node1 == node2:
        raise ValueError('Choose two different port nodes.')
    Vth = open_circuit_voltage(circuit, node1, node2, load)
    working = without_load(circuit, load)
    # Deactivate independent sources only; feedback amplifiers stay active.
    for part in working:
        if part['type'] in ('V', 'I'):
            part['value'] = 0
    used, name = {p['name'] for p in working}, 'Itest'
    while name in used:
        name += '_'
    working.append(dict(name=name, type='I', node1=node2, node2=node1, value=1))
    # Algebraic resistance test, not a physical 1 A operating point.
    voltages = get_voltages(working, check_rails=False)
    return Vth, voltages[node1] - voltages[node2]
