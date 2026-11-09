"""Student TODO: two pure functions only; no ROS /cmd_vel publication."""


def select_person(detections: list[dict], min_confidence: float = 0.5) -> dict | None:
    """D04: validate bbox/confidence; return highest-confidence valid person or None.

    Inputs may contain CSV numeric strings. Bounding boxes are integer [x1,y1,x2,y2)
    pixels; coordinates must remain inside the image. Reject malformed input.
    """
    # TODO(D04): ignore non-person labels, reject invalid person records,
    # enforce score >= threshold and stable highest-score selection.
    raise NotImplementedError("TODO_D04_SELECT_PERSON")


def measure_person_range(depth_m: list[list], bbox: dict,
                         frame_stamp_s: float, depth_stamp_s: float,
                         max_skew_s: float = 0.05) -> float | None:
    """D05: median depth (metres) of bbox ROI; unknown -> None.

    Reject malformed ROI/grid/timestamps. For valid grids skip zero, NaN, Inf,
    and readings outside [0.15, 8.0] metres. At least half of ROI pixels must
    be valid, and abs(RGB stamp - depth stamp) <= max_skew_s.
    """
    # TODO(D05): validate stamps + rectangular depth grid; compute median of
    # valid in-bounds ROI pixels, return None on stale or insufficient coverage.
    raise NotImplementedError("TODO_D05_PERSON_RANGE")
