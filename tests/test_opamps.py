"""Electrical behavior, invalid models and non-loading output probes."""
import copy
import unittest
from engine import solve_circuit, get_voltages, thevenin, open_circuit_voltage
from circuit_model import branch_current, without_load
from examples import get_examples
from topology import compile_drawing, validate_for_solving, output_ports
from teaching import build_lesson, kcl_equation


def case(name):
    return next(e for e in get_examples() if e['id'] == name)


def parts(name):
    return compile_drawing(case(name)['drawing'])[0]


class OpAmpTests(unittest.TestCase):
    def test_inverting_gain_and_loaded_output_current(self):
        c = parts('inverting')
        _, index, sources, solution = solve_circuit(c)
        v = get_voltages(c)
        self.assertAlmostEqual(v['Vout'], -2)
        self.assertAlmostEqual(v['Vm'], 0)
        u = next(p for p in c if p['type'] == 'OPAMP')
        self.assertAlmostEqual(branch_current(u, v, index, sources, solution), .0003)
        self.assertNotEqual(u['node1'], u['node2'])

    def test_noninverting_gain_and_input_source_current(self):
        c = parts('noninverting')
        _, index, sources, solution = solve_circuit(c)
        v = get_voltages(c)
        self.assertAlmostEqual(v['Vout'], 3)
        self.assertAlmostEqual(v['Vm'], 1)
        source = next(p for p in c if p['name'] == 'V1')
        self.assertAlmostEqual(branch_current(source, v, index, sources, solution), 0)

    def test_voltage_follower_drives_a_load_without_loading_input(self):
        c = parts('follower') + [dict(name='RL', type='R',node1='Vout',node2='0',value=1000)]
        _, i, sources, s = solve_circuit(c)
        v = get_voltages(c)
        self.assertAlmostEqual(v['Vout'], 2)
        u = next(p for p in c if p['name']=='U1')
        self.assertAlmostEqual(branch_current(u,v,i,sources,s), -.002)
        self.assertAlmostEqual(branch_current(c[0],v,i,sources,s), 0)

    def test_summing_amplifier_combines_independent_inputs(self):
        c = without_load(parts('inverting'), 'RL')
        next(p for p in c if p['name']=='Rf')['value'] = 10000
        c += [dict(name='V2',type='V',node1='Vin2',node2='0',value=2),
              dict(name='R2',type='R',node1='Vin2',node2='Vm',value=10000)]
        self.assertAlmostEqual(get_voltages(c)['Vout'], -3)

    def test_open_output_removes_external_load_but_keeps_feedback_current(self):
        c = parts('inverting')
        original = copy.deepcopy(c)
        self.assertAlmostEqual(open_circuit_voltage(c,'Vout','0','RL'), -2)
        working = without_load(c,'RL')
        _, index, sources, s = solve_circuit(working)
        u = next(p for p in working if p['name']=='U1')
        self.assertAlmostEqual(branch_current(u,get_voltages(working),index,sources,s), .0001)
        self.assertEqual(c,original)

    def test_thevenin_keeps_amplifier_active_and_zero_output_resistance_is_valid(self):
        self.assertEqual(thevenin(parts('inverting'),'Vout','0','RL'), (-2,0))
        self.assertEqual(thevenin(parts('follower'),'Vout'), (2,0))

    def test_resistance_test_does_not_apply_physical_rails_to_test_operating_point(self):
        c = parts('follower')
        u = next(p for p in c if p['type']=='OPAMP')
        u.update(v_min=1, v_max=3)
        self.assertEqual(thevenin(c,'Vout'), (2,0))

    def test_saturation_reports_failure_instead_of_fake_linear_or_clamped_answer(self):
        c = parts('inverting')
        c[0]['value'] = 10  # Gain −2 requires −20 V, beyond default −15 V.
        with self.assertRaisesRegex(ValueError,'saturate'):
            get_voltages(c)

    def test_positive_feedback_and_missing_feedback_rejected(self):
        c = parts('follower')
        u = next(p for p in c if p['type']=='OPAMP')
        u['node1'],u['node2'] = u['node2'],u['node1']
        with self.assertRaisesRegex(ValueError,'negative feedback'):
            solve_circuit(c)
        c = parts('inverting')
        c = [p for p in c if p['name']!='Rf']
        with self.assertRaisesRegex(ValueError,'negative feedback'):
            solve_circuit(c)

    def test_removing_feedback_is_not_an_open_load_measurement(self):
        with self.assertRaisesRegex(ValueError,'negative feedback'):
            open_circuit_voltage(parts('inverting'),'Vout','0','Rf')

    def test_tied_inputs_and_invalid_limits_rejected(self):
        c = parts('inverting')
        u = next(p for p in c if p['type']=='OPAMP')
        u['node2']=u['node1']
        with self.assertRaisesRegex(ValueError,'wired together'):
            solve_circuit(c)
        c = parts('follower')
        next(p for p in c if p['type']=='OPAMP').update(v_min=5,v_max=-5)
        with self.assertRaisesRegex(ValueError,'limits'):
            solve_circuit(c)

    def test_opamp_lessons_do_not_invent_input_current_or_connect_input_nodes(self):
        c = parts('inverting')
        _, i, sources, s = solve_circuit(c)
        lesson = build_lesson(c,'Vm','0',i,sources,s)
        self.assertEqual({p['name'] for p in lesson['incident']},{'Rin','Rf'})
        self.assertNotIn('U1',kcl_equation(c,'Vm'))
        self.assertIn('U1',kcl_equation(c,'Vout'))
        self.assertTrue(lesson['balanced'])
        self.assertTrue(any('I+ = I− = 0' in text for text in lesson['notes'][1]))
        self.assertTrue(any('Linear feedback' in e['label'] for e in lesson['equations']))
        for n in i:
            self.assertTrue(build_lesson(c,n,'0',i,sources,s)['balanced'],n)


