import copy
import json
from pathlib import Path
import unittest

from reference_engine import solve_circuit
from topology import compile_drawing
from teaching import build_lesson, circuit_signature, kcl_equation, math_number

ROOT = Path(__file__).resolve().parents[1]


def lesson(parts, node='Va', reference='0'):
    _, index, sources, values = solve_circuit(parts)
    return build_lesson(parts, node, reference, index, sources, values)


class TeachingTests(unittest.TestCase):
    def test_scientific_notation_is_valid_readable_math(self):
        self.assertEqual(math_number(1e-9), r'1\times 10^{-9}')
        self.assertEqual(math_number(1000), '1000')

    def setUp(self):
        self.drawing = json.loads((ROOT / 'sample_drawing.json').read_text())
        self.parts, _ = compile_drawing(self.drawing)

    def test_example_currents_and_conservation(self):
        result = lesson(self.parts)
        branches = {b['name']: b for b in result['branches']}
        self.assertAlmostEqual(result['answer'], 7.2)
        self.assertAlmostEqual(branches['R1']['outward'], -.0048)
        self.assertAlmostEqual(branches['R2']['outward'], .0072)
        self.assertAlmostEqual(branches['R3']['outward'], -.0024)
        self.assertEqual(branches['R3']['direction'], -1)
        self.assertAlmostEqual(result['incoming'], .0072)
        self.assertAlmostEqual(result['outgoing'], .0072)
        self.assertTrue(result['balanced'])
        self.assertEqual([b['number'] for b in result['incident']], [1, 2, 3])
        self.assertIn('from Vb (12 V) to Va (7.2 V)', branches['R3']['why'])

    def test_algebra_only_uses_given_source_voltages(self):
        result = lesson(self.parts)
        self.assertEqual(result['givens'], {'Vb': 12.0})
        self.assertIn('0.0025', result['algebra'][0]['latex'])
        self.assertIn('0.018', result['algebra'][0]['latex'])
        self.assertNotIn('7.2', result['kcl'])
        self.assertIn('2000', result['kcl'])

    def test_non_ground_reference_keeps_physical_voltages_and_answer_separate(self):
        result = lesson(self.parts, reference='Vb')
        self.assertAlmostEqual(result['node_voltage'], 7.2)
        self.assertAlmostEqual(result['reference_voltage'], 12)
        self.assertAlmostEqual(result['answer'], -4.8)
        self.assertAlmostEqual(result['incoming'], .0072)

    def test_source_node_and_ground_have_valid_balance(self):
        source = lesson(self.parts, node='Vb')
        self.assertAlmostEqual(source['answer'], 12)
        self.assertTrue(source['balanced'])
        self.assertIn('already set', source['algebra'][0]['text'])
        self.assertTrue(lesson(self.parts, node='0')['balanced'])
        self.assertIn('supplies energy', next(b for b in source['branches'] if b['name'] == 'V1')['why'])

    def test_unknown_neighbors_and_floating_voltage_source_stay_symbolic(self):
        parts = [
            {'name':'V1','type':'V','node1':'A','node2':'B','value':5},
            {'name':'R1','type':'R','node1':'A','node2':'0','value':1000},
            {'name':'R2','type':'R','node1':'B','node2':'0','value':2000},
        ]
        result = lesson(parts, 'A')
        self.assertEqual(result['givens'], {})
        self.assertIn('I_{', result['kcl'])
        self.assertIn('solved together', result['algebra'][0]['text'])
        self.assertEqual(len(result['equations']), 3)
        self.assertTrue(result['balanced'])

    def test_negative_current_source_and_zero_resistor_current(self):
        parts = [
            {'name':'V1','type':'V','node1':'A','node2':'0','value':5},
            {'name':'V2','type':'V','node1':'B','node2':'0','value':5},
            {'name':'R1','type':'R','node1':'A','node2':'B','value':1000},
            {'name':'I1','type':'I','node1':'A','node2':'0','value':-.002},
        ]
        result = lesson(parts, 'A')
        branches = {b['name']: b for b in result['branches']}
        self.assertEqual(branches['R1']['direction'], 0)
        self.assertIn('Both ends', branches['R1']['why'])
        self.assertIn('from 0 to A', branches['I1']['why'])
        self.assertIn('- 0.002', kcl_equation(parts, 'A'))
        self.assertTrue(result['balanced'])

    def test_layout_does_not_change_signature_but_electrical_edits_do(self):
        before = circuit_signature(self.parts)
        moved = copy.deepcopy(self.drawing)
        moved['items'][1]['x'] += 40
        self.assertEqual(before, circuit_signature(compile_drawing(moved)[0]))
        moved['items'][1]['value'] *= 2
        self.assertNotEqual(before, circuit_signature(compile_drawing(moved)[0]))

    def test_self_loop_source_does_not_invent_net_node_current(self):
        parts = self.parts + [{'name':'Iloop','type':'I','node1':'Va','node2':'Va','value':1}]
        result = lesson(parts)
        self.assertEqual(next(b for b in result['branches'] if b['name']=='Iloop')['outward'], 0)
        self.assertTrue(result['balanced'])
