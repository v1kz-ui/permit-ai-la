---
sidebar_position: 3
title: Bottleneck Prediction
---

# Bottleneck Prediction

The bottleneck predictor estimates days-to-completion for each clearance and flags likely delays.

**File:** `backend/app/ai/predictor/bottleneck_model.py`

## Two-Tier Approach

### Tier 1: XGBoost Model (if trained)
- Trained model loaded from `trained_model.joblib`
- Confidence: 0.85
- Features: department (encoded), overlay flags, lot area, proposed sqft, stories

### Tier 2: Heuristic Baseline (always available)
- Lookup tables by department + clearance type
- Confidence: 0.6
- Overlay multipliers and seasonal adjustments applied

## Baseline Days by Department

| Department | Clearance | Base Days |
|-----------|-----------|-----------|
| LADBS | Building permit | 21 |
| LADBS | Zoning clearance | 14 |
| LADBS | Grading permit | 30 |
| DCP | Coastal development | 45 |
| DCP | HPOZ review | 35 |
| DCP | Specific plan | 21 |
| LAFD | Fire/life safety | 14 |
| LAFD | Brush clearance | 10 |
| BOE | Sewer connection | 14 |
| LADWP | Water/power service | 14 |
| LASAN | LID compliance | 10 |
| Default | Any other | 14 |

## Overlay Multipliers

These compound (multiply together) when a parcel has multiple overlays:

| Overlay | Multiplier | Rationale |
|---------|-----------|-----------|
| Coastal Zone | 1.3x | Additional Coastal Commission review |
| Hillside | 1.25x | Geotechnical and drainage requirements |
| Very High Fire Severity | 1.15x | Enhanced fire safety review |
| Historic | 1.2x | Preservation board review |
| Flood Zone | 1.1x | Additional drainage review |
| Geological Hazard | 1.2x | Soils and stability analysis |

Example: A coastal + hillside parcel = 1.3 x 1.25 = 1.625x baseline days.

## Seasonal Adjustments

| Month | Factor | Reason |
|-------|--------|--------|
| January - March | 1.15 - 1.20x | Post-fire surge in applications |
| April - May | 1.05x | Slightly above baseline |
| June - August | 1.0x | Baseline |
| September - October | 1.05x | Slightly above baseline |
| November - December | 1.10 - 1.20x | Holiday slowdowns |

## Bottleneck Threshold

A clearance is flagged as a bottleneck when `predicted_days > 28`. Bottlenecked clearances appear with red borders and animated indicators on the dashboard.

## Timeline Prediction

The timeline predictor uses the critical path method:
1. Group clearances by department
2. Within each department: clearances are sequential
3. Across departments: clearances are parallel
4. **Critical path** = longest department timeline
5. **Total** = critical path + 8 days overhead (5 for application processing + 3 for final review)
