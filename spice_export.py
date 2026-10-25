"""Export a checked DC operating point for LTspice or ngspice.

Feedback amps use a finite-gain E source, so this is an approximation to the
app's infinite-gain model. Comparators use B sources. No vendor models needed.
"""
from math import isfinite
import re
from circuit_model import component_nodes, opamp_mode, without_load
from engine import get_voltages
from topology import validate_for_solving

FEEDBACK_GAIN = 1e9


def export_spice(components, *, dialect='ltspice', load=None):
    if dialect not in ('ltspice', 'ngspice'):
        raise ValueError('Choose ltspice or ngspice for the export format.')
    working = without_load(components, load)
    validate_for_solving(working)
    # Reject floating inputs, invalid feedback, threshold ambiguity and invalid
    # linear output ranges before emitting a deceptively runnable deck.
    reference = get_voltages(working)
    used = set()
    for p in working:
        name = p['name']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,15}', name) or name.lower() in used:
            raise ValueError('Use unique component names containing only letters, digits and underscores.')
        used.add(name.lower())
    original_nodes = sorted({n for p in working for n in component_nodes(p) if n != '0'})
    # Mapping prevents aliases such as GND, case-folded names and directives
    # embedded in labels from changing the exported electrical connectivity.
    nodes = {'0': '0', **{n: f'n{i}' for i, n in enumerate(original_nodes, 1)}}
    elements, lines = {}, ['* CircuitScope DC operating point',
        f'* Format: {dialect}; configuration: ' + (f'load {load} removed' if load else 'full drawing'),
        '* Probes add no electrical branch. All source values are SI numbers.']
    for node, mapped in nodes.items():
        # repr escapes newlines; node names themselves never enter SPICE syntax.
        lines.append(f'* Node {mapped} = {node!r}')
    notes = []
    if any(p['type'] == 'OPAMP' and opamp_mode(p) == 'feedback' for p in working):
        notes.append('Feedback op amps use finite gain 1e9 in SPICE, approximating CircuitScope’s infinite-gain model. Output limits are checked before export; the E source itself does not clip.')
    if any(p['type'] == 'OPAMP' and opamp_mode(p) == 'open_loop' for p in working):
        notes.append('Comparators use ideal two-level behavioral sources. Threshold ambiguity is checked before export; the raw SPICE expression chooses LOW at equality and has no 1 nV guard. Recheck inputs after editing the file.')
    notes.append('This exports an operating point, not a schematic or a physical op-amp model. Supplies are implicit; no timing, bias, current limit or real-chip behavior is modeled.')
    for note in notes:
        lines.append('* ' + note)
    for p in working:
        kind = p['type']
        prefix = ('B' if opamp_mode(p) == 'open_loop' else 'E') if kind == 'OPAMP' else kind
        element = prefix + '_' + p['name']
        elements[p['name']] = element
        a, b = nodes[p['node1']], nodes[p['node2']]
        if kind in ('R', 'V', 'I'):
            value = p['value']
            if not isfinite(value):
                raise ValueError('SPICE values must be finite.')
            lines.append(f'{element} {a} {b} {value:.17g}')
        elif kind == 'OPAMP':
            out = nodes[p['node3']]
            if opamp_mode(p) == 'feedback':
                lines.append(f'{element} {out} 0 {a} {b} {FEEDBACK_GAIN:.17g}')
            else:
                high, low = p.get('v_max', 15), p.get('v_min', -15)
                difference = f'(V({a})-V({b}))'
                expression = f'if({difference}>0,{high:.17g},{low:.17g})' if dialect == 'ltspice' else f'{difference}>0 ? {high:.17g} : {low:.17g}'
                lines.append(f'{element} {out} 0 V={expression}')
        else:
            raise ValueError(f'Cannot export unsupported component type {kind}.')
    lines += ['.options reltol=1e-8 abstol=1e-12 vntol=1e-10', '.save all', '.op', '.end', '']
    return dict(netlist='\n'.join(lines), node_map=nodes, element_map=elements,
                reference_voltages=reference, notes=notes, dialect=dialect, removed_load=load)
