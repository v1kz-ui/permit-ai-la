"""Train an XGBoost bottleneck-prediction model on synthetic fire-rebuild permit data.

Generates 5,000 realistic training samples, fits an XGBRegressor, reports test
metrics, and saves the artefacts so that bottleneck_model.py can load them.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR.parent / "app" / "ai" / "predictor"
MODEL_PATH = MODEL_DIR / "trained_model.joblib"
FEATURES_PATH = MODEL_DIR / "model_features.json"

# ---------------------------------------------------------------------------
# Feature schema (must match _extract_features in bottleneck_model.py)
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "department_encoded",       # 0-7
    "is_coastal_zone",          # 0/1
    "is_hillside",              # 0/1
    "is_very_high_fire_severity",  # 0/1
    "is_historic",              # 0/1
    "is_flood_zone",            # 0/1
    "is_geological_hazard",     # 0/1
    "lot_area_sqft",            # 2000-15000
    "proposed_sqft",            # 800-6000
    "stories",                  # 1-3
    "month",                    # 1-12
]

# ---------------------------------------------------------------------------
# Baseline days per department (aligned with BASELINE_DAYS in bottleneck_model.py)
# ---------------------------------------------------------------------------
DEPT_BASELINE = {
    0: 21,   # ladbs
    1: 30,   # dcp  (midpoint of 14-45 range)
    2: 14,   # boe
    3: 14,   # lafd
    4: 10,   # ladwp
    5: 14,   # lasan
    6: 7,    # lahd
    7: 21,   # la_county
}

# Overlay multipliers (10-30% each)
OVERLAY_COLS = [
    "is_coastal_zone",
    "is_hillside",
    "is_very_high_fire_severity",
    "is_historic",
    "is_flood_zone",
    "is_geological_hazard",
]
OVERLAY_MULTIPLIERS = {
    "is_coastal_zone": 1.30,
    "is_hillside": 1.25,
    "is_very_high_fire_severity": 1.15,
    "is_historic": 1.20,
    "is_flood_zone": 1.10,
    "is_geological_hazard": 1.20,
}

# Seasonal factors (Jan/Feb/Dec add 15-20%)
SEASONAL_FACTORS = {
    1: 1.15,
    2: 1.20,
    3: 1.15,
    4: 1.10,
    5: 1.05,
    6: 1.00,
    7: 1.00,
    8: 1.00,
    9: 1.05,
    10: 1.05,
    11: 1.10,
    12: 1.20,
}

N_SAMPLES = 5_000
NOISE_STD = 5.0
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_samples(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Return (X, y) where X has shape (n, len(FEATURE_NAMES)) and y is integer days."""

    dept = rng.integers(0, 8, size=n)               # 0-7

    # Binary overlay flags – realistic sparsity for LA fire-rebuild permits
    is_coastal   = rng.random(n) < 0.15
    is_hillside  = rng.random(n) < 0.35
    is_vhfhsz    = rng.random(n) < 0.60             # Very High Fire Hazard Severity Zone
    is_historic  = rng.random(n) < 0.10
    is_flood     = rng.random(n) < 0.20
    is_geo       = rng.random(n) < 0.25

    lot_area  = rng.integers(2_000, 15_001, size=n).astype(float)
    prop_sqft = rng.integers(800,   6_001,  size=n).astype(float)
    stories   = rng.integers(1, 4, size=n)           # 1-3
    month     = rng.integers(1, 13, size=n)          # 1-12

    # --- Compute target (actual_days) from the same rules as the heuristic ---
    base = np.array([DEPT_BASELINE[int(d)] for d in dept], dtype=float)

    mult = np.ones(n)
    mult[is_coastal]  *= OVERLAY_MULTIPLIERS["is_coastal_zone"]
    mult[is_hillside] *= OVERLAY_MULTIPLIERS["is_hillside"]
    mult[is_vhfhsz]   *= OVERLAY_MULTIPLIERS["is_very_high_fire_severity"]
    mult[is_historic] *= OVERLAY_MULTIPLIERS["is_historic"]
    mult[is_flood]    *= OVERLAY_MULTIPLIERS["is_flood_zone"]
    mult[is_geo]      *= OVERLAY_MULTIPLIERS["is_geological_hazard"]

    seasonal = np.array([SEASONAL_FACTORS[int(m)] for m in month])
    mult *= seasonal

    # Slight size effect: larger buildings take fractionally longer
    size_factor = 1.0 + (prop_sqft - 800) / (6_000 - 800) * 0.10
    mult *= size_factor

    actual_days_float = base * mult + rng.normal(0, NOISE_STD, size=n)
    actual_days = np.clip(actual_days_float, 1, None).astype(int)

    X = np.column_stack([
        dept,
        is_coastal.astype(int),
        is_hillside.astype(int),
        is_vhfhsz.astype(int),
        is_historic.astype(int),
        is_flood.astype(int),
        is_geo.astype(int),
        lot_area,
        prop_sqft,
        stories,
        month,
    ])

    return X, actual_days


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(X_train: np.ndarray, y_train: np.ndarray) -> XGBRegressor:
    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_SEED,
        n_jobs=-1,
        verbosity=0,
    )
    model.fit(X_train, y_train)
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def report_metrics(model: XGBRegressor, X_test: np.ndarray, y_test: np.ndarray) -> None:
    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    print(f"  MAE  (test): {mae:.2f} days")
    print(f"  RMSE (test): {rmse:.2f} days")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_artefacts(model: XGBRegressor) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    print(f"  Model saved → {MODEL_PATH}")

    with open(FEATURES_PATH, "w", encoding="utf-8") as fh:
        json.dump(FEATURE_NAMES, fh, indent=2)
    print(f"  Feature names saved → {FEATURES_PATH}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== PermitAI LA – Bottleneck Model Training ===")
    print(f"Generating {N_SAMPLES:,} synthetic samples …")

    rng = np.random.default_rng(RANDOM_SEED)
    X, y = generate_samples(N_SAMPLES, rng)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=RANDOM_SEED
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    print("Training XGBRegressor …")
    model = train(X_train, y_train)
    print("Training complete.")

    print("Evaluating on held-out test set:")
    report_metrics(model, X_test, y_test)

    print("Saving artefacts:")
    save_artefacts(model)

    print("Done.")


if __name__ == "__main__":
    main()
