import copy
import unittest

import engine
from examples import get_examples
from topology import compile_drawing, validate_for_solving
from verification import verify_example, verify_examples


class ReferenceExamplesTests(unittest.TestCase):
    def test_all_hand_calculated_cases_with_the_included_engine(self):
        cases = get_examples()
        self.assertEqual(len(cases), 9)
        for case in cases:
            with self.subTest(case=case['id']):
                row = verify_example(case, engine.solve_circuit, engine.thevenin)
                self.assertEqual(row['Result'], 'PASS', row['Details'])
                passed, total = map(int, row['Checks'].split('/'))
                self.assertEqual(passed, total)
                self.assertGreaterEqual(total, 10)

    def test_fresh_examples_and_checks_do_not_mutate_the_circuits(self):
        first, second = get_examples(), get_examples()
        first[0]['drawing']['items'][0]['value'] = 99
        self.assertEqual(second[0]['drawing']['items'][0]['value'], 12)
        before = copy.deepcopy(second[3])
        verify_example(second[3], engine.solve_circuit, engine.thevenin)
        self.assertEqual(second[3], before)

    def test_every_expected_node_is_present_and_all_terminals_are_connected(self):
        for case in get_examples():
            with self.subTest(case=case['id']):
                parts, labels = compile_drawing(case['drawing'])
                validate_for_solving(parts)
                self.assertEqual(set(case['expected_v']), set(labels.values()))

    def test_bad_solver_numbers_are_detected(self):
        def wrong_solver(parts):
            nodes, index, sources, solution = engine.solve_circuit(parts)
            solution = solution.copy()
            solution[0] += 1
            return nodes, index, sources, solution
        result = verify_example(get_examples()[1], wrong_solver, engine.thevenin)
        self.assertEqual(result['Result'], 'FAIL')
        self.assertIn('expected', result['Details'])

    def test_bad_equivalent_results_are_detected(self):
        result = verify_example(get_examples()[4], engine.solve_circuit, lambda *args: (99, 100))
        self.assertEqual(result['Result'], 'FAIL')
        self.assertIn('Thévenin', result['Details'])

    def test_solver_errors_are_reported_per_circuit(self):
        def broken_solver(parts):
            raise ValueError('Example failure')
        rows = verify_examples(broken_solver, engine.thevenin)
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row['Result']=='FAIL' for row in rows))
        self.assertTrue(all('Example failure' in row['Details'] for row in rows))
