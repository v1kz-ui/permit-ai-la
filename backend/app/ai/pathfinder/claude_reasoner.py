"""Claude API integration for PathfinderAI edge-case reasoning.

The rules engine handles deterministic pathway evaluation. This module is called
only when the rules engine cannot make a confident determination -- e.g., unusual
zoning overlays, conflicting requirements, or ambiguous project scope.

The rules engine always has veto power over Claude's output.
"""

import json

import structlog

from app.config import settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are PathfinderAI, a regulatory reasoning engine for Los Angeles
fire-rebuild permits. You analyze parcel data and rebuild scope to determine the
optimal permit pathway.

LA Executive Orders for fire rebuilds:
- EO1 (Like-for-Like): Allows rebuilding to match original structure with up to 10%
  size increase. Fastest pathway (45-120 days). Exempts full environmental review,
  design review board, and conditional use permits.
- EO8 (Expanded): Allows rebuilding with up to 50% size increase. Intermediate
  timeline (90-180 days). Still requires plan check and some design review.
- Standard: Full permitting process for projects exceeding EO thresholds (180+ days).

Key overlays that add requirements:
- Coastal Zone: Requires Coastal Development Permit from DCP
- Hillside: Requires grading permit, geotechnical review, haul route approval
- Very High Fire Severity Zone: Requires brush clearance, fire flow verification
- Historic/HPOZ: Requires historic preservation review

You MUST respond with valid JSON in this exact format:
{
    "recommended_pathway": "eo1_like_for_like" | "eo8_expanded" | "standard",
    "confidence": 0.0 to 1.0,
    "reasoning": "explanation of your analysis",
    "additional_clearances": ["list of any additional clearances needed"],
    "risk_factors": ["list of potential issues or delays"],
    "estimated_days_adjustment": integer (positive = longer, negative = shorter)
}"""


async def reason_about_pathway(
    parcel_data: dict,
    rebuild_scope: dict,
    rules_result: dict,
    ambiguity_description: str,
) -> dict:
    """Ask Claude to reason about edge cases in permit pathway determination."""
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("Claude API key not configured, skipping AI reasoning")
        return {
            "ai_recommendation": None,
            "confidence": 0.0,
            "reasoning": "AI reasoning not available (API key not configured)",
            "additional_clearances": [],
            "risk_factors": [],
        }

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        user_prompt = f"""Analyze this fire-rebuild permit case and recommend the optimal pathway.

PARCEL DATA:
{json.dumps(parcel_data, indent=2)}

REBUILD SCOPE:
{json.dumps(rebuild_scope, indent=2)}

RULES ENGINE RESULT (deterministic evaluation):
{json.dumps(rules_result, indent=2)}

AMBIGUITY / EDGE CASE:
{ambiguity_description}

Provide your analysis considering the parcel overlays, rebuild scope, and any
conflicts between requirements. The rules engine result above is the baseline --
explain whether you agree or see issues the rules engine may have missed."""

        message = await client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = message.content[0].text

        # Parse structured JSON response
        try:
            ai_result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response_text)
            if json_match:
                ai_result = json.loads(json_match.group(1))
            else:
                logger.warning("Failed to parse Claude response as JSON", response=response_text[:200])
                return {
                    "ai_recommendation": None,
                    "confidence": 0.0,
                    "reasoning": response_text[:500],
                    "additional_clearances": [],
                    "risk_factors": [],
                }

        # Validate against rules engine (rules engine has veto)
        validated = _validate_against_rules(ai_result, rules_result)

        logger.info(
            "claude_reasoning_complete",
            recommendation=validated.get("ai_recommendation"),
            confidence=validated.get("confidence"),
            vetoed=validated.get("rules_engine_vetoed", False),
        )

        return validated

    except ImportError:
        logger.warning("anthropic package not installed")
        return {
            "ai_recommendation": None,
            "confidence": 0.0,
            "reasoning": "Anthropic SDK not installed",
            "additional_clearances": [],
            "risk_factors": [],
        }
    except Exception as e:
        logger.error("claude_reasoning_error", error=str(e))
        return {
            "ai_recommendation": None,
            "confidence": 0.0,
            "reasoning": f"AI reasoning failed: {str(e)}",
            "additional_clearances": [],
            "risk_factors": [],
        }


def _validate_against_rules(ai_result: dict, rules_result: dict) -> dict:
    """Rules engine has absolute veto power over Claude's recommendation.

    If Claude recommends a faster pathway than the rules engine allows,
    the rules engine result wins. Claude can only recommend the same or
    slower pathway, or add additional clearances/risk factors.
    """
    pathway_speed = {
        "eo1_like_for_like": 1,
        "eo8_expanded": 2,
        "standard": 3,
        "self_certification": 0,
    }

    rules_pathway = rules_result.get("pathway", "standard")
    ai_pathway = ai_result.get("recommended_pathway", "standard")
    rules_speed = pathway_speed.get(rules_pathway, 3)
    ai_speed = pathway_speed.get(ai_pathway, 3)

    vetoed = False
    final_pathway = ai_pathway

    # Veto: Claude cannot recommend a FASTER pathway than the rules engine
    if ai_speed < rules_speed:
        final_pathway = rules_pathway
        vetoed = True

    return {
        "ai_recommendation": final_pathway,
        "confidence": min(ai_result.get("confidence", 0.0), 1.0),
        "reasoning": ai_result.get("reasoning", ""),
        "additional_clearances": ai_result.get("additional_clearances", []),
        "risk_factors": ai_result.get("risk_factors", []),
        "estimated_days_adjustment": ai_result.get("estimated_days_adjustment", 0),
        "rules_engine_vetoed": vetoed,
    }
