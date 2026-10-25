"""Ideal open-loop decisions, model boundaries and complete-circuit loads."""
import copy
import unittest
from circuit_model import branch_current, without_load
from engine import solve_circuit, get_voltages, open_circuit_voltage, thevenin
from examples import get_examples
from topology import compile_drawing, validate_for_solving
from teaching import build_lesson, circuit_signature, kcl_equation


def example(identifier='comparator_high'):
    return next(e for e in get_examples() if e['id']==identifier)


def circuit(identifier='comparator_high'):
    return compile_drawing(example(identifier)['drawing'])[0]


def amp(parts):
    return next(p for p in parts if p['name']=='U1')


class OpenLoopTests(unittest.TestCase):
    def test_high_decision_keeps_distinct_input_voltages_and_zero_input_current(self):
        c=circuit()
        _, i, sources, s=solve_circuit(c)
        v=get_voltages(c)
        self.assertEqual((v['Vin'],v['Vref'],v['Vout']),(3,2,5))
        self.assertAlmostEqual(branch_current(amp(c),v,i,sources,s),-.005)
        for p in c:
            if p['type']=='V':
                self.assertEqual(branch_current(p,v,i,sources,s),0)

    def test_low_decision_supports_bipolar_output_limits(self):
        c=circuit('comparator_low')
        self.assertEqual(get_voltages(c)['Vout'],-12)
        _,i,sources,s=solve_circuit(c)
        self.assertAlmostEqual(branch_current(amp(c),get_voltages(c),i,sources,s),.006)

    def test_single_supply_low_and_swapped_input_polarity(self):
        c=circuit()
        amp(c)['node1'],amp(c)['node2']=amp(c)['node2'],amp(c)['node1']
        self.assertEqual(get_voltages(c)['Vout'],0)

    def test_equal_and_numerically_indistinguishable_inputs_do_not_guess_a_rail(self):
        for difference in (0, .5e-9, -.5e-9):
            c=circuit()
            c[0]['value']=2+difference
            with self.subTest(difference=difference),self.assertRaisesRegex(ValueError,'undefined at the switching threshold'):
                solve_circuit(c)
        for difference,expected in ((2e-9,5),(-2e-9,0)):
            c=circuit();c[0]['value']=2+difference
            self.assertEqual(get_voltages(c)['Vout'],expected)

    def test_open_output_retains_voltage_while_load_current_disappears(self):
        c=circuit();original=copy.deepcopy(c)
        self.assertEqual(open_circuit_voltage(c,'Vout','0','RL'),5)
        w=without_load(c,'RL')
        _,i,sources,s=solve_circuit(w)
        self.assertEqual(branch_current(amp(w),get_voltages(w),i,sources,s),0)
        self.assertEqual(c,original)

    def test_input_divider_and_current_source_are_solved_before_comparison(self):
        c=circuit()
        amp(c)['node1']='Sense'
        c += [dict(name='Ra',type='R',node1='Vin',node2='Sense',value=1000),
              dict(name='Rb',type='R',node1='Sense',node2='0',value=1000)]
        self.assertEqual(get_voltages(c)['Sense'],1.5)
        self.assertEqual(get_voltages(c)['Vout'],0)
        c += [dict(name='Ibias',type='I',node1='0',node2='Sense',value=.002)]
        self.assertEqual(get_voltages(c)['Sense'],2.5)
        self.assertEqual(get_voltages(c)['Vout'],5)

    def test_direct_and_resistive_feedback_are_rejected_in_open_loop_mode(self):
        c=circuit();amp(c)['node2']='Vout'
        with self.assertRaisesRegex(ValueError,'no feedback'):
            solve_circuit(c)
        c=circuit();amp(c)['node2']='Sense'
        c += [dict(name='Rg',type='R',node1='Sense',node2='Vref',value=1000),
              dict(name='Rf',type='R',node1='Sense',node2='Vout',value=1000)]
        with self.assertRaisesRegex(ValueError,'no feedback'):
            solve_circuit(c)

    def test_feedback_through_another_amplifier_is_rejected(self):
        c=circuit();amp(c)['node2']='BufferOut'
        c += [dict(name='U2',type='OPAMP',node1='Vout',node2='BufferOut',node3='BufferOut',v_min=0,v_max=5)]
        with self.assertRaisesRegex(ValueError,'no feedback'):
            solve_circuit(c)

    def test_cascaded_comparators_settle_even_if_an_intermediate_input_ties(self):
        c=circuit()
        c += [dict(name='U2',type='OPAMP',mode='open_loop',node1='Vout',node2='0',node3='Stage2',v_min=0,v_max=5),
              dict(name='U3',type='OPAMP',mode='open_loop',node1='Stage2',node2='0',node3='Stage3',v_min=0,v_max=5)]
        for ordered in (c,list(reversed(c))):
            v=get_voltages(ordered)
            self.assertEqual((v['Vout'],v['Stage2'],v['Stage3']),(5,5,5))

    def test_comparator_can_drive_linear_follower_without_intermediate_rail_error(self):
        c=circuit()
        c += [dict(name='U2',type='OPAMP',node1='Vout',node2='BufferOut',node3='BufferOut',v_min=1,v_max=6)]
        v=get_voltages(c)
        self.assertEqual((v['Vout'],v['BufferOut']),(5,5))
        c[-1]['v_max']=4
        with self.assertRaisesRegex(ValueError,'would saturate'):
            solve_circuit(c)

    def test_undefined_floating_input_is_not_fixed_by_open_loop_mode(self):
        c=circuit();amp(c)['node1']='Floating'
        with self.assertRaisesRegex(ValueError,'Floating node'):
            validate_for_solving(c)
        with self.assertRaisesRegex(ValueError,'No unique DC solution'):
            solve_circuit(c)

    def test_tied_input_and_grounded_output_errors_are_explicit(self):
        c=circuit();amp(c)['node2']='Vin'
        with self.assertRaisesRegex(ValueError,'equal inputs'):
            solve_circuit(c)
        c=circuit();amp(c)['node3']='0'
        with self.assertRaisesRegex(ValueError,'do not short'):
            solve_circuit(c)

    def test_mode_persists_in_netlist_and_old_drawings_default_to_feedback(self):
        c=circuit()
        self.assertEqual(amp(c)['mode'],'open_loop')
        d=next(e['drawing'] for e in get_examples() if e['id']=='follower')
        self.assertNotIn('mode',next(p for p in d['items'] if p['type']=='OPAMP'))
        old,_=compile_drawing(d)
        self.assertEqual(amp(old)['mode'],'feedback')
        self.assertEqual(get_voltages(old)['Vout'],2)
        before=circuit_signature(c);amp(c)['mode']='feedback'
        self.assertNotEqual(before,circuit_signature(c))

    def test_unknown_modes_rejected_in_canvas_and_numerical_api(self):
        d=example()['drawing'];next(p for p in d['items'] if p['type']=='OPAMP')['mode']='typo'
        with self.assertRaisesRegex(ValueError,'mode'):
            compile_drawing(d)
        c=circuit();amp(c)['mode']='typo'
        with self.assertRaisesRegex(ValueError,'mode'):
            solve_circuit(c)

    def test_nonlinear_circuit_does_not_claim_global_thevenin_or_norton(self):
        with self.assertRaisesRegex(ValueError,'require a linear circuit'):
            thevenin(circuit(),'Vout','0','RL')

    def test_open_loop_lesson_shows_decision_without_a_feedback_equality_equation(self):
        c=circuit();_,i,sources,s=solve_circuit(c)
        lesson=build_lesson(c,'Vout','0',i,sources,s)
        self.assertTrue(lesson['balanced'])
        self.assertTrue(any('Open-loop HIGH' in e['label'] for e in lesson['equations']))
        self.assertFalse(any('Linear feedback' in e['label'] for e in lesson['equations']))
        self.assertNotIn('U1',kcl_equation(c,'Vin'))
        self.assertIn('U1',kcl_equation(c,'Vout'))
        self.assertTrue(any('not forced equal' in b['why'] for b in lesson['branches'] if b['name']=='U1'))
        self.assertTrue(any('OPEN LOOP' in n for n in lesson['notes'][0]))

    def test_maximum_number_of_comparators_is_bounded(self):
        c=circuit()
        for n in range(2,10):
            c.append(dict(name=f'U{n}',type='OPAMP',mode='open_loop',node1='Vin',node2='Vref',node3=f'Out{n}',v_min=0,v_max=5))
        with self.assertRaisesRegex(ValueError,'at most 8'):
            solve_circuit(c)
