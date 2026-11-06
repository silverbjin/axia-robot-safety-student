# AXIA Robot Safety — Student TODO (public independent repository)

This repository is a standalone **student exercise**, not a copy of the instructor's private answer package. It has zero dependency on any private repository or token and intentionally includes **no correct solution**.

## Learning target

Design an abstract **SW Stop latch** that denies movement in BOOT_SAFE and after a protective stop, keeps fault-cleared and operator rearm separate, and never automatically resumes a previous Goal. This is a Python-only model, not a ROS component or certified E-Stop.

## Exercises

- Implement the four `NotImplementedError` TODO methods in `axia_student/stop_latch.py`.
- Run `python3 -m pip install pytest==8.3.5` then `python3 -m pytest -q tests/test_stop_latch_behavior.py`.
- In the supplied skeleton, the **behavior tests intentionally fail** (RED). Implement GREEN, then REFACTOR and request REVIEW.
- The automatic GitHub Actions workflow verifies **only scaffold imports**, not exercise correctness. A green scaffold is **not** exercise acceptance.

## Safety and privacy

Do not connect this code to physical robot actuators, live `/cmd_vel`, or claim certified hardware E-Stop. Do not copy instructor solutions or hidden tests into this public repository. The learning contract is intentionally narrow; real Supervisor/Nav2 integration remains private and separately verified.
