"""Phase-A tests: no TC-S1 scheduler comparisons are executed."""
import ast
import copy
import itertools
import json
from pathlib import Path
import unittest
import tc_s1_generate as gen
import tc_s1_analysis as analysis


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = gen.config()
        cls.all = list(gen.corpus(cls.cfg, sensitivities=True))
        cls.primary = [(m,s) for m,s in cls.all if m['profile']=='primary']

    def test_splitmix_known_vector(self):
        rng = gen.SplitMix64(0)
        self.assertEqual([rng.next() for _ in range(3)], [0xE220A8397B1DCDAF,0x6E789E6AA1B965F4,0x06C45D188009454F])

    def test_seed_derivation_is_domain_separated(self):
        seeds = [m['seed'] for m,s in self.all if m['profile'] in ['primary','oracle','control']]
        self.assertEqual(len(seeds),len(set(seeds)))

    def test_manifest_exactly_reproduces(self):
        self.assertEqual(gen.manifest(),gen.verify())

    def test_generator_reproduces_every_definition(self):
        self.assertEqual(self.all,list(gen.corpus(self.cfg,sensitivities=True)))

    def test_complete_balanced_seed_set(self):
        cells = {}
        for m,s in self.primary:
            cells.setdefault((m['mission_mix'],m['load_regime']),[]).append(m['replicate'])
        self.assertEqual((len(self.primary),len(cells),list(cells.values())),(200,20,[list(range(10))]*20))

    def test_primary_class_bounds_and_initial_feasibility(self):
        for meta,scenario in self.primary:
            self.assertEqual(len(scenario['tasks']),48)
            for task in scenario['tasks']:
                cls = self.cfg['classes'][gen.task_class(task)]
                at = task['arrival_time_us']
                for field,param in [('execution_cost_us','cost_s'),('deadline_us','deadline_s'),('fresh_until_us','fresh_s')]:
                    value = task[field]-(at if field!='execution_cost_us' else 0)
                    self.assertTrue(cls[param][0]*gen.SECOND <= value <= cls[param][1]*gen.SECOND)
                self.assertTrue(cls['base'][0] <= task['base_utility'] <= cls['base'][1])
                self.assertEqual(task['priority'],cls['priority'])
                self.assertLessEqual(at+task['execution_cost_us'],min(task['deadline_us'],task['fresh_until_us']))

    def test_every_scenario_hash_and_value_invariant(self):
        for meta,scenario in self.all:
            self.assertEqual(meta['sha256'],gen.digest(scenario))
            self.assertEqual(len({t['id'] for t in scenario['tasks']}),len(scenario['tasks']))
            for task in scenario['tasks']:
                self.assertGreater(task['execution_cost_us'],0)
                self.assertGreater(task['base_utility'],0)
                curve = task['utility']
                if curve['kind']=='exponential':
                    self.assertTrue(0 <= curve['retention_ppm'] <= 1_000_000 and curve['interval_us']>0)
                steps = curve.get('steps',[])
                self.assertEqual(sorted(s['after_us'] for s in steps),[s['after_us'] for s in steps])
                self.assertEqual(sorted([task['base_utility']]+[s['utility'] for s in steps],reverse=True),[task['base_utility']]+[s['utility'] for s in steps])

    def test_sensitivity_is_paired_and_cost_does_not_move_arrivals(self):
        original,scenario = self.primary[0]
        meta,perturbed = gen.primary(self.cfg,original['mission_mix'],original['load_regime'],0,1,'cost-plus20')
        self.assertEqual(meta['seed'],original['seed'])
        self.assertEqual([t['arrival_time_us'] for t in perturbed['tasks']],[t['arrival_time_us'] for t in scenario['tasks']])
        self.assertEqual([t['execution_cost_us'] for t in perturbed['tasks']],[t['execution_cost_us']*120//100 for t in scenario['tasks']])

    def test_generator_has_no_policy_imports_or_calls(self):
        tree = ast.parse(Path(gen.__file__).read_text())
        names = [n.id for n in ast.walk(tree) if isinstance(n,ast.Name)]
        self.assertFalse(set(names)&{'simulate','select_next','Scheduler','Policy','subprocess'})

    def test_hash_detects_a_single_value_change(self):
        meta,original = self.primary[0]
        changed = copy.deepcopy(original)
        changed['tasks'][0]['base_utility'] += 1
        self.assertNotEqual(meta['sha256'],gen.digest(changed))


class AnalysisTests(unittest.TestCase):
    def test_quantiles_have_known_interpolation(self):
        self.assertEqual(analysis.distribution([0,10,20,30])['p10'],3.0)

    def test_oracle_matches_exhaustive_search_including_idling(self):
        tasks = [gen.simple_task('t000-IMAGE_COMPRESSION',5,10),gen.simple_task('t001-WILDFIRE_ALERT',1,100,deadline=2,arrival=1),gen.simple_task('t002-DISASTER_MAPPING',3,20,deadline=10)]
        best = 0
        for size in range(len(tasks)+1):
            for order in itertools.permutations(tasks,size):
                now = value = 0
                for task in order:
                    now = max(now,task['arrival_time_us'])+task['execution_cost_us']
                    value += analysis.utility_at(task,now)
                best = max(best,value)
        self.assertEqual(analysis.oracle({'tasks':tasks})['utility'],best)

    def test_python_utility_matches_existing_tc0_recordings(self):
        for path in (gen.ROOT/'results/tc0').glob('*.json'):
            if path.name=='summary.json':
                continue
            for run in json.loads(path.read_text())['runs']:
                tasks = {t['id']:t for t in run['scenario']['tasks']}
                for event in run['events']:
                    if event['event']=='task_completed':
                        self.assertEqual(analysis.utility_at(tasks[event['task_id']],event['sim_time_us']),event['utility'])

    def test_paired_bootstrap_preserves_constant_known_difference(self):
        cfg = gen.config()
        cfg['analysis']['bootstrap_resamples'] = 100
        rows = []
        for i in range(4):
            for policy in cfg['schedulers']:
                value = 10*(i+1)+(3 if policy==cfg['primary_scheduler'] else 0)
                rows.append(dict(id=str(i),scheduler=policy,mission_mix='synthetic',load_regime=str(i//2),metrics={'total_utility':value,'maximum_task_utility_sum':100}))
        result = analysis.paired(rows,cfg)
        self.assertEqual((result['fifo']['wins'],result['fifo']['bootstrap_mean_delta_ci']),(4,[3.0,3.0]))


if __name__=='__main__':
    unittest.main()
