"""SPICE export semantics, result parsing and report freshness."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from examples import get_examples
from spice_export import export_spice
from spice_validate import parse_operating_point, validate_examples, run_ngspice
from topology import compile_drawing
from verification import source_fingerprint, load_spice_report, EXTERNAL_CHECK_FILES


def parts(identifier):
    return compile_drawing(next(e['drawing'] for e in get_examples() if e['id']==identifier))[0]


class SpiceExportTests(unittest.TestCase):
    def test_every_example_exports_without_mutating_the_circuit(self):
        for case in get_examples():
            c,_=compile_drawing(case['drawing']); before=copy.deepcopy(c)
            for dialect in ('ltspice','ngspice'):
                with self.subTest(case=case['id'],dialect=dialect):
                    result=export_spice(c,dialect=dialect)
                    self.assertTrue(result['netlist'].endswith('.op\n.end\n'))
                    self.assertEqual(len(result['element_map']),len(c))
                    self.assertEqual(result['node_map']['0'],'0')
            self.assertEqual(c,before)

    def test_exported_operating_point_can_remove_the_selected_external_load(self):
        c=parts('inverting');result=export_spice(c,load='RL')
        self.assertNotIn('RL',result['element_map'])
        self.assertIn('Rf',result['element_map'])
        self.assertEqual(result['reference_voltages']['Vout'],-2)
        self.assertIn('load RL removed',result['netlist'])
        self.assertEqual(result['removed_load'],'RL')

    def test_feedback_gain_is_an_explicit_approximation_and_probe_is_not_a_load(self):
        result=export_spice(parts('inverting'))
        line=next(l for l in result['netlist'].splitlines() if l.startswith('E_U1 '))
        self.assertEqual(line.split()[-1],'1000000000')
        self.assertNotIn('OUT1',result['element_map'])
        self.assertTrue(any('finite gain' in n for n in result['notes']))

    def test_comparator_formats_preserve_input_polarity_and_custom_limits(self):
        c=parts('comparator_low')
        lt=export_spice(c); ng=export_spice(c,dialect='ngspice')
        self.assertIn('V=if(',lt['netlist'])
        self.assertIn('>0,12,-12)',lt['netlist'])
        self.assertIn('>0 ? 12 : -12',ng['netlist'])
        self.assertTrue(any('equality' in n for n in lt['notes']))

    def test_ambiguous_comparator_and_invalid_feedback_fail_before_export(self):
        c=parts('comparator_high');c[0]['value']=2
        with self.assertRaisesRegex(ValueError,'undefined at the switching threshold'):
            export_spice(c)
        with self.assertRaisesRegex(ValueError,'negative feedback'):
            export_spice(parts('inverting'),load='Rf')

    def test_node_aliases_and_labels_do_not_change_spice_connectivity(self):
        c=parts('openoutput')
        for p in c:
            for key in ('node1','node2'):
                if p[key]=='Vout':p[key]='GND'
        result=export_spice(c)
        self.assertNotEqual(result['node_map']['GND'],'0')
        self.assertFalse(any(' GND ' in l for l in result['netlist'].splitlines() if not l.startswith('*')))
        self.assertEqual(result['reference_voltages']['GND'],12)

    def test_invalid_names_and_formats_cannot_inject_netlist_commands(self):
        c=parts('openoutput');c[1]['name']='R1\n.end'
        with self.assertRaisesRegex(ValueError,'component names'):
            export_spice(c)
        with self.assertRaisesRegex(ValueError,'export format'):
            export_spice(parts('openoutput'),dialect='unknown')


RAW='''Title: test
Plotname: Operating Point
Flags: real
No. Variables: 2
No. Points: 1
Variables:
 0 v(n1) voltage
 1 i(v_v1) current
Values:
0 1.2e1
-0.004
'''


class SpiceReportTests(unittest.TestCase):
    def test_ascii_raw_parser_does_not_confuse_header_count_with_variable_table(self):
        self.assertEqual(parse_operating_point(RAW),{'v(n1)':12,'i(v_v1)':-.004})

    def test_parser_rejects_sweeps_corruption_nonfinite_and_duplicate_variables(self):
        for text in (RAW.replace('Points: 1','Points: 2'),RAW.replace('Flags: real','Flags: complex'),
                     RAW.replace('-0.004','nan'),RAW.replace('-0.004',''),
                     RAW.replace('1 i(v_v1) current','1 v(n1) voltage')):
            with self.subTest(text=text),self.assertRaises(ValueError):parse_operating_point(text)

    def test_external_report_is_invalidated_by_relevant_source_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in EXTERNAL_CHECK_FILES:(root/name).write_text('original '+name)
            (root/'validation').mkdir()
            data=dict(schema='circuitscope.spice-check.v1',source_hashes=source_fingerprint(EXTERNAL_CHECK_FILES,root),
                      rows=[dict(Result='PASS')])
            p=root/'validation/spice_report.json';p.write_text(json.dumps(data))
            report,reason=load_spice_report(root)
            self.assertIsNotNone(report);self.assertIsNone(reason)
            (root/'topology.py').write_text('edited topology')
            report,reason=load_spice_report(root)
            self.assertIsNone(report);self.assertIn('source changed',reason)

    def test_missing_or_malformed_external_report_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(load_spice_report(folder)[0])
            root=Path(folder);(root/'validation').mkdir();(root/'validation/spice_report.json').write_text('{}')
            self.assertIsNone(load_spice_report(root)[0])


NGSPICE=os.environ.get('CIRCUITSCOPE_NGSPICE') or shutil.which('ngspice')


@unittest.skipUnless(NGSPICE,'Optional: install ngspice or set CIRCUITSCOPE_NGSPICE')
class ExternalSpiceTests(unittest.TestCase):
    def test_all_29_external_dc_configurations_match_hand_and_engine_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            report=validate_examples(NGSPICE,folder)
            self.assertEqual(len(report['rows']),29)
            self.assertTrue(all(r['Result']=='PASS' for r in report['rows']),report['rows'])
            self.assertEqual(sum(r['Checks'] for r in report['rows']),293)

    def test_spice_does_not_treat_a_node_named_gnd_as_ground(self):
        c=parts('openoutput')
        for p in c:
            for key in ('node1','node2'):
                if p[key]=='Vout':p[key]='GND'
        voltages,_=run_ngspice(export_spice(c,dialect='ngspice'),NGSPICE)
        self.assertAlmostEqual(voltages['GND'],12)
