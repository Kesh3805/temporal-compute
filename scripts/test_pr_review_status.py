"""Deterministic API fixtures; tests never access live GitHub."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from pr_review_status import collect, gate, pages, summarize

HEAD = 'a'*40
CONFIG = {'coderabbit_status_contexts': ['Observed review context']}


def fixture():
    return dict(pr={'number': 12, 'head': {'sha': HEAD}, 'draft': False,
                    'state': 'open', 'mergeable': True},
        checks=[{'id': 1, 'name': 'arbitrary CI name', 'app': {'id': 1, 'slug': 'github-actions'},
                 'status': 'completed', 'conclusion': 'success'},
                {'id': 2, 'name': 'new review name', 'app': {'id': 2, 'slug': 'coderabbitai'},
                 'status': 'completed', 'conclusion': 'success'}],
        statuses=[], reviews=[{'id': 1, 'user': {'login': 'coderabbitai[bot]'},
            'commit_id': HEAD, 'state': 'COMMENTED', 'body': 'Review summary'}],
        comments=[], inline_comments=[], threads=[])


class StatusTests(unittest.TestCase):
    def result(self, data):
        return summarize(data, CONFIG, HEAD, HEAD)

    def test_all_gates_green_and_attestations_required(self):
        self.assertTrue(self.result(fixture())['merge_ready'])
        self.assertFalse(summarize(fixture(),CONFIG)['merge_ready'])
        self.assertFalse(summarize(fixture(),CONFIG,'b'*40,HEAD)['merge_ready'])

    def test_ci_pending_and_failed(self):
        for status, conclusion, expected in [('in_progress',None,'pending'),('completed','failure','failed')]:
            data=fixture()
            data['checks'][0].update(status=status,conclusion=conclusion)
            self.assertEqual(self.result(data)['ci'],expected)
            self.assertFalse(self.result(data)['merge_ready'])

    def test_rabbit_pending_failed_skipped_missing(self):
        for status, conclusion, expected in [('in_progress',None,'pending'),
                ('completed','failure','failed'),('completed','skipped','skipped')]:
            data=fixture()
            data['checks'][1].update(status=status,conclusion=conclusion)
            self.assertEqual(self.result(data)['coderabbit'],expected)
        data=fixture()
        data['checks'].pop()
        self.assertEqual(self.result(data)['coderabbit'],'missing')

    def test_completed_with_comments_and_outdated_unresolved_thread(self):
        data=fixture()
        data['threads']=[{'id':'t','isResolved':False,'isOutdated':True,'comments':{'nodes':[]}}]
        self.assertEqual(self.result(data)['coderabbit'],'complete')
        self.assertFalse(self.result(data)['merge_ready'])
        data['threads'][0]['isResolved']=True
        self.assertTrue(self.result(data)['merge_ready'])

    def test_human_requested_changes_and_comments_preserved(self):
        data=fixture()
        data['comments']=[{'user':{'login':'maintainer'},'body':'Please inspect this.'}]
        self.assertEqual(self.result(data)['feedback']['comments'],data['comments'])
        data['reviews'].append({'id':2,'user':{'login':'maintainer'},'state':'CHANGES_REQUESTED'})
        self.assertFalse(self.result(data)['merge_ready'])
        data['reviews'].append({'id':3,'user':{'login':'maintainer'},'state':'APPROVED'})
        self.assertTrue(self.result(data)['merge_ready'])

    def test_stale_review_cannot_approve_current_head(self):
        data=fixture()
        data['reviews'][0]['commit_id']='b'*40
        self.assertEqual(self.result(data)['coderabbit'],'unverified')

    def test_bot_requested_changes_block_even_without_threads(self):
        data=fixture()
        data['reviews'][0]['state']='CHANGES_REQUESTED'
        self.assertFalse(self.result(data)['merge_ready'])

    def test_legacy_context_must_be_discovered(self):
        data=fixture()
        data['checks'].pop()
        data['statuses']=[{'id':3,'context':'Observed review context','state':'success'}]
        self.assertTrue(self.result(data)['merge_ready'])
        data['statuses'][0]['context']='Guessed CodeRabbit name'
        self.assertEqual(self.result(data)['coderabbit'],'missing')

    def test_unknown_new_check_conclusion_fails_closed(self):
        data=fixture()
        data['checks'][0]['conclusion']='brand_new_state'
        self.assertEqual(self.result(data)['ci'],'unknown')
        self.assertFalse(self.result(data)['merge_ready'])

    def test_latest_rerun_and_status_win(self):
        data=fixture()
        old=deepcopy(data['checks'][0])
        old.update(id=0,conclusion='failure')
        data['checks'].append(old)
        self.assertTrue(self.result(data)['merge_ready'])

    def test_skipped_rate_limited_not_clean(self):
        for body, state in [('Review skipped','skipped'),('Rate limit exceeded','rate_limited')]:
            data=fixture()
            data['checks'][1].update(status='in_progress',conclusion=None)
            data['comments']=[{'user':{'login':'coderabbitai[bot]'},'body':body,'updated_at':'2026-10-07'}]
            self.assertEqual(self.result(data)['coderabbit'],state)

    def test_draft_closed_unknown_mergeability_missing_required(self):
        for key, value in [('draft',True),('state','closed'),('mergeable',None)]:
            data=fixture()
            data['pr'][key]=value
            self.assertFalse(self.result(data)['merge_ready'])
        self.assertEqual(summarize(fixture(),{'required_checks':['Absent']})['ci'],'missing')

    def test_pagination_and_api_errors(self):
        with patch('pr_review_status.gh',side_effect=[[{}]*100,[{'id':101}]]) as mock:
            self.assertEqual(len(pages('endpoint')),101)
            self.assertIn('page=2',mock.call_args.args[-1])
        with patch('pr_review_status.gh',side_effect=[fixture()['pr'],{'errors':['denied']}]):
            with self.assertRaises(ValueError):
                collect('owner/repo',12)

    def test_neutral_is_not_success(self):
        self.assertEqual(gate([{'state':'neutral'}]),'skipped')


if __name__=='__main__':
    unittest.main()
