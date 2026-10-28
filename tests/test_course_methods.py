from copy import deepcopy
import unittest
from course_examples import get_course_examples
from course_ui import verify_course_examples
from course_methods import *
from circuit_layout import netlist_to_drawing, preview_svg
from topology import compile_drawing


def circuit(identifier):
    return compile_drawing(next(e['drawing'] for e in get_course_examples() if e['id']==identifier))[0]


class CourseMethodTests(unittest.TestCase):
    def test_new_drawings_match_fixed_hand_answers_and_kcl(self):
        rows=verify_course_examples()
        self.assertEqual(len(rows),7)
        self.assertTrue(all(r['Result']=='PASS' for r in rows),rows)

    def test_supernode_boundary_cancels_internal_source_and_resistor(self):
        p=circuit('supernode');g=supernodes(p)[0]
        self.assertEqual(g['nodes'],['Va','Vb']);self.assertEqual(g['sources'],['V1'])
        self.assertNotIn('I_',g['kcl']);self.assertEqual(len(g['constraints']),1)
        p.append(dict(name='Rinside',type='R',node1='Va',node2='Vb',value=100))
        self.assertEqual(supernodes(p)[0]['kcl'],g['kcl'])

    def test_chained_supernode_and_grounded_sources(self):
        p=circuit('supernode');p.append(dict(name='V2',type='V',node1='Vb',node2='Vc',value=1))
        g=supernodes(p)[0];self.assertEqual(g['nodes'],['Va','Vb','Vc']);self.assertEqual(len(g['constraints']),2)
        self.assertEqual(supernodes(circuit('divider')),[])

    def test_superposition_voltage_and_signed_branch_current(self):
        p=circuit('mixed_sources');original=deepcopy(p)
        result=superposition(p,'Va')
        self.assertAlmostEqual(result['rows'][0]['value'],8)
        self.assertAlmostEqual(result['rows'][1]['value'],4/3)
        self.assertAlmostEqual(result['full'],28/3);self.assertTrue(result['agrees'])
        self.assertTrue(superposition(p,'Va',branch='V1')['agrees']);self.assertEqual(p,original)

    def test_superposition_keeps_feedback_active_and_rejects_comparators(self):
        r=superposition(circuit('inverting_sum'),'Vout')
        self.assertEqual([round(row['value'],8) for row in r['rows']],[-2,-2])
        from examples import get_examples
        p=compile_drawing(next(e['drawing'] for e in get_examples() if e['id']=='comparator_high'))[0]
        with self.assertRaisesRegex(ValueError,'linear'):superposition(p,'Vout')

    def test_voltage_source_transformation_and_reverse_preserve_external_voltage(self):
        p=circuit('divider');original=deepcopy(p)
        c=transformation_candidates(p)[0]
        self.assertEqual((c['a'],c['b'],c['value']),('Va','0',.012))
        transformed=transform_source(p,c)['components']
        self.assertAlmostEqual(operating_point(transformed)[0]['Va'],8)
        reverse=next(c for c in transformation_candidates(transformed) if c['resistor']=='R1')
        self.assertAlmostEqual(operating_point(transform_source(transformed,reverse)['components'])[0]['Va'],8)
        self.assertEqual(p,original)

    def test_source_reversal_and_negative_value_have_correct_polarity(self):
        for reverse in (False,True):
            for sign in (1,-1):
                p=circuit('divider');v=next(x for x in p if x['type']=='V');v['value']*=sign
                if reverse:v['node1'],v['node2']=v['node2'],v['node1']
                c=transformation_candidates(p)[0]
                self.assertAlmostEqual(operating_point(transform_source(p,c)['components'])[0]['Va'],8*sign*(-1 if reverse else 1))

    def test_transformations_reject_observed_or_branched_private_node(self):
        p=circuit('divider')
        self.assertEqual(transformation_candidates(p,{'Vs'}),[])
        p.append(dict(name='Rx',type='R',node1='Vs',node2='0',value=500))
        self.assertFalse(any(c['kind']=='V to I' for c in transformation_candidates(p)))

    def test_divider_loaded_and_unloaded_values_and_wrong_loading(self):
        self.assertAlmostEqual(divider(circuit('divider'),'R1','R2')['predicted'],8)
        r=divider(circuit('loaded_divider'),'R1','R2','RL');self.assertAlmostEqual(r['predicted'],6)
        self.assertAlmostEqual(r['bottom'],1000)
        with self.assertRaisesRegex(ValueError,'loads'):divider(circuit('loaded_divider'),'R1','R2')
        with self.assertRaises(ValueError):divider(circuit('divider'),'R1','R1')

    def test_feedback_follower_and_cascade_paths(self):
        paths=feedback_paths(circuit('feedback_cascade'))
        self.assertEqual(paths[0]['path'],[]);self.assertEqual(paths[1]['path'],['Rf'])
        p=circuit('inverting_sum');amp=next(x for x in p if x['type']=='OPAMP');amp['node1'],amp['node2']=amp['node2'],amp['node1']
        with self.assertRaises(ValueError):feedback_paths(p)

    def test_inverting_and_noninverting_summing_predictions(self):
        for identifier,expected in [('inverting_sum',-4),('noninverting_sum',4)]:
            p=circuit(identifier);r=summing_amplifiers(p)[0]
            self.assertAlmostEqual(r['predicted'],expected);self.assertAlmostEqual(r['actual'],expected)
        p=circuit('inverting_sum');p.append(dict(name='Ix',type='I',node1='0',node2='Vm',value=.0001))
        self.assertEqual(summing_amplifiers(p),[])

    def test_generated_editable_wiring_round_trips_the_netlist(self):
        for e in get_course_examples():
            p,_=compile_drawing(e['drawing']);generated=netlist_to_drawing(p)
            compiled,_=compile_drawing(generated)
            self.assertEqual(sorted(compiled,key=lambda x:x['name']),sorted(p,key=lambda x:x['name']))
            svg=preview_svg(generated);self.assertTrue(svg.startswith('<svg'));self.assertNotIn('<script',svg)
