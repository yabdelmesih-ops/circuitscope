"""Drawn reference circuits with independently derived, fixed expectations.

Expected numbers below come from the displayed hand equations, not the engine.
"""
import json
from pathlib import Path


def part(name, kind, value, x, y, rotation=0, label1='', label2=''):
    item = dict(id=name, type=kind, x=x, y=y, rotation=rotation, label1=label1, label2=label2)
    if value is not None:
        item['value'] = value
    return item


def drawing(items, links):
    wires = []
    for i, link in enumerate(links, 1):
        a, b, bend, *rest = link
        wire = dict(id=f'w{i}', a=a, b=b, bend=bend)
        if rest:
            wire['via'] = [dict(x=x, y=y) for x, y in rest[0]]
        wires.append(wire)
    return dict(schema='circuitscope.canvas.v1', items=items, wires=wires)


def get_examples():
    # New dictionaries on each call keep example loading and verification isolated.
    worked = json.loads((Path(__file__).parent / 'sample_drawing.json').read_text(encoding='utf-8'))
    divider = drawing([
        part('V1','V',12,200,340,90,'Vs'),
        part('R1','R',1000,500,220),
        part('R2','R',2000,780,380,90,'Va'),
        part('GND1','GROUND',None,200,600),
    ], [('V1:1','R1:1','vh'),('R1:2','R2:1','hv'),
        ('R2:2','V1:2','hv',[(780,520),(200,520)]),('V1:2','GND1:1','vh')])
    current = drawing([
        part('I1','I',.003,220,340,270,'','Va'),
        part('R1','R',2000,760,340,90,'Va'),
        part('GND1','GROUND',None,220,600),
    ], [('I1:2','R1:1','hv',[(220,160),(760,160)]),
        ('I1:1','R1:2','hv',[(220,520),(760,520)]),('I1:1','GND1:1','vh')])
    supernode = drawing([
        part('V1','V',6,580,160,0,'Va','Vb'),
        part('R1','R',1000,320,380,90,'Va'),
        part('R2','R',2000,840,380,90,'Vb'),
        part('GND1','GROUND',None,320,620),
    ], [('V1:1','R1:1','hv'),('V1:2','R2:1','hv'),
        ('R1:2','R2:2','vh',[(320,540),(840,540)]),('R1:2','GND1:1','vh')])
    bridge = drawing([
        part('V1','V',9,140,380,90,'Vs'),
        part('R1','R',1000,400,220,90),part('R2','R',2000,400,500,90),
        part('R3','R',2000,820,220,90),part('R4','R',1000,820,500,90),
        part('R5','R',1000,610,360),
        part('JA','J',None,400,360,0,'Va'),part('JB','J',None,820,360,0,'Vb'),
        part('GND1','GROUND',None,140,640),
    ], [('V1:1','R1:1','vh',[(140,100),(400,100)]),
        ('R1:1','R3:1','vh',[(400,100),(820,100)]),
        ('R1:2','JA:1','vh'),('JA:1','R2:1','vh'),('JA:1','R5:1','hv'),
        ('R5:2','JB:1','hv'),('R3:2','JB:1','vh'),('JB:1','R4:1','vh'),
        ('R2:2','R4:2','vh',[(400,600),(820,600)]),
        ('R2:2','V1:2','vh',[(400,600),(140,600)]),('V1:2','GND1:1','vh')])
    from opamp_examples import amplifier_examples
    return [
        dict(id='worked', title='Worked example · parallel paths', drawing=worked,
             description='See current divide between R1 and R3, then join through R2.',
             expected_v={'0':0,'Va':7.2,'Vb':12}, expected_i={'V1':-.0072,'R1':.0048,'R2':.0072,'R3':-.0024},
             port=dict(node1='Va',node2='0',load='R2',voltage=12,resistance=2000/3),
             hand=['R1 and R3 connect the same two nodes: their parallel resistance is 2000/3 Ω. With R2 connected, Va is 7.2 V.',
                   'For the equivalent port, remove R2. The open-circuit node rises to 12 V; with V1 deactivated, the port resistance is R1 ∥ R3.'],
             equations=[r'R_1\parallel R_3=\frac{1000(2000)}{1000+2000}=\frac{2000}{3}\ \Omega',r'V_a=12\frac{1000}{1000+2000/3}=7.2\ \mathrm{V}']),
        dict(id='divider', title='Voltage divider · 8 V output', drawing=divider,
             description='A 12 V source and two series resistors show how a divider sets its output voltage.',
             expected_v={'0':0,'Vs':12,'Va':8}, expected_i={'V1':-.004,'R1':.004,'R2':.004},
             port=dict(node1='Va',node2='0',load=None,voltage=8,resistance=2000/3),
             hand=['The same 4 mA flows through both resistors. Their voltage drops are 4 V and 8 V.',
                   'For this reference port, both resistors remain: the open external port is at 8 V and Rth = R1 ∥ R2.'],
             equations=[r'I=\frac{12}{1000+2000}=0.004\ \mathrm{A}',r'V_a=12\frac{2000}{1000+2000}=8\ \mathrm{V}']),
        dict(id='current', title='Current source · 6 V node', drawing=current,
             description='A 3 mA current source drives a 2 kΩ resistor. The source fixes current, and the resistor sets voltage.',
             expected_v={'0':0,'Va':6}, expected_i={'I1':.003,'R1':.003},
             port=dict(node1='Va',node2='0',load=None,voltage=6,resistance=2000),
             hand=['The source injects 3 mA into Va, so KCL requires 3 mA through the resistor.',
                   'Deactivating the current source opens it; the equivalent resistance is 2 kΩ.'],
             equations=[r'\frac{V_a}{2000}-0.003=0',r'V_a=(0.003)(2000)=6\ \mathrm{V}']),
        dict(id='supernode', title='Floating voltage source · negative node voltage', drawing=supernode,
             description='The source sits between two unknown nodes. A supernode equation and the source constraint must be solved together.',
             expected_v={'0':0,'Va':2,'Vb':-4}, expected_i={'V1':-.002,'R1':.002,'R2':-.002},
             port=dict(node1='Va',node2='0',load=None,voltage=2,resistance=2000/3),
             hand=['KCL around both source terminals gives 2Va + Vb = 0. The source imposes Va − Vb = 6.',
                   'Together those equations give Va = 2 V and Vb = −4 V. Negative voltage is relative to ground, not a broken circuit.'],
             equations=[r'\frac{V_a}{1000}+\frac{V_b}{2000}=0',r'V_a-V_b=6',r'V_a=2\ \mathrm{V},\qquad V_b=-4\ \mathrm{V}']),
        dict(id='bridge', title='Resistor bridge · coupled nodes and Thévenin', drawing=bridge,
             description='A loaded bridge needs two coupled node equations. Remove the middle resistor R5 to check its Thévenin port.',
             expected_v={'0':0,'Vs':9,'Va':36/7,'Vb':27/7},
             expected_i={'V1':-45/7000,'R1':27/7000,'R2':18/7000,'R3':18/7000,'R4':27/7000,'R5':9/7000},
             port=dict(node1='Va',node2='Vb',load='R5',voltage=3,resistance=4000/3),
             hand=['With R5 connected, the two KCL equations reduce to 5Va − 2Vb = 18 and −2Va + 5Vb = 9.',
                   'For Thévenin, remove R5: the left divider gives 6 V and the right divider gives 3 V. Vth = 3 V.',
                   'With the 9 V source shorted, the resistance between Va and Vb is (R1 ∥ R2) + (R3 ∥ R4) = 4000/3 Ω.'],
             equations=[r'\frac{V_a-9}{1000}+\frac{V_a}{2000}+\frac{V_a-V_b}{1000}=0',
                        r'\frac{V_b-9}{2000}+\frac{V_b}{1000}+\frac{V_b-V_a}{1000}=0',
                        r'V_a=\frac{36}{7}\ \mathrm{V},\quad V_b=\frac{27}{7}\ \mathrm{V}',
                        r'V_{th}=6-3=3\ \mathrm{V},\quad R_{th}=\frac{4000}{3}\ \Omega']),
    ] + amplifier_examples(part, drawing)
