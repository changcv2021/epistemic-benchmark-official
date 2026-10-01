"""Synthetic software fixtures only: no recorded model answers."""
import copy
import unittest

from epistemic_benchmark.analysis.design import coefficients
from epistemic_benchmark.analysis.diagnostics import holm
from epistemic_benchmark.analysis.interventions import bootstrap
from epistemic_benchmark.backends.inference import build_payload
from epistemic_benchmark.cli import score
from epistemic_benchmark.evaluation.attempts import validate_attempts
from epistemic_benchmark.evaluation.parser import parse_answer
from epistemic_benchmark.evaluation.scoring import parse
from epistemic_benchmark.prompts.benchmark import inventory
from epistemic_benchmark.prompts.interventions import render_flat, render_ledger, validate_renderers
from epistemic_benchmark.utils.io import digest


class ProtocolTests(unittest.TestCase):
    def test_strict_choice_parser(self):
        for bad in ('A', '{"answer":"A","explanation":"x"}', '{"answer":"A","answer":"B"}', '{"answer":"C"}'):
            self.assertIsNone(parse_answer(bad, {'A':'left','B':'right'})[0])
        self.assertEqual(parse_answer('```json\n{"answer":"B"}\n```', {'A':'left','B':'right'}), ('B',None))

    def test_exact_count_parser(self):
        self.assertEqual(parse('7','integer_0_8',{}), (7,None))
        for bad in ('9','07','seven','{"answer":7}'):
            self.assertIsNone(parse(bad,'integer_0_8',{})[0])

    def test_factorial_contrasts(self):
        weights=coefficients()
        self.assertEqual(set(weights), {'R','Q','I','R_x_Q','R_x_I','Q_x_I','R_x_Q_x_I'})
        for row in weights.values():
            self.assertEqual(len(row),8)
            self.assertEqual(sum(row.values()),0)

    def test_absolute_of_mean_not_mean_absolute(self):
        self.assertEqual(bootstrap([1.,-1.],[0.,0.],absolute=True,reps=100)['estimate'],0)
        self.assertIsNone(bootstrap([],reps=100)['estimate'])
        self.assertIsNone(bootstrap([0.],reps=100)['ci95'])

    def test_holm_keeps_missing_family_members(self):
        actual=holm({'observed':.01,'missing':None},48)
        self.assertAlmostEqual(actual['observed'],.48)
        self.assertIsNone(actual['missing'])

    def test_benchmark_complete_inventory(self):
        rows=inventory({'world_id':'fixture'})
        self.assertEqual(len(rows),48)
        self.assertEqual(len({r[3] for r in rows}),48)

    def test_flat_and_ledger_have_same_facts(self):
        facts=[dict(group='Source O1',key='History',sentence='O1 matched seven of eight checks.'),dict(group='Source O2',key='History',sentence='O2 matched four of eight checks.')]
        flat,ledger=render_flat(facts),render_ledger(facts)
        validate_renderers(facts,flat,ledger)
        with self.assertRaises(ValueError):
            validate_renderers(facts,flat+' A recommendation.',ledger)

    def fixture(self):
        request=dict(request_id='fixture',messages=[dict(role='system',content='Synthetic test.'),dict(role='user',content='Synthetic test only.')])
        manifest=dict(request_id='fixture',case_id='c',world_id='w',family='T3',variant='LH',relation_family='location',probe_id='P4',output_protocol='json_option_letter',track_id='T3',task_id='ReliabilitySwap',condition_id='LH',split='core',renderer_id='fixture')
        label=dict(request_id='fixture',has_gold=False,gold_answer=None,choice_to_semantic_answer={'A':'A','B':'B'})
        bundle=dict(requests=[request],manifests=[manifest],labels=[label])
        attempt=dict(request_id='fixture',attempt=1,input_hash=digest(request['messages']),status='completed',terminal=True,decoded=dict(content='{"answer":"B"}',finish_reason='stop',reasoning_content=None))
        return bundle,attempt

    def test_attempt_context_hash_and_terminal_history(self):
        bundle,attempt=self.fixture()
        validate_attempts([attempt],{'fixture':bundle['requests'][0]})
        bad=dict(attempt,input_hash='changed')
        with self.assertRaises(ValueError):validate_attempts([bad],{'fixture':bundle['requests'][0]})
        with self.assertRaises(ValueError):validate_attempts([attempt,dict(attempt,attempt=2)],{'fixture':bundle['requests'][0]})

    def test_missing_unverified_answer_is_not_imputed(self):
        bundle,_=self.fixture();row=score('benchmark',bundle,[])[0]
        self.assertEqual(row['status'],'not_run')
        self.assertIsNone(row['semantic_answer'])
        self.assertIsNone(row['correct'])

    def test_native_reasoning_policy_is_explicit(self):
        bundle,attempt=self.fixture();attempt['decoded']['reasoning_content']='synthetic presence marker'
        self.assertFalse(score('benchmark',bundle,[attempt])[0]['valid'])
        row=score('benchmark',bundle,[attempt],native_api=True)[0]
        self.assertTrue(row['valid']);self.assertIsNone(row['correct'])
        self.assertEqual(attempt['decoded']['reasoning_content'],'synthetic presence marker')

    def test_payload_has_no_labels_credentials_or_history(self):
        bundle,_=self.fixture();messages=bundle['requests'][0]['messages']
        entry=dict(provider='openai_responses',model_id='fixture-model',key='synthetic-secret')
        self.assertEqual(build_payload(entry,messages,{}),dict(model='fixture-model',input=messages))
        with self.assertRaises(ValueError):build_payload(entry,messages+[dict(role='assistant',content='prior answer')],{})


if __name__=='__main__':
    unittest.main()
