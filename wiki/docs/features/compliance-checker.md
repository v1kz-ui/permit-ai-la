---
sidebar_position: 7
title: Compliance Checker
---

# Compliance Checker

Validates that projects meet pathway requirements and clearances are in the correct order.

## Features

### Rule Validation
Checks each project against its declared pathway rules:
- Is the sqft increase within EO1/EO8 limits?
- Are all required clearances present?
- Are overlay-specific reviews included?

### Sequence Validation
Verifies clearance ordering dependencies:
- Geotechnical review before grading permit
- Zoning clearance before building permit
- Fire safety before final inspection

## Dashboard Page

The compliance page (`/compliance`) provides:

1. **Project search** -- Enter project ID or address
2. **Quick select** -- 5 recent projects with pathway badges
3. **Results summary** -- Pass/fail count and pathway
4. **Blocking issues** -- Critical problems that prevent permit issuance (red cards)
5. **Warnings** -- Non-blocking issues to address (amber cards)
6. **Rule results** -- Individual rules with PASS/FAIL badges and severity

## API Endpoints

```
GET  /api/v1/compliance/check/{project_id}           # Full compliance check
GET  /api/v1/compliance/requirements/{pathway}        # Pathway requirements
POST /api/v1/compliance/validate-sequence/{project_id} # Clearance order validation
```
