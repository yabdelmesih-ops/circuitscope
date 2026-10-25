"""Run the real Streamlit registration and sample solve when installed."""
from pathlib import Path
import unittest
from unittest.mock import patch

import reference_engine
import json

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(AppTest is None, 'Install requirements.txt to check real Streamlit')
class StreamlitIntegrationTests(unittest.TestCase):
    def test_load_bridge_and_run_reference_checks_without_changing_the_drawing(self):
        with patch.dict('sys.modules', {'engine': reference_engine}):
            app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
            next(s for s in app.selectbox if s.label == 'Reference circuit').set_value('Resistor bridge · coupled nodes and Thévenin').run()
            next(b for b in app.button if b.label == 'Load selected example').click().run()
            next(b for b in app.button if b.label == 'Solve drawing').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertIn('5.14286 V', [m.value for m in app.metric])
            key = f"circuit_canvas_{app.session_state['canvas_revision']}"
            before = json.dumps(app.session_state[key]['drawing'], sort_keys=True)
            next(b for b in app.button if b.label == 'Run solver checks').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            rows = app.session_state['solver_check_results']
            self.assertEqual(len(rows), 9)
            self.assertTrue(all(row['Result']=='PASS' for row in rows))
            self.assertEqual(before, json.dumps(app.session_state[key]['drawing'], sort_keys=True))

    def test_canvas_node_click_solves_once_and_step_changes_keep_the_lesson(self):
        with patch.dict('sys.modules', {'engine': reference_engine}), patch.object(reference_engine, 'solve_circuit', wraps=reference_engine.solve_circuit) as solve:
            app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
            next(b for b in app.button if b.label == 'Load worked example').click().run()
            key = f"circuit_canvas_{app.session_state['canvas_revision']}"
            drawing = json.loads((ROOT / 'sample_drawing.json').read_text())
            app.session_state[key] = {'drawing': drawing, 'node_request': {'pin':'R3:2','revision':0,'sequence':1}}
            app.run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(app.session_state['question_node'], 'Vb')
            self.assertEqual(app.session_state['analysis_result']['lesson']['node'], 'Vb')
            self.assertIn('12 V', [m.value for m in app.metric])
            self.assertEqual(solve.call_count, 1)
            app.radio[0].set_value('3 · KCL').run()
            self.assertEqual(solve.call_count, 1)
            self.assertIn('12 V', [m.value for m in app.metric])
            app.session_state[key] = {'drawing': drawing, 'node_request': {'pin':'GND1:1','revision':0,'sequence':2}}
            app.run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(app.session_state['question_node'], '0')
            self.assertIn('0 V', [m.value for m in app.metric])

    def test_stale_node_click_is_rejected_and_incomplete_circuit_reports_ground(self):
        with patch.dict('sys.modules', {'engine': reference_engine}):
            app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
            next(b for b in app.button if b.label == 'Load worked example').click().run()
            key = f"circuit_canvas_{app.session_state['canvas_revision']}"
            drawing = json.loads((ROOT / 'sample_drawing.json').read_text())
            app.session_state[key] = {'drawing': drawing, 'node_request': {'pin':'R1:2','revision':99,'sequence':1}}
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.metric)
            self.assertTrue(any('drawing changed' in m.value.lower() for m in app.info))
            drawing['items'] = [p for p in drawing['items'] if p['type'] != 'GROUND']
            drawing['wires'] = [w for w in drawing['wires'] if 'GND1' not in w['a'] and 'GND1' not in w['b']]
            app.session_state[key] = {'drawing': drawing, 'node_request': {'pin':'R1:2','revision':0,'sequence':2}}
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any('ground' in m.value.lower() for m in app.error))
            self.assertFalse(app.metric)

    def test_empty_start_sample_solve_and_clear(self):
        # Use the lesson's engine interface, without requiring a user's engine.py.
        with patch.dict('sys.modules', {'engine': reference_engine}):
            app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(app.session_state['canvas_seed']['items'], [])
            self.assertFalse(any(b.label == 'Solve drawing' for b in app.button))
            next(b for b in app.button if b.label == 'Load worked example').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            next(b for b in app.button if b.label == 'Solve drawing').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertIn('7.2 V', [metric.value for metric in app.metric])
            previous_revision = app.session_state['canvas_revision']
            next(b for b in app.button if b.label == 'Clear screen / New circuit').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(app.session_state['canvas_seed']['items'], [])
            self.assertEqual(app.session_state['canvas_seed']['wires'], [])
            self.assertGreater(app.session_state['canvas_revision'], previous_revision)
            self.assertEqual(app.session_state[f'circuit_canvas_{previous_revision + 1}']['drawing']['items'], [])
            self.assertFalse(app.metric)
            app.run()
            self.assertEqual(app.session_state['canvas_seed']['items'], [])

    def test_visual_lesson_steps_persist_and_electrical_edit_hides_old_answer(self):
        with patch.dict('sys.modules', {'engine': reference_engine}):
            app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
            next(b for b in app.button if b.label == 'Load worked example').click().run()
            next(b for b in app.button if b.label == 'Solve drawing').click().run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            result = app.session_state['analysis_result']
            self.assertAlmostEqual(result['lesson']['answer'], 7.2)
            app.radio[0].set_value('3 · KCL').run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertTrue(any('2000' in item.value for item in app.latex))
            self.assertIn('7.2 V', [metric.value for metric in app.metric])
            app.radio[0].set_value('4 · Check').run()
            self.assertTrue(app.success)
            drawing = json.loads((ROOT / 'sample_drawing.json').read_text())
            drawing['items'][1]['value'] = 2000
            key = f"circuit_canvas_{app.session_state['canvas_revision']}"
            app.session_state[key] = {'drawing': drawing}
            app.run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertFalse(app.metric)
            self.assertFalse(app.radio)

    def load_reference(self, name):
        from examples import get_examples
        title = next(e['title'] for e in get_examples() if e['id']==name)
        app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
        next(s for s in app.selectbox if s.label=='Reference circuit').set_value(title).run()
        next(b for b in app.button if b.label=='Load selected example').click().run()
        return app

    def test_open_output_probe_and_external_load_removal(self):
        app = self.load_reference('inverting')
        next(s for s in app.selectbox if s.label=='Find').set_value('Open-circuit voltage').run()
        next(s for s in app.selectbox if s.label=='Load to remove').set_value('RL').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertFalse(app.error,[e.value for e in app.error])
        self.assertIn('-2 V',[m.value for m in app.metric])
        active = app.session_state['analysis_result']
        self.assertEqual(active['measurement']['removedLoad'],'RL')
        self.assertEqual(active['measurement']['portId'],'OUT1')
        self.assertNotIn('RL',[p['name'] for p in active['lesson']['branches']])
        amp = next(p for p in active['lesson']['branches'] if p['name']=='U1')
        self.assertAlmostEqual(amp['current'],.0001)
        app.radio[0].set_value('3 · KCL').run()
        self.assertIn('-2 V',[m.value for m in app.metric])
        next(s for s in app.selectbox if s.label=='Load to remove').set_value('Rf').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.metric)
        self.assertTrue(any('negative feedback' in e.value for e in app.error))

    def test_zero_resistance_ideal_output_has_no_finite_norton_current(self):
        app = self.load_reference('follower')
        next(s for s in app.selectbox if s.label=='Find').set_value('Norton').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any('no finite Norton current' in e.value for e in app.error))
        self.assertFalse(app.metric)

    def test_unloaded_output_probe_can_read_voltage_with_no_teaching_overlay(self):
        app = self.load_reference('openoutput')
        next(s for s in app.selectbox if s.label=='Find').set_value('Open-circuit voltage').run()
        next(c for c in app.checkbox if c.label=='Teach me how this node works').uncheck().run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertFalse(app.error,[e.value for e in app.error])
        self.assertIn('12 V',[m.value for m in app.metric])
        self.assertIsNone(app.session_state['analysis_result']['lesson'])
        self.assertEqual(app.session_state['analysis_result']['measurement']['voltage'],12)
