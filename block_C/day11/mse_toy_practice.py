#!/usr/bin/env python3
"""D11 classroom-only MSE; NOT a trained AE or real robot sensor stream."""
FEATURE_NAMES = ("current_a_mean", "current_a_std", "torque_nm_mean",
                 "torque_nm_std", "accel_mps2_mean", "accel_mps2_std")
TOY_THRESHOLD = 0.5

def mse(x, x_hat):
    if len(x) != 6 or len(x_hat) != 6:
        raise ValueError("D11_TOY_FEATURE_COUNT_MUST_BE_6")
    return sum((a - b) ** 2 for a, b in zip(x, x_hat)) / 6

def decide(quality, x, x_hat):
    if quality != "VALID":
        return "INSUFFICIENT_DATA", None
    score = mse(x, x_hat)
    return ("WARNING" if score > TOY_THRESHOLD else "NORMAL"), score

def main():
    x = [0.0] * 6
    cases = (
        ("normal", "VALID", [0.1, -0.1, 0.1, -0.1, 0.1, -0.1]),
        ("anomaly", "VALID", [1.0] * 6),
        ("missing", "INSUFFICIENT_DATA", [1.0] * 6),
    )
    print("D11_TOY_DEMO_BEGIN source=HAND_CRAFTED_NOT_MODEL_PREDICTION")
    for name, quality, xhat in cases:
        prediction, score = decide(quality, x, xhat)
        display = "UNSCORED" if score is None else f"{score:.6f}"
        print(f"D11_TOY case={name} mse={display} threshold={TOY_THRESHOLD:.6f} prediction={prediction}")
    print("D11_TOY_DEMO_PASS only_classroom_math=true model_training=false robot_control=false")

if __name__ == "__main__":
    main()
