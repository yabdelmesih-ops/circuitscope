"""Optional external check: py spice_validate.py --ngspice PATH --output validation.

The web app never launches external executables. This developer CLI does.
"""
import argparse
from datetime import datetime, timezone
from math import isclose, isfinite
import json
import os
import platform
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import numpy as np

from circuit_model import branch_current, without_load
from engine import solve_circuit
from examples import get_examples
from spice_export import export_spice, FEEDBACK_GAIN
from topology import compile_drawing
from verification import source_fingerprint, EXTERNAL_CHECK_FILES


def parse_operating_point(text):
    """Read one real DC point in ngspice's ASCII raw format; fail closed."""
    header, separator, data = text.partition('Values:')
    if not separator or 'Flags: real' not in header:
        raise ValueError('Expected an ASCII real operating-point raw file.')
    count = re.search(r'No\. Variables:\s*(\d+)', header)
    points = re.search(r'No\. Points:\s*(\d+)', header)
    if not count or not points or int(points[1]) != 1:
        raise ValueError('Expected exactly one DC operating point.')
    n = int(count[1])
    _, separator, declarations = header.partition('\nVariables:')
    variables = [line.split() for line in declarations.splitlines() if line.strip()]
    if not separator or len(variables) != n or any(len(v) != 3 or v[0] != str(i) for i, v in enumerate(variables)):
        raise ValueError('Invalid raw-file variable declarations.')
    tokens = data.split()
    if len(tokens) != n + 1 or tokens[0] != '0':
        raise ValueError('Unexpected operating-point value count.')
    values = [float(v) for v in tokens[1:]]
    if not all(isfinite(v) for v in values):
        raise ValueError('SPICE returned a non-finite value.')
    result = {v[1].lower(): value for v, value in zip(variables, values)}
    if len(result) != n:
        raise ValueError('Duplicate SPICE variables.')
    return result


def run_ngspice(exported, executable='ngspice'):
    executable = shutil.which(str(executable)) or str(Path(executable).expanduser().resolve())
    with tempfile.TemporaryDirectory(prefix='circuitscope-spice-') as directory:
        root = Path(directory)
        (root / 'input.cir').write_text(exported['netlist'], encoding='utf-8')
        environment = os.environ.copy()
        environment['SPICE_ASCIIRAWFILE'] = '1'
        completed = subprocess.run([str(executable), '-n', '-b', '-r', 'result.raw', 'input.cir'],
            cwd=root, env=environment, capture_output=True, text=True, timeout=20)
        raw = root / 'result.raw'
        if completed.returncode != 0 or not raw.is_file():
            raise ValueError('ngspice failed: ' + (completed.stderr + completed.stdout)[-1800:])
        vectors = parse_operating_point(raw.read_text(encoding='utf-8'))
    voltages = {'0': 0.0}
    for original, node in exported['node_map'].items():
        if node != '0':
            voltages[original] = vectors[f'v({node.lower()})']
    return voltages, vectors


def spice_currents(components, exported, voltages, vectors):
    result = {}
    for p in components:
        if p['type'] == 'R':
            current = (voltages[p['node1']] - voltages[p['node2']]) / p['value']
        elif p['type'] == 'I':
            current = p['value']
        else:
            current = vectors['i(' + exported['element_map'][p['name']].lower() + ')']
        result[p['name']] = current
    return result


def compare_case(example, configuration, components, executable):
    checks, errors, maximum_voltage_error = 0, [], 0.0
    exported = export_spice(components, dialect='ngspice')
    actual, vectors = run_ngspice(exported, executable)
    currents = spice_currents(components, exported, actual, vectors)
    _, index, sources, solution = solve_circuit(components)
    engine_volts = {'0': 0.0, **{n: float(solution[i]) for n, i in index.items()}}

    def check(label, got, expected, unit):
        nonlocal checks, maximum_voltage_error
        checks += 1
        if unit == 'V':
            maximum_voltage_error = max(maximum_voltage_error, abs(got - expected))
        absolute = 1e-8 if unit in ('V', 'ohm') else 1e-10
        if not isclose(got, expected, rel_tol=1e-6, abs_tol=absolute):
            errors.append(f'{label}: SPICE {got:.10g}, expected {expected:.10g} {unit}')

    for n, value in engine_volts.items():
        check(f'CircuitScope V({n})', actual[n], value, 'V')
    for p in components:
        check('CircuitScope I(' + p['name'] + ')', currents[p['name']],
              branch_current(p, engine_volts, index, sources, solution), 'A')
    if configuration == 'drawing':
        for n, value in example['expected_v'].items():
            check(f'Hand V({n})', actual[n], value, 'V')
        for name, value in example['expected_i'].items():
            check(f'Hand I({name})', currents[name], value, 'A')
    else:
        port = example['port']
        difference = actual[port['node1']] - actual[port['node2']]
        check('Hand port ' + ('voltage' if configuration == 'open_port' else 'resistance at 1 A'),
              difference, port['voltage'] if configuration == 'open_port' else port['resistance'],
              'V' if configuration == 'open_port' else 'ohm')
    return dict(Circuit=example['title'], Configuration=configuration, Result='FAIL' if errors else 'PASS',
                Checks=checks, Max_voltage_error_V=maximum_voltage_error,
                Details='; '.join(errors) if errors else 'SPICE, CircuitScope and applicable fixed hand references agree.'), exported


