"""G07 read-only Guard timer evidence selection; no safety policy changes.

FV17z53O showed the actual Owner Guard was alive, forwarding commands and
canceling its Goal, but did not export cm_age_sec/guard_ever_moved. The strict
post-run verifier required fields only emitted under GITHUB_ACTIONS, making
WSL2 Owner impossible to verify regardless of its actual physical behavior.
This pure contract selects diagnostics only, never authorizes a Goal.
"""

def internal_timing_evidence_enabled(env):
    if env.get("AXIA_P0_SIM_ONLY") != "1":
        return False
    ci = (env.get("GITHUB_ACTIONS") == "true"
          and env.get("AXIA_G07_TASK03_FORMAL_CI") == "1")
    owner = (env.get("GITHUB_ACTIONS") != "true"
             and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "0"
             and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3") == "1"
             and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1")
    return ci or owner
