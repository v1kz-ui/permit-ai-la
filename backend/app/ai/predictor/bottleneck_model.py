"""XGBoost-based bottleneck prediction model.

Predicts days-to-completion for each clearance based on project features.
Flags clearances likely to become bottlenecks (predicted days > threshold).

The model is trained on historical fire-rebuild permit data (3,000+ permits).
Until sufficient training data is available, a heuristic baseline is used.
"""

import json
from pathlib import Path

import structlog

logger = structlog.get_logger()

MODEL_PATH = Path(__file__).parent / "trained_model.joblib"

# Heuristic baseline: typical processing days by department and clearance type
# Derived from LADBS historical data for fire-rebuild permits
BASELINE_DAYS = {
    # (department, clearance_type_pattern) -> typical days
    ("ladbs", "building_permit"): 21,
    ("ladbs", "zoning_clearance"): 14,
    ("ladbs", "electrical_permit"): 7,
    ("ladbs", "plumbing_permit"): 7,
    ("ladbs", "mechanical_permit"): 7,
    ("ladbs", "grading_permit"): 30,
    ("ladbs", "hillside"): 28,
    ("ladbs", "geotechnical"): 25,
    ("dcp", "zoning_clearance"): 14,
    ("dcp", "coastal_development_permit"): 45,
    ("dcp", "specific_plan"): 21,
    ("dcp", "hpoz"): 35,
    ("dcp", "historic"): 30,
    ("boe", "sewer"): 14,
    ("boe", "street"): 10,
    ("boe", "haul_route"): 14,
    ("boe", "hillside"): 21,
    ("boe", "flood"): 18,
    ("lafd", "fire_life_safety"): 14,
    ("lafd", "brush_clearance"): 10,
    ("lafd", "fire_flow"): 12,
    ("lafd", "fire_hazard"): 14,
    ("ladwp", "water_service"): 10,
    ("ladwp", "power_service"): 10,
    ("ladwp", "power/water"): 10,
    ("lasan", "lid_compliance"): 14,
    ("lasan", "sanitation"): 12,
    ("lahd", "rent_stabilization"): 7,
    ("la_county", "geotechnical_review"): 21,
    ("la_county", "flood_zone_review"): 18,
}

# Multipliers for overlays that increase processing time
OVERLAY_MULTIPLIERS = {
    "is_coastal_zone": 1.3,
    "is_hillside": 1.25,
    "is_very_high_fire_severity": 1.15,
    "is_historic": 1.2,
    "is_flood_zone": 1.1,
    "is_geological_hazard": 1.2,
}

# Seasonal adjustment: certain months are slower due to volume or holidays
SEASONAL_FACTORS = {
    1: 1.15,   # January - post-fire surge
    2: 1.2,    # February - peak fire-rebuild submissions
    3: 1.15,   # March - still elevated
    4: 1.1,
    5: 1.05,
    6: 1.0,    # Summer baseline
    7: 1.0,
    8: 1.0,
    9: 1.05,
    10: 1.05,
    11: 1.1,   # Holiday slowdown
    12: 1.2,   # Holiday slowdown
}

BOTTLENECK_THRESHOLD_DAYS = 28  # Flag as bottleneck if predicted > this


def predict_clearance_days(
    department: str,
    clearance_type: str,
    parcel_data: dict,
    month: int | None = None,
) -> dict:
    """Predict processing days for a single clearance.

    Uses XGBoost model if trained, otherwise falls back to heuristic baseline.
    """
    # Try to use trained model
    model_prediction = _try_model_prediction(department, clearance_type, parcel_data)
    if model_prediction is not None:
        return model_prediction

    # Heuristic fallback
    return _heuristic_prediction(department, clearance_type, parcel_data, month)


def _try_model_prediction(department: str, clearance_type: str, parcel_data: dict) -> dict | None:
    """Attempt prediction with trained XGBoost model."""
    if not MODEL_PATH.exists():
        return None

    try:
        import joblib
        import numpy as np

        model = joblib.load(MODEL_PATH)
        features = _extract_features(department, clearance_type, parcel_data)
        feature_array = np.array([list(features.values())])
        predicted_days = int(model.predict(feature_array)[0])

        return {
            "predicted_days": predicted_days,
            "is_bottleneck": predicted_days > BOTTLENECK_THRESHOLD_DAYS,
            "confidence": 0.85,
            "method": "xgboost",
        }
    except Exception as e:
        logger.warning("model_prediction_failed", error=str(e))
        return None


