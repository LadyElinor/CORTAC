"""Regression checks for the agent's read surface and exported evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from wac_offline.agent_controls import AgentControlGateway, report
from wac_offline.runner import RunnerError
from wac_offline.runner_fixtures import fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from check_agent_controls import check


class AgentControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observed = report()

    def test_frozen_matrix_reconciles(self):
        self.assertEqual(check(self.observed), 42)

    def test_denied_reads_never_return_the_private_record(self):
        data = fixture()
        note = {'content': 'Synthetic private ticket 119'}
        with AgentControlGateway(data, 'refund', note) as gateway:
            for session in (None, 'unknown', 'guest-session', 'green-session'):
                with self.subTest(session=session), self.assertRaises(RunnerError):
                    gateway.reader_call(session, 'read_record', 'private-ticket')
            with self.assertRaisesRegex(RunnerError, 'record access denied'):
                gateway.reader_call('blue-session', 'read_record', 'missing')
            for event in gateway.snapshot()['journal']:
                self.assertEqual(event['result'], 'REJECTED')
                self.assertNotIn(note['content'], str(event))
            delivery = gateway.reader_call('blue-session', 'read_record', 'private-ticket')
            delivery.clear()
            self.assertEqual(gateway.reader_call('blue-session', 'read_record', 'private-ticket'), note)

    def test_incomplete_and_duplicated_case_exports_are_rejected(self):
        for replacement in ([], [self.observed['rows'][0]]):
            export = dict(self.observed, rows=self.observed['rows'][:-1] + replacement)
            with self.assertRaisesRegex(ValueError, 'inventory'):
                check(export)

    def test_checker_detects_tampered_evidence(self):
        def edited(case):
            export = deepcopy(self.observed)
            row = next(r for r in export['rows'] if r['inputs']['case'] == case)
            return export, row

        changes = [('effect_failure', lambda r: r['state'].update(simulated_commands=[{}])),
                   ('revoked', lambda r: r['state']['journal'].pop()),
                   ('approved', lambda r: r['state']['effects'][0].update(executor='reader')),
                   ('approved', lambda r: r['state']['receipts']['r3'].update(result='FAIL')),
                   ('approved', lambda r: r['audit'].update(observed_revision=True)),
                   ('anonymous', lambda r: r.update(read_digest='delivered')),
                   ('withheld', lambda r: r['inputs'].update(review_granted=True))]
        for case, mutate in changes:
            with self.subTest(case=case):
                export, row = edited(case)
                mutate(row)
                with self.assertRaises(ValueError):
                    check(export)


class TraceReadbackTests(unittest.TestCase):
    def test_timeline_and_applied_geometry(self):
        from check_robot_payloads import WEEVIL, WEEVIL_BASELINE, check_weevil_samples
        scenario = dict(scenario_id='fixture', duration_s=0.0034, timestep_s=0.001,
                        slope_deg=10.0, gravity_m_s2=1.62)
        metadata = dict(scenario_id='fixture', duration_s=0.0034, timestep_s=0.001,
                        engine_version='fixture', elapsed_s=0.003, sampling_phase='post_step',
                        requested_slope_deg=10, applied_slope_deg=10, applied_gravity_m_s2=[0,0,-1.62])
        trace = dict(metadata=metadata, summary=dict(completed=True, total_steps=3),
                     steps=[dict(step=i, time_s=(i+1)*0.001) for i in range(3)])
        result = check_weevil_samples(trace, scenario, WEEVIL)
        self.assertEqual((result['simulated_seconds'], result['requested_seconds']), (0.003, 0.0034))
        self.assertFalse(check_weevil_samples(trace, scenario, WEEVIL_BASELINE)['geometry_readback_verified'])
        for key, value in [('applied_slope_deg',25), ('sampling_phase','pre_step'),
                           ('applied_gravity_m_s2',[0,0,-9.81]), ('elapsed_s',float('nan'))]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_weevil_samples(dict(trace, metadata=dict(metadata, **{key:value})), scenario, WEEVIL)
        for key, value in [('step',0), ('step',True), ('time_s',float('nan')), ('time_s',0.001)]:
            damaged = deepcopy(trace)
            damaged['steps'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check_weevil_samples(damaged, scenario, WEEVIL)