def validate_examples(executable, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    decks = output / 'spice'
    (decks / 'ngspice').mkdir(parents=True, exist_ok=True)
    (decks / 'ltspice').mkdir(parents=True, exist_ok=True)
    rows = []
    for example in get_examples():
        parts, _ = compile_drawing(example['drawing'])
        configurations = [('drawing', parts)]
        if example['port'] is not None:
            port = example['port']
            opened = without_load(parts, port['load'])
            configurations.append(('open_port', opened))
            test = without_load(parts, port['load'])
            for p in test:
                if p['type'] in ('V', 'I'):
                    p['value'] = 0
            name = 'Itest'
            while any(p['name'] == name for p in test):
                name += '_'
            test.append(dict(name=name, type='I', node1=port['node2'], node2=port['node1'], value=1))
            configurations.append(('resistance_test', test))
        for configuration, components in configurations:
            filename = example['id'] + '_' + configuration + '.cir'
            try:
                row, exported = compare_case(example, configuration, components, executable)
                (decks / 'ngspice' / filename).write_text(exported['netlist'], encoding='utf-8')
                (decks / 'ltspice' / filename).write_text(export_spice(components)['netlist'], encoding='utf-8')
            except Exception as error:
                row = dict(Circuit=example['title'], Configuration=configuration, Result='FAIL', Checks=0,
                           Max_voltage_error_V=None, Details=str(error))
            rows.append(row)
    version = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=10)
    version_text = next((line.strip('* ') for line in (version.stdout + version.stderr).splitlines() if 'ngspice-' in line.lower()), 'ngspice (version not reported)')
    report = dict(schema='circuitscope.spice-check.v1', generated_utc=datetime.now(timezone.utc).isoformat(),
        simulator=version_text, source_hashes=source_fingerprint(EXTERNAL_CHECK_FILES), rows=rows,
        environment=dict(python=sys.version.split()[0], numpy=np.__version__, platform=platform.system()),
        models=dict(feedback_gain=FEEDBACK_GAIN, comparator='ideal two-level behavioral source'),
        tolerances=dict(relative=1e-6, voltage_absolute_V=1e-8, current_absolute_A=1e-10, resistance_absolute_ohm=1e-8),
        scope=f'{len(rows)} DC configurations: ' + ', '.join(f'{sum(r["Configuration"] == key for r in rows)} {label}' for key, label in [('drawing','original drawings'),('open_port','open-port tests'),('resistance_test','1 A resistance tests')]) + '. Feedback amps use finite gain 1e9. Comparator expression threshold behavior differs from the app guard. LTspice decks are provided, but LTspice itself was not run. Native Windows browser behavior is not covered.')
    (output / 'spice_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ngspice', default=shutil.which('ngspice'))
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'validation')
    args = parser.parse_args()
    if not args.ngspice:
        parser.error('Install ngspice or pass --ngspice PATH. The app and netlist export work without it.')
    args.ngspice = shutil.which(str(args.ngspice)) or str(Path(args.ngspice).expanduser().resolve())
    report = validate_examples(args.ngspice, args.output)
    for row in report['rows']:
        print(row['Result'], row['Configuration'], row['Circuit'], row['Details'] if row['Result'] != 'PASS' else '')
    passed = sum(row['Result'] == 'PASS' for row in report['rows'])
    print(f'{passed}/{len(report["rows"])} configurations; {sum(row["Checks"] for row in report["rows"])} comparisons.')
    return 0 if passed == len(report['rows']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