class OpenOutputTests(unittest.TestCase):
    def test_dangling_resistor_output_is_defined_with_zero_current(self):
        c = parts('openoutput')
        self.assertEqual(open_circuit_voltage(c,'Vout'),12)
        self.assertEqual(open_circuit_voltage(c,'0','Vout'),-12)
        _, i, sources, s = solve_circuit(c)
        self.assertEqual(branch_current(c[1],get_voltages(c),i,sources,s),0)

    def test_probe_is_not_a_short_or_a_resistive_load(self):
        d = case('openoutput')['drawing']
        c, labels = compile_drawing(d)
        self.assertEqual(output_ports(d,labels),{'OUT1':('Vout','0')})
        self.assertNotEqual(labels['OUT1:1'],labels['OUT1:2'])
        self.assertNotIn('PORT',[p['type'] for p in c])
        without = copy.deepcopy(d)
        without['items']=[p for p in without['items'] if p['type']!='PORT']
        without['wires']=[w for w in without['wires'] if not any('OUT1:' in w[k] for k in ('a','b'))]
        c2,_ = compile_drawing(without)
        self.assertEqual(get_voltages(c),get_voltages(c2))

    def test_disconnected_probe_end_is_reported_as_undefined(self):
        d = case('openoutput')['drawing']
        d['wires']=[w for w in d['wires'] if not any(w[k]=='OUT1:1' for k in ('a','b'))]
        c,labels = compile_drawing(d)
        a,b = output_ports(d,labels)['OUT1']
        with self.assertRaisesRegex(ValueError,'floating terminal'):
            open_circuit_voltage(c,a,b)

    def test_truly_floating_network_does_not_acquire_an_arbitrary_voltage(self):
        c = parts('openoutput')+[dict(name='Rfloat',type='R',node1='floatingA',node2='floatingB',value=1000)]
        with self.assertRaisesRegex(ValueError,'Floating'):
            validate_for_solving(c)
        with self.assertRaisesRegex(ValueError,'No unique DC solution'):
            open_circuit_voltage(c,'floatingA')
