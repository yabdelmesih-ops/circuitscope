"""Run the real Streamlit registration and sample solve when installed."""
from pathlib import Path
from copy import deepcopy
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
    def test_loading_an_example_replaces_a_stale_ground_node_selection(self):
        app=AppTest.from_file(str(ROOT/'drawing_app.py')).run()
        next(b for b in app.button if b.label=='Load worked example').click().run()
        next(s for s in app.selectbox if s.label=='First node').set_value('0').run()
        next(s for s in app.selectbox if s.label=='Reference circuit').set_value('Op amp · inverting amplifier (−2 V)').run()
        next(b for b in app.button if b.label=='Load selected example').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertEqual(app.session_state['question_node'],'Vout')
        self.assertEqual(app.session_state['question_reference'],'0')

    def test_course_methods_superposition_and_summing_use_the_active_drawing(self):
        app=AppTest.from_file(str(ROOT/'drawing_app.py')).run()
        next(s for s in app.selectbox if s.label=='Course example').set_value('Superposition · voltage and current sources').run()
        next(b for b in app.button if b.label=='Load course example').click().run()
        next(s for s in app.selectbox if s.label=='Circuit method').set_value('Superposition').run()
        next(b for b in app.button if b.label=='Explain selected method').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertAlmostEqual(app.session_state['method_result']['result']['full'],28/3)
        next(s for s in app.selectbox if s.label=='Course example').set_value('Summing amplifier · inverting').run()
        next(b for b in app.button if b.label=='Load course example').click().run()
        next(s for s in app.selectbox if s.label=='Circuit method').set_value('Summing amplifiers').run()
        next(b for b in app.button if b.label=='Explain selected method').click().run()
        self.assertEqual(app.session_state['method_result']['result'][0]['predicted'],-4)
        self.assertFalse(app.exception,[e.message for e in app.exception])

    def test_source_transformation_loads_editable_equivalent_and_preserves_voltage(self):
        app=AppTest.from_file(str(ROOT/'drawing_app.py')).run()
        next(s for s in app.selectbox if s.label=='Course example').set_value('Voltage divider and source transformation').run()
        next(b for b in app.button if b.label=='Load course example').click().run()
        next(s for s in app.selectbox if s.label=='Circuit method').set_value('Source transformation').run()
        next(b for b in app.button if b.label=='Explain selected method').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        next(b for b in app.button if b.label=='Load transformed circuit').click().run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertIn('8 V',[m.value for m in app.metric])
        self.assertTrue(any(p['type']=='I' for p in app.session_state['canvas_seed']['items']))

    def test_import_review_requires_approval_and_blocks_unsupported_symbols(self):
        app=AppTest.from_file(str(ROOT/'drawing_app.py')).run()
        next(b for b in app.button if b.label=='Try import review demo (no API)').click().run()
        load=next(b for b in app.button if b.label=='Load reviewed circuit')
        self.assertTrue(load.disabled)
        next(c for c in app.checkbox if c.label.startswith('I checked the values')).check().run()
        next(b for b in app.button if b.label=='Load reviewed circuit').click().run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertIn('8 V',[m.value for m in app.metric])
        payload=app.session_state['image_candidate']['payload']
        payload['unsupported']=['capacitor C1']
        app.run()
        self.assertTrue(any('Unsupported elements' in e.value for e in app.error))
        self.assertFalse(any(b.label=='Load reviewed circuit' for b in app.button))

    def test_practice_hints_checking_and_reveal_are_explicit(self):
        app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
        next(b for b in app.button if b.label == 'Start practice question').click().run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertFalse(app.metric)
        self.assertFalse(app.session_state['practice_active']['revealed'])
        next(t for t in app.text_input if t.label == 'Your predicted answer').set_value('7')
        next(b for b in app.button if b.label == 'Check my answer').click().run()
        self.assertFalse(app.session_state['practice_active']['revealed'])
        self.assertTrue(any('Try again' in m.value for m in app.info))
        next(b for b in app.button if b.label == 'Show next hint').click().run()
        self.assertEqual(app.session_state['practice_active']['hints'], 1)
        next(s for s in app.selectbox if s.label == 'Answer unit').set_value('mV')
        next(t for t in app.text_input if t.label == 'Your predicted answer').set_value('8000')
        next(b for b in app.button if b.label == 'Check my answer').click().run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertTrue(app.session_state['practice_active']['revealed'])
        record = app.session_state['practice_progress']['divider_voltage']
        self.assertTrue(record['correct'])
        self.assertEqual(record['attempts'], 2)
        self.assertFalse(app.metric, 'practice must not silently run the regular solver')

    def test_practice_rejects_changed_circuits_and_keeps_progress_across_questions(self):
        app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
        next(b for b in app.button if b.label == 'Start practice question').click().run()
        next(b for b in app.button if b.label == 'Reveal worked answer').click().run()
        self.assertFalse(app.session_state['practice_progress']['divider_voltage']['correct'])
        key = f"circuit_canvas_{app.session_state['canvas_revision']}"
        drawing = deepcopy(app.session_state[key]['drawing'])
        drawing['items'][0]['x'] += 40
        app.session_state[key] = {'drawing': drawing, 'node_request': None}
        app.run()
        self.assertTrue(any(b.label == 'Check my answer' for b in app.button))
        drawing['items'][0]['value'] = 24
        app.session_state[key] = {'drawing': drawing, 'node_request': None}
        app.run()
        self.assertTrue(any('circuit changed' in w.value for w in app.warning))
        self.assertFalse(any(b.label == 'Check my answer' for b in app.button))
        next(s for s in app.selectbox if s.label == 'Practice question').set_value('4 · Signed branch current').run()
        next(b for b in app.button if b.label == 'Start practice question').click().run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertEqual(app.session_state['practice_active']['id'], 'branch_direction')
        self.assertEqual(app.session_state['question_kind'], 'Branch current')
        self.assertEqual(app.session_state['question_branch'], 'R3')
        self.assertIn('divider_voltage', app.session_state['practice_progress'])
        next(b for b in app.button if b.label == 'Load worked example').click().run()
        self.assertNotIn('practice_active', app.session_state)

    def test_practice_selection_does_not_change_an_active_key_until_start(self):
        app = AppTest.from_file(str(ROOT / 'drawing_app.py')).run()
        next(b for b in app.button if b.label == 'Start practice question').click().run()
        next(t for t in app.text_input if t.label == 'Your predicted answer').set_value('nan')
        next(b for b in app.button if b.label == 'Check my answer').click().run()
        self.assertEqual(app.session_state['practice_progress']['divider_voltage']['attempts'], 0)
        next(s for s in app.selectbox if s.label == 'Practice question').set_value('6 · Resistance seen at a port').run()
        self.assertEqual(app.session_state['practice_active']['id'], 'divider_voltage')
        next(b for b in app.button if b.label == 'Start practice question').click().run()
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertEqual(app.session_state['practice_active']['id'], 'bridge_resistance')
        self.assertEqual(app.session_state['practice_answer'], '')
        self.assertEqual(app.session_state['practice_unit'], 'kΩ')
        self.assertEqual(app.session_state['question_kind'], 'Thevenin')
        self.assertEqual(app.session_state['question_reference'], 'Vb')
        self.assertEqual(app.session_state['removed_load'], 'R5')
        next(t for t in app.text_input if t.label == 'Your predicted answer').set_value('1.333')
        next(b for b in app.button if b.label == 'Check my answer').click().run()
        self.assertTrue(app.session_state['practice_progress']['bridge_resistance']['correct'])

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
            self.assertEqual(len(rows), 11)
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

    def test_open_loop_example_teaches_high_decision_and_shows_hand_reference(self):
        app = self.load_reference('comparator_high')
        next(c for c in app.checkbox if c.label=='Show this example’s hand-calculated reference').check().run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertFalse(app.error,[e.value for e in app.error])
        self.assertIn('5 V',[m.value for m in app.metric])
        active=app.session_state['analysis_result']
        self.assertEqual(active['amplifiers'],[dict(name='U1',state='HIGH',voltage=5)])
        self.assertEqual(active['lesson']['voltages']['Vin'],3)
        self.assertEqual(active['lesson']['voltages']['Vref'],2)
        app.radio[0].set_value('3 · KCL').run()
        self.assertTrue(any('Open-loop HIGH' in e['label'] for e in app.session_state['analysis_result']['lesson']['equations']))
        next(s for s in app.selectbox if s.label=='Find').set_value('Thevenin').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.metric)
        self.assertTrue(any('require a linear circuit' in e.value for e in app.error))
        self.assertFalse(app.exception)

    def test_comparator_open_output_has_zero_output_current_and_retains_low_voltage(self):
        app=self.load_reference('comparator_low')
        next(s for s in app.selectbox if s.label=='Find').set_value('Open-circuit voltage').run()
        next(s for s in app.selectbox if s.label=='Load to remove').set_value('RL').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertFalse(app.error,[e.value for e in app.error])
        self.assertIn('-12 V',[m.value for m in app.metric])
        active=app.session_state['analysis_result']
        self.assertEqual(active['amplifiers'][0]['state'],'LOW')
        self.assertEqual(next(p for p in active['lesson']['branches'] if p['name']=='U1')['current'],0)
        self.assertEqual(active['measurement']['removedLoad'],'RL')

    def test_comparator_source_edit_clears_high_and_equal_input_has_no_stale_answer(self):
        app=self.load_reference('comparator_high')
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        key=f"circuit_canvas_{app.session_state['canvas_revision']}"
        from examples import get_examples
        model=next(e['drawing'] for e in get_examples() if e['id']=='comparator_high')
        model['items'][0]['value']=1
        model['revision']=1
        app.session_state[key]={'drawing':model}
        app.run()
        self.assertFalse(app.metric)
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertIn('0 V',[m.value for m in app.metric])
        self.assertEqual(app.session_state['analysis_result']['amplifiers'][0]['state'],'LOW')
        model['items'][0]['value']=2
        model['revision']=2
        app.session_state[key]={'drawing':model}
        app.run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        self.assertFalse(app.metric)
        self.assertNotIn('analysis_result',app.session_state)
        self.assertTrue(any('undefined at the switching threshold' in e.value for e in app.error))
        self.assertFalse(app.exception)

    def test_spice_export_matches_selected_unloaded_configuration(self):
        app=self.load_reference('inverting')
        next(s for s in app.selectbox if s.label=='Find').set_value('Open-circuit voltage').run()
        next(s for s in app.selectbox if s.label=='Load to remove').set_value('RL').run()
        next(b for b in app.button if b.label=='Solve drawing').click().run()
        next(s for s in app.selectbox if s.label=='Circuit configuration').set_value('Current solved circuit').run()
        next(b for b in app.button if b.label=='Prepare SPICE export').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertFalse(app.error,[e.value for e in app.error])
        result=app.session_state['spice_export']['payload']
        self.assertEqual(result['removed_load'],'RL')
        self.assertNotIn('RL',result['element_map'])
        self.assertIn('Rf',result['element_map'])
        next(s for s in app.selectbox if s.label=='Circuit configuration').set_value('Full drawing').run()
        next(b for b in app.button if b.label=='Prepare SPICE export').click().run()
        self.assertIn('RL',app.session_state['spice_export']['payload']['element_map'])

    def test_comparator_ngspice_export_and_undefined_threshold_fail_cleanly(self):
        app=self.load_reference('comparator_high')
        next(s for s in app.selectbox if s.label=='SPICE format').set_value('ngspice').run()
        next(b for b in app.button if b.label=='Prepare SPICE export').click().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertIn('>0 ? 5 : 0',app.session_state['spice_export']['payload']['netlist'])
        from examples import get_examples
        model=next(e['drawing'] for e in get_examples() if e['id']=='comparator_high')
        model['items'][0]['value']=2
        key=f"circuit_canvas_{app.session_state['canvas_revision']}"
        app.session_state[key]={'drawing':model}
        app.run()
        next(b for b in app.button if b.label=='Prepare SPICE export').click().run()
        self.assertNotIn('spice_export',app.session_state)
        self.assertTrue(any('undefined at the switching threshold' in e.value for e in app.error))
        self.assertFalse(app.exception)

    def test_independent_spice_report_is_shown_without_running_a_simulator_in_the_app(self):
        from verification import load_spice_report
        report,reason=load_spice_report()
        self.assertIsNotNone(report,reason)
        app=AppTest.from_file(str(ROOT/'drawing_app.py')).run()
        next(c for c in app.checkbox if c.label=='Show independent SPICE verification').check().run()
        self.assertFalse(app.exception,[e.message for e in app.exception])
        self.assertTrue(any('29/29 external DC configurations' in s.value for s in app.success))
