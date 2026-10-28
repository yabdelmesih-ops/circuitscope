"""Convert an explicit netlist into editable canvas wiring and a safe preview."""
from html import escape
from math import cos, sin, radians
from topology import compile_drawing, terminals


def pin_positions(item):
    offsets = [(0, -20)] if item['type'] == 'GROUND' else [(0, 0)] if item['type'] == 'J' else [(-60, -20), (-60, 20), (60, 0)] if item['type'] == 'OPAMP' else [(-40, 0), (40, 0)]
    angle = radians(item.get('rotation', 0))
    c, s = round(cos(angle)), round(sin(angle))
    return [(item['x'] + x*c-y*s, item['y']+x*s+y*c) for x, y in offsets]


def netlist_to_drawing(components, *, positions=None):
    """Labels never make connections: every shared node receives explicit wires.

    Positions may override the default grid for method previews.
    """
    if not isinstance(components, list) or not 1 <= len(components) <= 24:
        raise ValueError('Lay out 1–24 supported components at a time.')
    items, groups = [], {}
    used = {p.get('name') for p in components if isinstance(p, dict)}
    if len(used) != len(components):
        raise ValueError('Component names must be unique.')
    for i, p in enumerate(components):
        if p.get('type') not in ('R', 'V', 'I', 'OPAMP', 'PORT'):
            raise ValueError('Use resistors, independent V/I sources, ideal op amps or probes.')
        x, y = 160 + (i % 4)*260, 110 + (i//4)*100
        location = (positions or {}).get(p['name'], {})
        item = dict(id=p['name'], type=p['type'], x=location.get('x', x), y=location.get('y', y),
                    rotation=location.get('rotation', 0))
        if p['type'] in ('R', 'V', 'I'):
            item['value'] = p.get('value')
        if p['type'] == 'OPAMP':
            item.update(mode=p.get('mode', 'feedback'), v_min=p.get('v_min', -15), v_max=p.get('v_max', 15))
        for n, pin in enumerate(terminals(item), 1):
            node = p.get(f'node{n}')
            if not isinstance(node, str) or not node:
                raise ValueError(f"{p['name']}: enter every terminal's node name.")
            item[f'label{n}'] = '' if node == '0' else node
            groups.setdefault(node, []).append(pin)
        items.append(item)
    if '0' not in groups:
        raise ValueError('Identify a reference node named 0 before laying out the circuit.')
    if len(groups) > 40:
        raise ValueError('Lay out at most 40 electrical nodes.')
    ground = 'GNDlayout'
    while ground in used:
        ground += '_'
    items.append(dict(id=ground, type='GROUND', x=80, y=660, rotation=0))
    groups['0'].append(ground+':1')
    wires = []
    for pins in groups.values():
        for pin in pins[1:]:
            wires.append(dict(id=f'w{len(wires)+1}', a=pins[0], b=pin, bend='hv'))
    model = dict(schema='circuitscope.canvas.v1', items=items, wires=wires)
    compile_drawing(model)
    return model


def preview_svg(drawing):
    """Only our own SVG elements are generated; labels are always escaped."""
    compile_drawing(drawing)
    endpoints = {pin: xy for item in drawing['items'] for pin, xy in zip(terminals(item), pin_positions(item))}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1140 720" width="1140" height="720"><rect width="1140" height="720" fill="#fafdf8"/>']
    for wire in drawing['wires']:
        points = [endpoints[wire['a']], *[(p['x'], p['y']) for p in wire.get('via', [])], endpoints[wire['b']]]
        d = f'M{points[0][0]} {points[0][1]}'
        for x, y in points[1:]:
            d += f' H{x} V{y}' if wire.get('bend') != 'vh' else f' V{y} H{x}'
        svg.append(f'<path d="{d}" fill="none" stroke="#648f70" stroke-width="2"/>')
    for item in drawing['items']:
        kind = item['type']
        shape = '<circle r="5"/>'
        if kind == 'R':
            shape = '<path d="M-40 0h12l5-10 8 20 8-20 8 20 8-20 8 20 5-10h18"/>'
        elif kind in ('V', 'I', 'PORT'):
            text = '+' if kind == 'V' else '→' if kind == 'I' else 'V'
            shape = f'<path d="M-40 0h17m46 0h17"/><circle r="23" fill="white"/><text x="0" y="6" text-anchor="middle" fill="#416d4b" stroke="none" font-size="20">{text}</text>'
        elif kind == 'OPAMP':
            shape = '<path d="M-60-20h20m-20 40h20m80-20h20M-40-44V44L40 0Z" fill="white"/><text x="-31" y="-14" fill="#416d4b" stroke="none">+</text><text x="-31" y="26" fill="#416d4b" stroke="none">−</text>'
        elif kind == 'GROUND':
            shape = '<path d="M0-20V0m-18 0h36m-29 7h22m-16 7h10"/>'
        svg.append(f'<g transform="translate({item["x"]},{item["y"]}) rotate({item.get("rotation",0)})" fill="none" stroke="#416d4b" stroke-width="2">{shape}</g>')
        label = item['id'] + (f" · {item['value']:g} {'Ω' if kind=='R' else 'V' if kind=='V' else 'A'}" if 'value' in item else '')
        svg.append(f'<text x="{item["x"]}" y="{item["y"]-52}" font-family="sans-serif" font-size="14" text-anchor="middle" fill="#253d31">{escape(label)}</text>')
        for n, (x, y) in enumerate(pin_positions(item), 1):
            label = item.get(f'label{n}', '')
            svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="white" stroke="#416d4b"/><text x="{x+8}" y="{y+17}" font-family="sans-serif" font-size="11" fill="#253d31">{escape(label)}</text>')
    return ''.join(svg)+'</svg>'
