"""Conservative P0 occupancy-map pose checker and reproducible diagnostics.

Simulation only. A cell is acceptable only when its OccupancyGrid value is
exactly 0; unknown (-1) or any nonzero occupancy remain blocked.
"""
from __future__ import annotations
import math



def _lower_cell_at_float32_boundary(local_min: float, resolution: float) -> int:
    """Normalize only a submicrometer float32 artifact at a *lower* cell edge.

    ROS OccupancyGrid.info.resolution is float32: 0.05 arrives as
    0.05000000074505806, so 7.65 / resolution becomes 152.99999772.
    A 0.5-micrometer physical cap plus 1e-5-cell cap disallows large shifts.
    Other boundaries retain original conservative floor semantics.
    """
    ratio = local_min / resolution
    nearest = round(ratio)
    tolerance_cells = min(1e-5, 5e-7 / resolution)
    if abs(ratio - nearest) <= tolerance_cells:
        return int(nearest)
    return math.floor(ratio)


def inspect_candidate_cells(*, x: float, y: float, radius: float,
                            width: int, height: int, resolution: float,
                            origin_x: float, origin_y: float, origin_yaw: float,
                            data: list[int]) -> dict:
    """Inspect the exact rectangular cell footprint used for the safety gate.

    Bounded output (up to 12 unsafe samples) prevents dumping the entire map.
    Never publishes pose, velocity, or action.
    """
    report = {
        "grid_bounds": None, "local_xy": None, "total_cells": 0,
        "value_counts": {}, "first_unsafe_cells": [], "reasons": [],
    }
    scalars = (x, y, radius, resolution, origin_x, origin_y, origin_yaw)
    if (any(type(v) not in (float, int) or not math.isfinite(v)
            for v in scalars)
            or radius <= 0 or resolution <= 0
            or type(width) is not int or type(height) is not int
            or width <= 0 or height <= 0
            or not isinstance(data, (list, tuple)) or len(data) != width * height):
        report["reasons"] = ["invalid map metadata or candidate pose"]
        return report

    delta_x, delta_y = x - origin_x, y - origin_y
    cosine, sine = math.cos(origin_yaw), math.sin(origin_yaw)
    local_x = cosine * delta_x + sine * delta_y
    local_y = -sine * delta_x + cosine * delta_y
    report["local_xy"] = [local_x, local_y]
    left = _lower_cell_at_float32_boundary(local_x - radius, resolution)
    right = math.floor((local_x + radius) / resolution)
    bottom = _lower_cell_at_float32_boundary(local_y - radius, resolution)
    top = math.floor((local_y + radius) / resolution)
    report["grid_bounds"] = [left, right, bottom, top]

    if min(left, bottom) < 0 or right >= width or top >= height:
        report["reasons"] = ["candidate footprint intersects map border or lies outside map"]
        return report

    for j in range(bottom, top + 1):
        for i in range(left, right + 1):
            cell = data[j * width + i]
            key = str(cell)
            report["value_counts"][key] = report["value_counts"].get(key, 0) + 1
            report["total_cells"] += 1
            if type(cell) is not int or cell != 0:
                if len(report["first_unsafe_cells"]) < 12:
                    report["first_unsafe_cells"].append({"i": i, "j": j, "value": cell})

    if report["first_unsafe_cells"]:
        report["reasons"] = ["candidate footprint intersects occupied or unknown map cell"]
    return report


def check_disk_free(*, x: float, y: float, radius: float,
                    width: int, height: int, resolution: float,
                    origin_x: float, origin_y: float, origin_yaw: float,
                    data: list[int]) -> list[str]:
    """Compatibility API; use exactly the same bounds and cells as diagnostic."""
    return inspect_candidate_cells(
        x=x, y=y, radius=radius,
        width=width, height=height, resolution=resolution,
        origin_x=origin_x, origin_y=origin_y, origin_yaw=origin_yaw,
        data=data,
    )["reasons"]
