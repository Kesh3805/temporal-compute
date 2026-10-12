"""Amendment 0005 section 1: deterministic charged-ray cost for the controller.

The controller ranks by predicted gain per predicted charged ray, the unit of
the registered budget. Cost per region is its cumulative allocation-stream
charged rays per camera sample, already present in RegionState; measured wall
time (launch-dominated and non-reproducible) no longer enters ranking. The
kernel still records elapsed time for end-to-end accounting.
"""
from dataclasses import replace

from amended_policies import AmendedTcPolicy
from progressive_kernel import RegionState, require


def ray_cost(state):
    """Charged rays per camera sample on the allocation stream; None before any sample."""
    require(isinstance(state, RegionState), 'allocation state interface')
    require(type(state.charged_rays) is int and type(state.sample_count) is int and
            state.sample_count >= 0 and state.charged_rays >= state.sample_count, 'charge/sample identity')
    return state.charged_rays/state.sample_count if state.sample_count else None


class RayCostTcPolicy(AmendedTcPolicy):
    """Amended controller or ablation whose cost input is ray_cost, never wall time."""
    def choose(self, states):
        require(isinstance(states, tuple), 'allocation state interface')
        return super().choose(tuple(replace(s, estimated_sample_cost=ray_cost(s)) for s in states))
