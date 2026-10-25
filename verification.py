"""Read-only checks against fixed hand-calculated circuit expectations."""
from math import isclose
from hashlib import sha256
import json
from pathlib import Path
from examples import get_examples
from topology import compile_drawing, validate_for_solving
from circuit_model import branch_nodes, branch_current, opamp_mode, OPEN_LOOP_EPS

BASE = Path(__file__).parent
INTERNAL_CHECK_FILES = ('engine.py', 'circuit_model.py', 'topology.py', 'examples.py', 'opamp_examples.py', 'verification.py')
EXTERNAL_CHECK_FILES = INTERNAL_CHECK_FILES + ('spice_export.py', 'spice_validate.py')


def source_fingerprint(files=INTERNAL_CHECK_FILES, base=BASE):
    return {name: sha256((Path(base) / name).read_bytes()).hexdigest() for name in files}


def load_spice_report(base=BASE):
    """A report describes one source revision, never a claim about later edits."""
    try:
        report = json.loads((Path(base) / 'validation' / 'spice_report.json').read_text(encoding='utf-8'))
        if report.get('schema') != 'circuitscope.spice-check.v1' or not isinstance(report.get('rows'), list) or not report['rows']:
            return None, 'The external verification report is invalid.'
        if report.get('source_hashes') != source_fingerprint(EXTERNAL_CHECK_FILES, base):
            return None, 'The solver or validation source changed after this external report. Rerun spice_validate.py to refresh it.'
        if any(not isinstance(row, dict) or row.get('Result') not in ('PASS', 'FAIL') for row in report['rows']):
            return None, 'The external verification report has invalid result rows.'
        return report, None
    except (OSError, ValueError, TypeError, AttributeError):
        return None, 'No readable external verification report is included.'


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
                difference = voltages[p['node1']]-voltages[p['node2']]
                if opamp_mode(p) == 'open_loop':
                    if abs(difference) <= OPEN_LOOP_EPS:
                        raise ValueError('Undefined comparator threshold in reference circuit.')
                    expected_level = p.get('v_max',15) if difference > 0 else p.get('v_min',-15)
                    check(f"{p['name']} comparator output limit", voltages[p['node3']], expected_level, 'V')
                else:
                    check(f"{p['name']} linear input equality", difference, 0, 'V')
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
        if port is not None:
            voltage, resistance = thevenin(components, port['node1'], port['node2'], port['load'])
            check('Thévenin voltage', voltage, port['voltage'], 'V')
            check('Thévenin resistance', resistance, port['resistance'], 'Ω')
            if abs(port['resistance']) >= 1e-12:
                check('Norton current', voltage/resistance, port['voltage']/port['resistance'], 'A')
    except Exception as error:
        total += 1
        errors.append(f'Could not complete checks: {error}')
    return {'Circuit': example['title'], 'Result': 'PASS' if not errors else 'FAIL',
            'Checks': f'{passed}/{total}', 'Details': ' '.join(errors) if errors else 'Matches hand calculations; KCL and power balance pass.' + (' Nonlinear comparator: no global Thévenin/Norton check.' if example['port'] is None else '')}


def verify_examples(solve_circuit, thevenin):
    return [verify_example(example, solve_circuit, thevenin) for example in get_examples()]
