"""Read-only checks against fixed hand-calculated circuit expectations."""
from math import isclose
from examples import get_examples
from topology import compile_drawing, validate_for_solving
from circuit_model import branch_nodes, branch_current


def verify_example(example, solve_circuit, thevenin):
    passed, total, errors = 0, 0, []

    def check(label, actual, expected, unit):
        nonlocal passed, total
        total += 1
        if isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-10):
            passed += 1
        else:
            errors.append(f'{label}: expected {expected:.8g} {unit}, got {actual:.8g} {unit}.')

    try:
        components, _ = compile_drawing(example['drawing'])
        validate_for_solving(components)
        _, index, sources, solution = solve_circuit(components)
        voltages = {'0':0.0, **{n:float(solution[i]) for n,i in index.items()}}
        currents = {}
        for p in components:
            currents[p['name']] = branch_current(p, voltages, index, sources, solution)
            if p['type'] == 'OPAMP':
                check(f"{p['name']} linear input equality", voltages[p['node1']]-voltages[p['node2']], 0, 'V')
        for node, expected in example['expected_v'].items():
            check(f'V({node})', voltages[node], expected, 'V')
        for name, expected in example['expected_i'].items():
            check(f'I({name}), pin 1 → pin 2', currents[name], expected, 'A')
        for node in voltages:
            outward = sum((int(branch_nodes(p)[0]==node)-int(branch_nodes(p)[1]==node))*currents[p['name']] for p in components)
            check(f'KCL at {node}', outward, 0, 'A')
        powers = [(voltages[branch_nodes(p)[0]]-voltages[branch_nodes(p)[1]])*currents[p['name']] for p in components]
        # Scale the power residual so the tolerance also works for larger values.
        check('Total signed power / total absolute power', sum(powers)/max(sum(abs(p) for p in powers),1e-30), 0, '')
        port = example['port']
        voltage, resistance = thevenin(components, port['node1'], port['node2'], port['load'])
        check('Thévenin voltage', voltage, port['voltage'], 'V')
        check('Thévenin resistance', resistance, port['resistance'], 'Ω')
        if abs(port['resistance']) >= 1e-12:
            check('Norton current', voltage/resistance, port['voltage']/port['resistance'], 'A')
    except Exception as error:
        total += 1
        errors.append(f'Could not complete checks: {error}')
    return {'Circuit': example['title'], 'Result': 'PASS' if not errors else 'FAIL',
            'Checks': f'{passed}/{total}', 'Details': ' '.join(errors) if errors else 'Matches hand calculations; KCL and power balance pass.'}


def verify_examples(solve_circuit, thevenin):
    return [verify_example(example, solve_circuit, thevenin) for example in get_examples()]
