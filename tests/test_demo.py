"""End-to-end classroom outcomes, kept separate from agricultural knowledge."""
import unittest
from agent import run_assessment
from demo import PRESETS, demo_knowledge
from tests.test_app import request


class TestClassroomDemo(unittest.TestCase):
    def test_expected_outcomes(self):
        expected = {
            'match': ('FEASIBLE_OPTIONS_FOUND', ['wheat', 'maize']),
            'water': ('FEASIBLE_OPTIONS_FOUND', ['wheat']),
            'reject': ('NO_FEASIBLE_OPTION', []),
            'unknown': ('MORE_INFORMATION_NEEDED', []),
        }
        for key, (status, ids) in expected.items():
            with self.subTest(key=key):
                report = run_assessment(PRESETS[key][1], knowledge_override=demo_knowledge())
                self.assertEqual(report['status'], status)
                self.assertEqual([c['candidate_id'] for c in report['feasible_options']], ids)
                self.assertTrue(report['rule_results'])

    def test_public_website_never_uses_synthetic_fixtures(self):
        import json
        _, raw = request('POST', '/report', PRESETS['match'][1])
        report = json.loads(raw)
        self.assertEqual(report['dataset_kind'], 'research')
        self.assertNotIn('SYNTHETIC_SOURCE', str(report['evidence_package']))
        _, body = request('POST', '/assess', PRESETS['match'][1])
        self.assertNotIn('synthetic', body.lower())
        self.assertNotIn('RULE_KB_001', body)
        self.assertIn('Published reference', body)

    def test_refresh_assessment_route(self):
        self.assertEqual(request('GET', '/assess')[0], '200 OK')
