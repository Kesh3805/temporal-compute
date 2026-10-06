"""Deterministic API fixtures; tests never access live GitHub."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from pr_review_status import collect, gate, main, pages, summarize

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

    def test_empty_bot_reply_review_cannot_certify_code_review(self):
        data=fixture()
        data['reviews'][0]['body']=''
        data['inline_comments']=[{'pull_request_review_id':1,'in_reply_to_id':999}]
        self.assertEqual(self.result(data)['coderabbit'],'unverified')
        data['inline_comments'][0].pop('in_reply_to_id')
        self.assertEqual(self.result(data)['coderabbit'],'complete')

    def test_bot_requested_changes_block_even_without_threads(self):
        data=fixture()
        data['reviews'][0]['state']='CHANGES_REQUESTED'
        self.assertFalse(self.result(data)['merge_ready'])

    def test_review_state_must_be_eligible_before_evidence_counts(self):
        for state in ('DISMISSED', 'PENDING', 'NEW_STATE', None):
            for evidence in ('body', 'inline'):
                with self.subTest(state=state,evidence=evidence):
                    data=fixture()
                    review=data['reviews'][0]
                    if state is None:
                        review.pop('state')
                    else:
                        review['state']=state
                    review['body']='Review summary' if evidence=='body' else ''
                    if evidence=='inline':
                        data['inline_comments']=[{'pull_request_review_id':review['id']}]
                    result=self.result(data)
                    self.assertEqual(result['coderabbit'],'unverified')
                    self.assertFalse(result['merge_ready'])

    def test_eligible_review_states_with_required_evidence(self):
        for state, body, comments, substantive, blocked in (
                ('COMMENTED','Summary',[],True,False),
                ('COMMENTED','',[{'pull_request_review_id':1}],True,False),
                ('COMMENTED','',[{'pull_request_review_id':1,'in_reply_to_id':2}],False,False),
                ('APPROVED','',[],True,False),
                ('CHANGES_REQUESTED','',[],True,True)):
            with self.subTest(state=state,body=body,comments=comments):
                data=fixture()
                data['reviews'][0].update(state=state,body=body)
                data['inline_comments']=comments
                result=self.result(data)
                self.assertEqual(result['coderabbit'],'complete' if substantive else 'unverified')
                self.assertEqual(result['merge_ready'],substantive and not blocked)

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

    def test_deleted_authors_are_retained_without_crashing(self):
        data=fixture()
        data['comments']=[{'user':None,'body':'Historical comment'}]
        data['reviews'] += [{'id':2,'user':None,'state':'CHANGES_REQUESTED'},
                            {'id':3,'user':None,'state':'APPROVED'}]
        result=self.result(data)
        self.assertEqual(result['human_requested_changes'],1)
        self.assertFalse(result['merge_ready'])
        self.assertEqual(result['feedback']['comments'],data['comments'])

    def run_wait(self, snapshots):
        args=['script','--pr','12','--wait','--max-polls','2',
              '--local-validated-sha',HEAD,'--findings-addressed-sha',HEAD]
        with patch('sys.argv',args), patch('pr_review_status.collect',side_effect=snapshots), \
             patch('pathlib.Path.read_text',return_value=json.dumps(CONFIG)), \
             patch('pr_review_status.time.sleep') as sleeper, patch('builtins.print'):
            return main(),sleeper.call_count

    def test_wait_unknown_mergeability_then_success(self):
        pending=fixture()
        pending['pr']['mergeable']=None
        self.assertEqual(self.run_wait([pending,fixture()]),(0,1))

    def test_wait_unknown_mergeability_exhausts_bound(self):
        pending=fixture()
        pending['pr']['mergeable']=None
        self.assertEqual(self.run_wait([pending,pending]),(2,1))

    def test_wait_settled_review_blocker_exits(self):
        blocked=fixture()
        blocked['threads']=[{'isResolved':False}]
        self.assertEqual(self.run_wait([blocked]),(1,0))


if __name__=='__main__':
    unittest.main()
