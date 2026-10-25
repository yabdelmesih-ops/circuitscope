"""Turn explicit terminal-to-terminal wires into the component list our solver uses.

This module does no circuit solving. It only determines which terminals are
on the same electrical node. Node 0 is ground.
"""
from math import isfinite
import re
from circuit_model import component_nodes, validate_opamps


def terminals(item):
    """Ground and junction dots have one pin; R, V, I have two."""
    count = 1 if item['type'] in ('GROUND', 'J') else 3 if item['type'] == 'OPAMP' else 2
    return [f"{item['id']}:{pin}" for pin in range(1, count + 1)]


def compile_drawing(drawing):
    """Return (components, terminal_nodes) from a drawing dictionary.

    'parent' groups pins connected by wires (a disjoint-set/union-find).
    Coordinates only draw the picture; crossing lines do not connect.
    """
    if not isinstance(drawing, dict):
        raise ValueError('Open a CircuitScope canvas project.')
    items, wires = drawing.get('items'), drawing.get('wires')
    if not isinstance(items, list) or not isinstance(wires, list):
        raise ValueError('A drawing needs items and wires lists.')
    if len(items) > 60 or len(wires) > 200:
        raise ValueError('Maximum 60 placed items and 200 wires.')

    ids, parent = set(), {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Invalid component entry.')
        name = item.get('id', '')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,15}', name):
            raise ValueError('Component IDs must begin with a letter and use letters, digits or underscores.')
        if name.lower() in ids:
            raise ValueError('Every component needs a unique ID.')
        ids.add(name.lower())
        if item.get('type') not in ('R', 'V', 'I', 'OPAMP', 'PORT', 'GROUND', 'J'):
            raise ValueError(f'{name}: unsupported component type.')
        for key, maximum in (('x', 1100), ('y', 680)):
            value = item.get(key)
            minimum = 0 if item['type'] == 'J' else 40
            maximum = (1140 if key == 'x' else 720) if item['type'] == 'J' else maximum
            if not isinstance(value, (float, int)) or not isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(f'{name}: invalid drawing coordinates.')
        if item.get('rotation', 0) not in (0, 90, 180, 270):
            raise ValueError(f'{name}: invalid rotation.')
        if item['type'] in ('R', 'V', 'I'):
            value = item.get('value')
            if not isinstance(value, (float, int)) or not isfinite(value):
                raise ValueError(f'{name}: enter a finite component value.')
            if item['type'] == 'R' and value <= 0:
                raise ValueError(f'{name}: resistance must be positive.')
        if item['type'] == 'OPAMP':
            low, high = item.get('v_min', -15), item.get('v_max', 15)
            if not all(isinstance(v, (int, float)) and isfinite(v) for v in (low, high)) or low >= high:
                raise ValueError(f'{name}: output limits must be finite and minimum < maximum.')
        for pin in terminals(item):
            parent[pin] = pin

    def find(pin):
        while parent[pin] != pin:
            parent[pin] = parent[parent[pin]]
            pin = parent[pin]
        return pin

    def connect(first, second):
        parent[find(second)] = find(first)

    wire_ids = set()
    for wire in wires:
        if not isinstance(wire, dict) or not isinstance(wire.get('id'), str) or wire['id'] in wire_ids:
            raise ValueError('Every wire needs a unique ID.')
        wire_ids.add(wire['id'])
        if wire.get('a') not in parent or wire.get('b') not in parent:
            raise ValueError('A wire points to a missing terminal.')
        via = wire.get('via', [])
        if not isinstance(via, list) or len(via) > 200:
            raise ValueError('A wire can have at most 200 routing points.')
        for point in via:
            if not isinstance(point, dict) or any(
                not isinstance(point.get(axis), (float, int)) or not isfinite(point[axis]) or not 0 <= point[axis] <= maximum
                for axis, maximum in (('x', 1140), ('y', 720))
            ):
                raise ValueError('A wire has an invalid routing point.')
        connect(wire['a'], wire['b'])

    # All ground symbols are one electrical reference, even when drawn apart.
    ground_pins = [terminals(i)[0] for i in items if i['type'] == 'GROUND']
    for pin in ground_pins[1:]:
        connect(ground_pins[0], pin)
    names = {find(ground_pins[0]): '0'} if ground_pins else {}
    used_names = {'0'}

    # Optional labels let the user name a node Va, Vb, etc.
    for item in items:
        for number, pin in enumerate(terminals(item), 1):
            label = item.get(f'label{number}', '')
            if not isinstance(label, str):
                raise ValueError('Node labels must be text.')
            label = label.strip()
            if not label:
                continue
            if label == '0':
                raise ValueError('Connect a ground symbol to make node 0; clear the typed 0 label.')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,11}', label):
                raise ValueError('Node labels use 1–12 letters/digits/underscores, beginning with a letter.')
            root = find(pin)
            if root in names and names[root] != label:
                raise ValueError('Connected terminals have conflicting labels. Select a component and clear one label.')
            if any(r != root and n.lower() == label.lower() for r, n in names.items()):
                raise ValueError(f'Label {label} is used on two separate nodes. Wire them together or rename one.')
            names[root] = label
            used_names.add(label.lower())

    counter = 1
    terminal_nodes = {}
    for pin in parent:
        root = find(pin)
        if root not in names:
            while f'N{counter}'.lower() in used_names:
                counter += 1
            names[root] = f'N{counter}'
            used_names.add(f'N{counter}'.lower())
            counter += 1
        terminal_nodes[pin] = names[root]

    # This is the exact dictionary format used in the original Python lessons.
    components = []
    for item in items:
        if item['type'] in ('R', 'V', 'I'):
            components.append({
                'name': item['id'], 'type': item['type'],
                'node1': terminal_nodes[f"{item['id']}:1"],
                'node2': terminal_nodes[f"{item['id']}:2"],
                'value': float(item['value']),
            })
        elif item['type'] == 'OPAMP':
            components.append(dict(name=item['id'], type='OPAMP',
                node1=terminal_nodes[f"{item['id']}:1"], node2=terminal_nodes[f"{item['id']}:2"],
                node3=terminal_nodes[f"{item['id']}:3"],
                v_min=float(item.get('v_min', -15)), v_max=float(item.get('v_max', 15))))
        # PORT is an infinite-resistance voltmeter. Its two pins stay separate
        # and it adds no electrical branch or extra equation.
    return components, terminal_nodes


