"""Transparent, fixed TC-0 fixture recipes. No scheduler-dependent generation."""
from pathlib import Path

SECOND = 1_000_000

def task(id, cost, value, deadline=None, arrival=0, priority=0, fresh=None, kind='constant', **curve):
    result = dict(id=id, arrival_time_us=arrival*SECOND, execution_cost_us=cost*SECOND,
                  priority=priority, base_utility=value, utility=dict(kind=kind, **curve))
    if deadline is not None: result['deadline_us'] = deadline*SECOND
    if fresh is not None: result['fresh_until_us'] = fresh*SECOND
    return result

def save(directory, name, description, tasks):
    lines = ['schema_version = 1', f'name = "{name}"', f'description = "{description}"', '']
    for item in tasks:
        lines.append('[[tasks]]')
        for key, value in item.items():
            if key != 'utility': lines.append(f'{key} = "{value}"' if isinstance(value, str) else f'{key} = {value}')
        lines.append('[tasks.utility]')
        for key, value in item['utility'].items():
            if key == 'steps':
                for after, utility in value:
                    lines += ['[[tasks.utility.steps]]', f'after_us = {after*SECOND}', f'utility = {utility}']
            else: lines.append(f'{key} = "{value}"' if isinstance(value, str) else f'{key} = {value}')
        lines.append('')
    path = Path('scenarios') / directory
    path.mkdir(parents=True, exist_ok=True)
    (path / 'scenario.toml').write_text('\n'.join(lines), encoding='utf-8')

save('tc0-basic', 'tc0-basic', 'Overload: long low-value work competes with short urgent work.', [
    task('a-long', 8, 10, 20, priority=9), task('b-short', 2, 60, 5, priority=1),
    task('c-short', 2, 50, 7, priority=1), task('d-medium', 4, 35, 12, priority=3)])
save('deadline-pressure', 'deadline-pressure', 'EDF control: greedy value and density can sacrifice a feasible urgent task.', [
    task('a-rich', 6, 100, 20), task('b-urgent', 4, 60, 4)])
save('temporal-decay', 'temporal-decay', 'Equal deadlines with distinct decay curves.', [
    task('a-steady', 8, 80, 30),
    task('b-rapid', 2, 100, 30, kind='exponential', interval_us=2*SECOND, retention_ppm=500_000),
    task('c-window', 3, 60, 30, kind='step', steps=[(6, 0)]),
    task('d-linear', 4, 100, 30, kind='linear')])
save('freshness-decay', 'freshness-decay', 'Freshness differs from deadline; stale completions waste compute.', [
    task('a-batch', 7, 30, 30, priority=9),
    task('b-observation', 2, 100, 30, fresh=4),
    task('c-observation', 3, 80, 30, arrival=1, fresh=7),
    task('d-late', 2, 60, 30, arrival=8, fresh=11),
    task('e-stale-risk', 5, 40, 30, arrival=8, fresh=10)])
mixed = []
for i in range(24):
    arrival = (i // 3) * 2
    cost = 1 + ((i * 5 + 3) % 7)
    value = 100 + ((i * 137 + 19) % 801)
    deadline = arrival + 5 + (i * 3 % 15)
    fresh = arrival + 3 + (i % 8) if i % 3 == 0 else None
    curve = i % 4
    args = {}
    if curve == 1: args = dict(kind='linear')
    if curve == 2: args = dict(kind='exponential', interval_us=2*SECOND, retention_ppm=750_000)
    if curve == 3: args = dict(kind='step', steps=[(4, value//2), (8, value//5), (12, 0)])
    mixed.append(task(f'task-{i:02}', cost, value, deadline, arrival, (i*7)%5, fresh, **args))
save('mixed-utility', 'mixed-utility', 'Fixed arithmetic recipe: 24 arrivals with mixed costs, priority, freshness and curves.', mixed)
save('fifo-equivalent', 'fifo-equivalent', 'Underload constant-value control: all policies deliver equal mission utility.', [
    task('a', 2, 10, 100, arrival=0), task('b', 3, 20, 100, arrival=10), task('c', 1, 30, 100, arrival=20)])
save('density-trap', 'density-trap', 'Density control: short cheap work blocks a high-value nonpreemptive task.', [
    task('a-large', 8, 100, 8), task('b-small', 2, 30, 12)])
