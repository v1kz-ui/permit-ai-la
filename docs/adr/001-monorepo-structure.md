# ADR-001: Monorepo Structure

## Status
Accepted

## Context
8-person team building an AI-powered permit platform with 3 deployable artifacts (API, dashboard, mobile) in a 90-day timeline.

## Decision
Use a single monorepo with backend/, dashboard/, mobile/, shared/, rules/, infrastructure/ directories.

## Consequences
- Shared types and clearance taxonomy across all apps
- Single CI pipeline with parallel jobs
- Atomic commits spanning API + frontend changes
- Slightly more complex build caching
