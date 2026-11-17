"""Read-only H01 free-space global Costmap baseline stability before intrusion.

Actual public Gazebo L2 #43601515742: the inner lethal-cell count changed
42 -> 46 after removal while ROI was clean. Two fresh free Grid stamps
were observed, but the *positions* of their lethal cells were not compared.
This module detects first native free-map variation, never claims source
causality, clearing, motor permission, or certified E-Stop.
"""
from __future__ import annotations
import math
try:
    from .d07_h01_costmap_drift import _read
except ImportError:
    from d07_h01_costmap_drift import _read


def assess_two_real_free_grid_baselines(first, second, *, obstacle_map_xy):
    """Compare lethal cell identities, not just counts or byte equality."""
    hold={
        "schema":"axia_d07_h01_free_grid_baseline_v1",
        "status":"FREE_BASELINE_PROVENANCE_HOLD_NO_GOAL",
        "reason":"TWO_GENUINE_ORDERED_FREE_COSTMAP_GRIDS_NOT_PROVEN",
        "first_invalid_boundary":"PRE_INTRUSION_FREE_GRID_PROVENANCE",
        "goal_sent":False,"motion_admitted":False,
        "obstacle_layer_clearing_proven":False,
        "spatial_restoration_proven":False,"certified_estop":False,
    }
    # Distinguish real first provenance boundary. The prior L2
    # #43669666508 failed before any physical intrusion but only reported
    # a generic RuntimeError; never guess clearing/root cause from it.
    if (not isinstance(first,dict) or not isinstance(second,dict)):
        return {**hold,"reason":"INVALID_REAL_COSTMAP_SOURCE"}
    if (first.get("frame")!="map" or second.get("frame")!="map"):
        return {**hold,"reason":"MISMATCHED_REAL_FREE_GRID_METADATA"}
    a,b=_read(first),_read(second)
    if a is None or b is None:
        return {**hold,"reason":"INVALID_REAL_COSTMAP_SOURCE"}
    if a["key"]!=b["key"]:
        return {**hold,"reason":"MISMATCHED_REAL_FREE_GRID_METADATA"}
    if not (0<a["stamp"]<b["stamp"] and
            0<a["received"]<b["received"]):
        return {**hold,"reason":"NON_MONOTONIC_FREE_GRID_STAMP_OR_RECEIPT"}
    if (not isinstance(obstacle_map_xy,(tuple,list))
        or len(obstacle_map_xy)!=2
        or any(type(x) not in (int,float) or not math.isfinite(x)
               for x in obstacle_map_xy)):
        return {**hold,"reason":"INVALID_PHYSICAL_OBSTACLE_MAP_POSITION"}
    width,height,res,origin=a["key"][:4]
    x,y=obstacle_map_xy
    if (not origin[0]<=x<origin[0]+width*res or
        not origin[1]<=y<origin[1]+height*res):
        return {**hold,"reason":"PHYSICAL_ROI_OUTSIDE_REAL_COSTMAP"}
    # Exclude unknown/no-information cells from a "stable" conclusion:
    # two free baselines cannot establish the same occupancy if the
    # source cell in the physical obstacle neighborhood was unknown.
    near=set()
    for row in range(height):
        cy=origin[1]+(row+.5)*res
        if abs(cy-y)>.75:
            continue
        for col in range(width):
            cx=origin[0]+(col+.5)*res
            if (cx-x)**2+(cy-y)**2<=.75**2:
                near.add(row*width+col)
    if not near:
        return {**hold,"reason":"PHYSICAL_ROI_OUTSIDE_REAL_COSTMAP"}
    unknown=sorted(i for i in near
                   if min(a["cells"][i],b["cells"][i])<0)
    if unknown:
        return {**hold,
                "reason":"UNKNOWN_COST_INSIDE_PHYSICAL_ROI",
                "first_invalid_boundary":"PRE_INTRUSION_UNKNOWN_COST_CELL",
                "first_unknown_cell_index":unknown[0],
                "unknown_cell_count":len(unknown),
                "source_grid_stamps":[a["stamp"],b["stamp"]]}
    # Official Nav2 Jazzy raw: 254 LETHAL -> published 100.
    # Raw 253 INSCRIBED_INFLATED -> published 99; 95..99 are high
    # NONLETHAL costs. Retain their dynamics as a separate risk signal,
    # never label natural Inflation boundary motion a genuine lethal cell.
    a_lethal={i for i in near if a["cells"][i]==100}
    b_lethal={i for i in near if b["cells"][i]==100}
    a_inscribed={i for i in near if a["cells"][i]==99}
    b_inscribed={i for i in near if b["cells"][i]==99}
    high_changed={i for i in near
                  if a["cells"][i]!=b["cells"][i]
                  and (95<=a["cells"][i]<100 or 95<=b["cells"][i]<100)}
    new=b_lethal-a_lethal
    removed=a_lethal-b_lethal
    status=("TWO_FREE_BASELINE_LETHAL_CELLS_STABLE_NO_GOAL"
            if not new and not removed else
            "FREE_BASELINE_LETHAL_VARIATION_HOLD_NO_GOAL")
    return {
        **hold,
        "status":status,
        "reason":("TWO_PRE_INTRUSION_LETHAL_CELL_SETS_EQUAL"
                  if not new and not removed else
                  "FREE_MAP_LETHAL_CELL_POSITIONS_NOT_STABLE"),
        "first_invalid_boundary":(
            None if not new and not removed else
            "PRE_INTRUSION_BASELINE_LETHAL_VARIATION"),
        "before_lethal_near":len(a_lethal),
        "later_lethal_near":len(b_lethal),
        "new_lethal_cells_near":len(new),
        "removed_lethal_cells_near":len(removed),
        "first_new_lethal_indices":sorted(new)[:12],
        "first_removed_lethal_indices":sorted(removed)[:12],
        "new_inscribed_inflation_cells_near":len(b_inscribed-a_inscribed),
        "removed_inscribed_inflation_cells_near":len(a_inscribed-b_inscribed),
        "nonlethal_high_cost_variation_observed":bool(high_changed),
        "high_nonlethal_changed_cell_count":len(high_changed),
        "first_high_nonlethal_changed_indices":sorted(high_changed)[:12],
        "full_grid_identical":a["cells"]==b["cells"],
        "source_session_id":a["key"][-1],
        "source_grid_stamps":[a["stamp"],b["stamp"]],
        "goal_sent":False,"motion_admitted":False,
        "obstacle_layer_clearing_proven":False,
        "spatial_restoration_proven":False,
    }


