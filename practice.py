"""Hand-derived practice questions; grading never uses a solver as its key."""
from math import isfinite, isclose
from examples import get_examples
from teaching import circuit_signature
from topology import compile_drawing

UNITS = {'V': {'V': 1, 'mV': .001}, 'A': {'A': 1, 'mA': .001, 'µA': .000001},
         'Ω': {'Ω': 1, 'kΩ': 1000}}


def get_exercises():
    """Fresh drawings and explicit answer keys, independent of engine.py."""
    questions = [
        dict(id='divider_voltage', title='1 · Voltage divider', example='divider',
             prompt='Find Va relative to ground with both resistors connected.', answer=8, unit='V', node='Va',
             hints=['R1 and R2 carry the same current. Start with the total series resistance.',
                    'Va is the drop across R2: Va = 12 × 2000 / (1000 + 2000).'],
             solution='I = 12 / 3000 = 4 mA. Va = I × R2 = 0.004 × 2000 = 8 V.'),
        dict(id='current_voltage', title='2 · A source that fixes current', example='current',
             prompt='Find Va relative to ground. Follow the current-source arrow.', answer=6, unit='V', node='Va',
             hints=['The source injects 3 mA into Va. The resistor is the only path out.',
                    'Use KCL: Va / 2000 − 0.003 = 0.'],
             solution='The resistor carries 3 mA. Va = 0.003 × 2000 = 6 V.'),
        dict(id='supernode_voltage', title='3 · A floating voltage source', example='supernode',
             prompt='Find Vb relative to ground. Keep its sign.', answer=-4, unit='V', node='Vb',
             hints=['Neither source terminal is ground. Use one supernode KCL equation and one source constraint.',
                    'Va/1000 + Vb/2000 = 0 and Va − Vb = 6. Substitute Va = Vb + 6.'],
             solution='2Va + Vb = 0; Va = Vb + 6. Thus 3Vb + 12 = 0, so Vb = −4 V and Va = 2 V.'),
        dict(id='branch_direction', title='4 · Signed branch current', example='worked',
             prompt='Find R3 current in its pin 1 → pin 2 reference direction (Va → Vb). A negative value is allowed.',
             answer=-.0024, unit='A', default_unit='mA', node='Va',
             hints=['First solve Va using the two parallel paths between Vb and Va.',
                    '(Va − 12)/1000 + Va/1000 + (Va − 12)/2000 = 0. Then I_R3 = (Va − 12)/2000.'],
             solution='5Va = 36, so Va = 7.2 V. I_R3 = (7.2 − 12)/2000 = −0.0024 A = −2.4 mA. Actual current flows from Vb toward Va.'),
        dict(id='bridge_thevenin', title='5 · Open-port Thévenin voltage', example='bridge',
             prompt='Find Vth = V(Va) − V(Vb) with R5 removed. Leave R5 in the drawing; remove it only for this calculation.',
             answer=3, unit='V', node='Va',
             hints=['Remove the bridge load R5. The remaining left and right sides are separate voltage dividers.',
                    'Left: 9 × 2000/3000. Right: 9 × 1000/3000. Subtract right from left.'],
             solution='With R5 removed, Va = 6 V and Vb = 3 V. Vth = Va − Vb = 3 V.'),
        dict(id='bridge_resistance', title='6 · Resistance seen at a port', example='bridge',
             prompt='Find Rth between Va and Vb with R5 removed and the independent 9 V source deactivated.',
             answer=4000/3, unit='Ω', default_unit='kΩ', node='Va',
             hints=['Deactivate the ideal voltage source by replacing it with a short. Do not short the port.',
                    'Rth = (R1 ∥ R2) + (R3 ∥ R4). Each parallel pair is 1000 × 2000 / 3000.'],
             solution='Each parallel pair is 2000/3 Ω. Their series sum across the port is 4000/3 Ω ≈ 1.33333 kΩ.'),
        dict(id='inverting_output', title='7 · Negative-feedback amplifier', example='inverting',
             prompt='Find Vout relative to ground with the shown feedback and load connected.', answer=-2, unit='V', node='Vout',
             hints=['The grounded + input and negative feedback hold Vm at 0 V. Both input currents are zero.',
                    'KCL at Vm: (0 − 1)/10000 + (0 − Vout)/20000 = 0.'],
             solution='Vout = −(Rf/Rin)Vin = −(20000/10000) × 1 = −2 V. Feedback enforces equal input voltage without merging the input nodes.'),
        dict(id='open_output', title='8 · Voltage without load current', example='openoutput',
             prompt='Find Vout relative to ground at the unloaded output probe.', answer=12, unit='V', node='Vout',
             hints=['The ideal output probe has infinite resistance and draws zero current.',
                    'At Vout, KCL gives (Vout − 12)/1000 = 0. What voltage drop does zero current create?'],
             solution='I_R1 = 0, so the resistor drop is zero and Vout = 12 V. The output is defined through the source and resistor; it is not floating.'),
        dict(id='comparator_output', title='9 · Open-loop comparator', example='comparator_high',
             prompt='Find Vout for the shown open-loop amplifier. Its configured output levels are 0 V and 5 V.',
             answer=5, unit='V', node='Vout',
             hints=['Compare the actual + and − input voltages. Do not impose input equality in open-loop mode.',
                    'The + input is 3 V and the − input is 2 V. Select the output level for a positive difference.'],
             solution='V+ − V− = 3 − 2 = 1 V > 0, so the ideal comparator selects HIGH at 5 V.'),
    ]
    drawings = {e['id']: e['drawing'] for e in get_examples()}
    for q in questions:
        q['drawing'] = drawings[q['example']]
        q['signature'] = drawing_signature(q['drawing'])
    return questions


def drawing_signature(drawing):
    return circuit_signature(compile_drawing(drawing)[0])


def grade_answer(exercise, text, unit):
    """Convert explicit units and check a signed value within 0.5% tolerance."""
    if unit not in UNITS[exercise['unit']]:
        raise ValueError('Choose a unit for the quantity in this question.')
    try:
        value = float(text.strip()) * UNITS[exercise['unit']][unit]
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Enter a number, such as -2.4 or 1e-3. Choose the unit separately.') from None
    if not isfinite(value):
        raise ValueError('Enter a finite number.')
    expected = exercise['answer']
    correct = isclose(value, expected, rel_tol=.005, abs_tol=1e-9)
    if correct:
        return True, 'Correct — your signed answer and units agree with the hand calculation.'
    if expected and isclose(abs(value), abs(expected), rel_tol=.005, abs_tol=1e-9):
        return False, 'The magnitude matches. Check the reference direction or the order of the voltage subtraction.'
    return False, 'Try again. Check the chosen units and use the next hint to review your equation.'
