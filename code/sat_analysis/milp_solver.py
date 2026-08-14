"""
Shared MILP solver configuration for Tempest v3 security verification.
Auto-detects best available solver: HiGHS -> SCIP -> PULP_CBC_CMD
All scripts should import get_solver() from here.
"""
import pulp
import sys

def get_solver(timeLimit=300, threads=0, msg=False):
    """Return best available solver in order of preference."""
    available = pulp.listSolvers(onlyAvailable=True)

    # HiGHS: fast open-source, MIT license
    if 'HiGHS' in available:
        if msg:
            print("[solver] Using HiGHS (fast open-source MILP solver)")
        return pulp.HiGHS(msg=msg, timeLimit=timeLimit)

    # PULP_CBC_CMD: fallback (always available)
    if msg:
        print("[solver] Using PULP_CBC_CMD (fallback)")
    return pulp.PULP_CBC_CMD(msg=msg, timeLimit=timeLimit)
