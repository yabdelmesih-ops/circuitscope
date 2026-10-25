import json
from pathlib import Path
import unittest
from topology import compile_drawing, validate_for_solving
from reference_engine import get_voltages, thevenin

ROOT = Path(__file__).resolve().parents[1]

class DrawingTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT / 'sample_drawing.json').read_text())

    def test_worked_example_voltages(self):
        parts, _ = compile_drawing(self.model)
        validate_for_solving(parts)
        self.assertAlmostEqual(get_voltages(parts)['Va'], 7.2)
        self.assertAlmostEqual(get_voltages(parts)['Vb'], 12)

    def test_thevenin_and_norton(self):
        parts, _ = compile_drawing(self.model)
        v, r = thevenin(parts, 'Va', '0', 'R2')
        self.assertAlmostEqual(v, 12)
        self.assertAlmostEqual(r, 2000 / 3)
        self.assertAlmostEqual(v / r, .018)

    def test_pin_polarities_are_preserved(self):
        parts, _ = compile_drawing(self.model)
        r3 = next(p for p in parts if p['name'] == 'R3')
        self.assertEqual((r3['node1'], r3['node2']), ('Va', 'Vb'))

    def test_moving_and_rotating_changes_picture_not_connections(self):
        before, _ = compile_drawing(self.model)
        self.model['items'][1].update(x=600, y=200, rotation=270)
        self.assertEqual(before, compile_drawing(self.model)[0])

    def test_wires_not_overlapping_coordinates_define_connection(self):
        # Moving an unwired item onto another pin must NOT silently connect it.
        self.model['items'].append({'id':'R4','type':'R','x':480,'y':180,'rotation':0,'value':1000})
        _, pins = compile_drawing(self.model)
        self.assertNotEqual(pins['R4:1'], pins['R1:1'])

    def test_junction_dot_groups_arbitrary_number_of_wires(self):
        self.model['items'].append({'id':'J1','type':'J','x':900,'y':400,'rotation':0})
        self.model['wires'] = [w for w in self.model['wires'] if w['id'] not in ('w2','w5')]
        for i, pin in enumerate(('R1:2','R2:1','R3:1')):
            self.model['wires'].append({'id':'wj'+str(i),'a':pin,'b':'J1:1'})
        _, pins = compile_drawing(self.model)
        self.assertEqual(pins['R1:2'], pins['R2:1'])
        self.assertEqual(pins['R3:1'], 'Va')

    def test_ground_symbols_share_reference(self):
        self.model['items'].append({'id':'GND2','type':'GROUND','x':1000,'y':600,'rotation':0})
        _, pins = compile_drawing(self.model)
        self.assertEqual(pins['GND1:1'], '0')
        self.assertEqual(pins['GND2:1'], '0')

    def test_missing_ground_rejects(self):
        self.model['items'] = [i for i in self.model['items'] if i['type'] != 'GROUND']
        self.model['wires'] = [w for w in self.model['wires'] if w['b'] != 'GND1:1']
        parts, _ = compile_drawing(self.model)
        with self.assertRaisesRegex(ValueError, 'ground'):
            validate_for_solving(parts)

    def test_loose_resistor_terminal_rejects(self):
        self.model['items'].append({'id':'R4','type':'R','x':1000,'y':600,'rotation':0,'value':1000})
        parts, _ = compile_drawing(self.model)
        with self.assertRaisesRegex(ValueError, 'Floating'):
            validate_for_solving(parts)

    def test_current_source_does_not_reference_floating_node(self):
        with self.assertRaisesRegex(ValueError, 'Floating'):
            validate_for_solving([{'name':'I1','type':'I','node1':'0','node2':'A','value':.001}])

    def test_conflicting_labels_reject(self):
        self.model['items'][1]['label1'] = 'other'
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            compile_drawing(self.model)

    def test_user_label_renames_node(self):
        self.model['items'][2]['label1'] = 'OUT'
        parts, _ = compile_drawing(self.model)
        self.assertAlmostEqual(get_voltages(parts)['OUT'], 7.2)

    def test_bad_wire_reference_rejects(self):
        self.model['wires'][0]['a'] = 'missing:1'
        with self.assertRaisesRegex(ValueError, 'missing terminal'):
            compile_drawing(self.model)

    def test_duplicate_component_ids_reject(self):
        self.model['items'][1]['id'] = 'v1'
        with self.assertRaisesRegex(ValueError, 'unique'):
            compile_drawing(self.model)

    def test_bad_values_reject(self):
        for value in (0, -1, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.model['items'][1]['value'] = value
                with self.assertRaises(ValueError):
                    compile_drawing(self.model)

    def test_repeated_compilation_does_not_mutate_drawing(self):
        before = json.dumps(self.model)
        compile_drawing(self.model)
        self.assertEqual(before, json.dumps(self.model))

    def test_routing_corners_do_not_create_electrical_connections(self):
        before, _ = compile_drawing(self.model)
        self.model['wires'][0]['via'] = [{'x':300,'y':260},{'x':300,'y':180}]
        self.model['items'].append({'id':'J1','type':'J','x':300,'y':260,'rotation':0})
        parts, pins = compile_drawing(self.model)
        self.assertEqual(parts, before)
        self.assertNotEqual(pins['J1:1'], pins['V1:1'])

    def test_routing_points_are_validated(self):
        for via in ({}, [{'x':-1,'y':100}], [{'x':100,'y':float('nan')}], [{'x':100}], [{}]*201):
            with self.subTest(via=via):
                self.model['wires'][0]['via'] = via
                with self.assertRaisesRegex(ValueError, 'routing'):
                    compile_drawing(self.model)

    def test_junction_at_canvas_edge_is_allowed(self):
        self.model['items'].append({'id':'J1','type':'J','x':0,'y':20,'rotation':0})
        _, pins = compile_drawing(self.model)
        self.assertIn('J1:1', pins)

if __name__ == '__main__':
    unittest.main()