def _heuristic_prediction(
    department: str,
    clearance_type: str,
    parcel_data: dict,
    month: int | None = None,
) -> dict:
    """Heuristic baseline prediction using department averages and overlay multipliers."""
    dept_lower = department.lower().replace(" ", "_")
    type_lower = clearance_type.lower().replace(" ", "_")

    # Find best matching baseline
    base_days = 14  # default
    for (d, t), days in BASELINE_DAYS.items():
        if d == dept_lower and t in type_lower:
            base_days = days
            break
    else:
        # Try department-only match
        for (d, t), days in BASELINE_DAYS.items():
            if d == dept_lower:
                base_days = days
                break

    # Apply overlay multipliers
    multiplier = 1.0
    for flag, mult in OVERLAY_MULTIPLIERS.items():
        if parcel_data.get(flag, False):
            multiplier *= mult

    # Apply seasonal factor
    if month and month in SEASONAL_FACTORS:
        multiplier *= SEASONAL_FACTORS[month]

    predicted_days = int(base_days * multiplier)

    return {
        "predicted_days": predicted_days,
        "is_bottleneck": predicted_days > BOTTLENECK_THRESHOLD_DAYS,
        "confidence": 0.6,
        "method": "heuristic",
    }


def predict_project_timeline(
    clearances: list[dict],
    parcel_data: dict,
    month: int | None = None,
) -> dict:
    """Predict total project timeline considering all clearances.

    Some clearances run in parallel; others are sequential dependencies.
    """
    # Parallel groups: clearances within the same department run sequentially,
    # but different departments process in parallel
    department_timelines: dict[str, int] = {}
    bottlenecks = []

    for clearance in clearances:
        dept = clearance.get("department", "unknown")
        ctype = clearance.get("clearance_type", "unknown")

        prediction = predict_clearance_days(dept, ctype, parcel_data, month)

        # Accumulate sequential time within each department
        department_timelines[dept] = department_timelines.get(dept, 0) + prediction["predicted_days"]

        if prediction["is_bottleneck"]:
            bottlenecks.append({
                "department": dept,
                "clearance_type": ctype,
                "predicted_days": prediction["predicted_days"],
            })

        # Store prediction back on clearance dict
        clearance["predicted_days"] = prediction["predicted_days"]
        clearance["is_bottleneck"] = prediction["is_bottleneck"]

    # Total timeline is the longest department path (critical path)
    critical_path_days = max(department_timelines.values()) if department_timelines else 0

    # Add fixed overhead: application processing (5 days) + final review (3 days)
    total_days = critical_path_days + 8

    critical_department = max(department_timelines, key=department_timelines.get) if department_timelines else None

    return {
        "total_predicted_days": total_days,
        "critical_path_days": critical_path_days,
        "critical_department": critical_department,
        "department_timelines": department_timelines,
        "bottlenecks": bottlenecks,
        "bottleneck_count": len(bottlenecks),
    }


def _extract_features(department: str, clearance_type: str, parcel_data: dict) -> dict:
    """Extract numerical features for the XGBoost model."""
    dept_encoding = {
        "ladbs": 0, "dcp": 1, "boe": 2, "lafd": 3,
        "ladwp": 4, "lasan": 5, "lahd": 6, "la_county": 7,
    }

    return {
        "department_encoded": dept_encoding.get(department.lower(), 8),
        "is_coastal_zone": int(parcel_data.get("is_coastal_zone", False)),
        "is_hillside": int(parcel_data.get("is_hillside", False)),
        "is_very_high_fire_severity": int(parcel_data.get("is_very_high_fire_severity", False)),
        "is_historic": int(parcel_data.get("is_historic", False)),
        "is_flood_zone": int(parcel_data.get("is_flood_zone", False)),
        "is_geological_hazard": int(parcel_data.get("is_geological_hazard", False)),
        "lot_area_sqft": parcel_data.get("lot_area_sqft", 5000),
        "proposed_sqft": parcel_data.get("proposed_sqft", 2000),
        "stories": parcel_data.get("stories", 1),
    }
