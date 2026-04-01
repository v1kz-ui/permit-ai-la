# ADR-002: Deterministic Rules Engine with AI Veto Power

## Status
Accepted

## Context
Regulatory compliance requires absolute correctness. Claude AI provides reasoning for edge cases but could hallucinate incorrect pathways.

## Decision
- Regulatory logic encoded in versioned JSON files (rules/)
- Rules engine has veto power over AI recommendations
- Claude cannot recommend a faster pathway than the rules engine determines
- AI is only invoked when ambiguity is detected (edge cases with multiple possible pathways)

## Consequences
- Regulatory safety guaranteed by deterministic code
- AI adds value on ambiguous cases without risk of incorrect fast-tracking
- Rules must be maintained as regulations change (EO1, EO8, etc.)
- Claude API costs reduced by only calling on ambiguous cases (~15% of lookups)