def choose_bounded_stable_free_baselines(
        rows, *, obstacle_map_xy):
    """Find a consecutive truly stable free-grid pair within SIX updates.

    A free-map lethal flicker does not authorize movement and is not proof of
    physical obstacle clearing failure. Never discard or hide the first
    flicker: preserve its actual indices for CI and Owner evidence. If no
    stable pair occurs in the bounded six fresh native maps, HOLD.
    """
    hold={
        "status":"FREE_BASELINE_PROVENANCE_HOLD_NO_GOAL",
        "reason":"BOUNDED_REAL_FREE_GRIDS_NOT_VERIFIED",
        "first_invalid_boundary":"PRE_INTRUSION_FREE_GRID_PROVENANCE",
        "goal_sent":False,"motion_admitted":False,
        "obstacle_layer_clearing_proven":False,
        "source_causality_proven":False,
    }
    if (not isinstance(rows,(tuple,list)) or not 2<=len(rows)<=6):
        return hold
    first_variation=None
    latest_pair=None
    high_nonlethal_variation_any=False
    for idx in range(len(rows)-1):
        candidate=assess_two_real_free_grid_baselines(
            rows[idx],rows[idx+1],obstacle_map_xy=obstacle_map_xy)
        if candidate["status"]=="FREE_BASELINE_PROVENANCE_HOLD_NO_GOAL":
            return {**hold,"reason":"PRE_INTRUSION_SAME_SESSION_GRID_ORDER_INVALID",
                    "failed_pair_indices":[idx,idx+1]}
        high_nonlethal_variation_any=(
            high_nonlethal_variation_any or
            candidate.get("nonlethal_high_cost_variation_observed") is True)
        if candidate["status"]=="TWO_FREE_BASELINE_LETHAL_CELLS_STABLE_NO_GOAL":
            # A previous stable pair is superseded when a newer real Grid
            # changes. Accept ONLY the most recent consecutive pair.
            latest_pair=(idx,candidate)
            continue
        latest_pair=None
        if first_variation is None:
            first_variation={
                "first_invalid_boundary":"PRE_INTRUSION_BASELINE_LETHAL_VARIATION",
                "pair_indices":[idx,idx+1],
                "before_lethal_near":candidate["before_lethal_near"],
                "later_lethal_near":candidate["later_lethal_near"],
                "new_lethal_cells_near":candidate["new_lethal_cells_near"],
                "removed_lethal_cells_near":candidate["removed_lethal_cells_near"],
                "first_new_lethal_indices":candidate["first_new_lethal_indices"],
                "first_removed_lethal_indices":candidate["first_removed_lethal_indices"],
                "source_grid_stamps":candidate["source_grid_stamps"],
            }
    if latest_pair is not None:
        idx,candidate=latest_pair
        return {
            **hold,
            "status":"STABLE_FREE_GRID_PAIR_SELECTED_NO_GOAL",
            "reason":"LATEST_TWO_NATIVE_FREE_GRIDS_SAME_LETHAL_SET",
            "first_invalid_boundary":None,
            "pair_indices":[idx,idx+1],
            "selected_grid_stamps":candidate["source_grid_stamps"],
            "first_observed_variation":first_variation,
            "free_grid_samples_considered":len(rows),
            "nonlethal_high_cost_variation_observed":high_nonlethal_variation_any,
            "motion_admitted":False,"goal_sent":False,
            "obstacle_layer_clearing_proven":False,
        }
    return {
        **hold,
        "status":("UNSTABLE_FREE_GRID_BASELINE_HOLD_NO_GOAL"
                  if len(rows)==6 else
                  "AWAITING_REAL_FREE_GRID_STABILITY_NO_GOAL"),
        "reason":"PRE_INTRUSION_FREE_MAP_LETHAL_CELLS_CONTINUE_TO_VARY",
        "first_invalid_boundary":"PRE_INTRUSION_BASELINE_LETHAL_VARIATION",
        "first_observed_variation":first_variation,
        "free_grid_samples_considered":len(rows),
        "nonlethal_high_cost_variation_observed":high_nonlethal_variation_any,
        "goal_sent":False,"motion_admitted":False,
    }
