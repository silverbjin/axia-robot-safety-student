"""OPTIONAL real YOLO CPU demo; local licensed model/image ONLY, no auto download.

Never called by core D04/D05 course tests or any robot command path.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Optional local YOLO image demo (NO ROS/Gazebo)")
    p.add_argument("--model", type=Path, required=True, help="already-cached licensed *.pt")
    p.add_argument("--image", type=Path, required=True, help="licensed local image file")
    p.add_argument("--out", type=Path, required=True, help="new output directory")
    args = p.parse_args(argv)
    for source in (args.model, args.image):
        if not source.is_file() or source.is_symlink():
            p.error(f"Local regular file required (no network): {source}")
    if args.out.exists():
        p.error("Output directory must not exist")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        p.error(f"Preinstalled ultralytics required; no auto install: {exc}")
    model = YOLO(str(args.model))
    predictions = model.predict(source=str(args.image), device="cpu", verbose=False, save=False)
    if len(predictions) != 1:
        raise RuntimeError("Exactly one image result required")
    result = predictions[0]
    h, w = result.orig_shape
    records = []
    for i, (cls_id, score, corners) in enumerate(zip(result.boxes.cls.cpu().tolist(),
                    result.boxes.conf.cpu().tolist(), result.boxes.xyxy.cpu().tolist())):
        if str(model.names[int(cls_id)]).lower() != "person":
            continue
        x1, y1, x2, y2 = corners
        records.append({"frame_id": "instructor-local-image", "stamp_s": "NA",
                        "category": "person", "confidence": score,
                        "x1": max(0, min(w, int(x1))), "y1": max(0, min(h, int(y1))),
                        "x2": max(0, min(w, int(x2))), "y2": max(0, min(h, int(y2))),
                        "image_width": w, "image_height": h})
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / "detections.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["frame_id", "stamp_s", "category", "confidence",
                    "x1", "y1", "x2", "y2", "image_width", "image_height"])
        writer.writeheader()
        writer.writerows(records)
    metadata = {"image_sha256": hashlib.sha256(args.image.read_bytes()).hexdigest(),
                "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
                "detections": len(records), "level": "LOCAL_YOLO_CPU_ONLY",
                "ros_verified": False, "gazebo_verified": False}
    (args.out / "run_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"LOCAL_YOLO_CPU_ONLY: {len(records)} persons; output={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