def validate_for_solving(components):
    """Catch common incomplete drawings before NumPy sees their equations."""
    if not components:
        raise ValueError('Place at least one circuit component.')
    nodes = {n for p in components for n in component_nodes(p)}
    if '0' not in nodes:
        raise ValueError('Add a ground symbol and wire it to the circuit.')
    reached = {'0'}
    reached.update(p['node3'] for p in components if p['type'] == 'OPAMP')
    while True:
        before = len(reached)
        for p in components:
            # An ideal current source does not fix a node potential.
            if p['type'] in ('R', 'V') and (p['node1'] in reached or p['node2'] in reached):
                reached.update((p['node1'], p['node2']))
        if len(reached) == before:
            break
    floating = sorted(nodes - reached)
    if floating:
        raise ValueError('Floating node(s): ' + ', '.join(floating) + '. Connect all component terminals.')
    for p in components:
        if p['type'] == 'V' and p['node1'] == p['node2']:
            raise ValueError(f"{p['name']} is shorted. Check its wires.")
    validate_opamps(components)


def output_ports(drawing, terminal_nodes):
    """Return visual probes including disconnected ends, for useful UI errors."""
    return {p['id']: (terminal_nodes[f"{p['id']}:1"], terminal_nodes[f"{p['id']}:2"])
            for p in drawing['items'] if p['type'] == 'PORT'}
