"""Check independent practice keys, unit conversion, signs and drawing guards."""
from copy import deepcopy
import unittest
from circuit_model import branch_current
from engine import solve_circuit, thevenin
from practice import get_exercises, grade_answer, drawing_signature
from topology import compile_drawing


class PracticeTests(unittest.TestCase):
    def test_all_hand_keys_match_the_intended_circuit_and_quantity(self):
        questions = get_exercises()
        self.assertEqual(len({q['id'] for q in questions}), 9)
        for q in questions:
            with self.subTest(question=q['id']):
                parts, _ = compile_drawing(q['drawing'])
                if q['id'].startswith('bridge_'):
                    voltage, resistance = thevenin(parts, 'Va', 'Vb', 'R5')
                    value = resistance if q['unit'] == 'Ω' else voltage
                else:
                    _, index, sources, result = solve_circuit(parts)
                    if q['unit'] == 'A':
                        part = next(p for p in parts if p['name'] == 'R3')
                        voltages = {'0': 0, **{name: float(result[i]) for name, i in index.items()}}
                        value = branch_current(part, voltages, index, sources, result)
                    else:
                        value = result[index[q['node']]]
                self.assertAlmostEqual(value, q['answer'], places=8)

    def test_signed_current_and_explicit_units(self):
        q = next(q for q in get_exercises() if q['unit'] == 'A')
        self.assertTrue(grade_answer(q, '-2.4', 'mA')[0])
        self.assertTrue(grade_answer(q, '-2.4e-3', 'A')[0])
        self.assertTrue(grade_answer(q, '-2400', 'µA')[0])
        correct, message = grade_answer(q, '2.4', 'mA')
        self.assertFalse(correct)
        self.assertIn('magnitude matches', message)
        self.assertFalse(grade_answer(q, '-2.4', 'A')[0])

    def test_voltage_and_resistance_scaling(self):
        questions = {q['id']: q for q in get_exercises()}
        self.assertTrue(grade_answer(questions['divider_voltage'], '8000', 'mV')[0])
        self.assertTrue(grade_answer(questions['bridge_resistance'], '1.333', 'kΩ')[0])
        self.assertFalse(grade_answer(questions['bridge_resistance'], '1.333', 'Ω')[0])

    def test_invalid_and_nonfinite_input_is_not_a_checked_answer(self):
        q = get_exercises()[0]
        for text in ['', 'abc', '8 V', '1/2', 'nan', 'inf', '-Infinity', '1e9999']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                grade_answer(q, text, 'V')
        with self.assertRaises(ValueError):
            grade_answer(q, '8', 'A')

    def test_tolerance_accepts_rounding_and_rejects_wrong_values(self):
        q = get_exercises()[0]
        self.assertTrue(grade_answer(q, '7.97', 'V')[0])
        self.assertFalse(grade_answer(q, '7.9', 'V')[0])
        self.assertFalse(grade_answer(q, '0', 'V')[0])

    def test_moving_parts_preserves_the_key_but_electrical_edits_do_not(self):
        q = get_exercises()[0]
        moved = deepcopy(q['drawing'])
        moved['items'][0]['x'] += 80
        moved['items'][0]['rotation'] = 180
        self.assertEqual(drawing_signature(moved), q['signature'])
        moved['items'][0]['value'] += 1
        self.assertNotEqual(drawing_signature(moved), q['signature'])
        disconnected = deepcopy(q['drawing'])
        disconnected['wires'].pop()
        self.assertNotEqual(drawing_signature(disconnected), q['signature'])

    def test_returned_drawings_do_not_mutate_future_exercises(self):
        q = get_exercises()[0]
        q['drawing']['items'][0]['value'] = 100
        self.assertEqual(get_exercises()[0]['drawing']['items'][0]['value'], 12)
