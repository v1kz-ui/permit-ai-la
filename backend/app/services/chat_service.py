"""AI chatbot service for permit Q&A using Claude API.

Provides conversational support for homeowners navigating the LA
fire-rebuild permit process.  The service injects project-specific
context (address, pathway, clearance statuses, overlays) into each
prompt so that answers are tailored to the user's situation.

RAG (Retrieval-Augmented Generation) is applied on every request:
relevant regulatory documents are retrieved from the in-memory
KnowledgeBase and injected into the system prompt before the Claude
call, grounding answers in curated permit knowledge.
"""

from __future__ import annotations

import re
import structlog

from app.config import settings

_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instruction"),
    re.compile(r"(?i)system\s*(prompt\s*)?override"),
    re.compile(r"(?i)forget\s+(all\s+)?rules"),
    re.compile(r"(?i)you\s+are\s+now\s+"),
    re.compile(r"(?i)new\s+persona"),
    re.compile(r"(?i)jailbreak"),
    re.compile(r"(?i)DAN\s+mode"),
]


def _sanitize_user_input(text: str) -> str:
    """Remove common prompt injection patterns."""
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[FILTERED]", text)
    return text[:4000]  # Also enforce max length

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are PermitAI, a helpful assistant for homeowners rebuilding after
the Los Angeles wildfires. You help them understand the City of LA permit process.

Key facts you should know:
- The City of LA created Executive Orders to speed up fire-rebuild permits.
- EO1 (Like-for-Like) allows rebuilding to match the original structure with up to 10%
  size increase. Fastest pathway (~45-120 days).
- EO8 (Expanded) allows rebuilding with up to 50% size increase (~90-180 days).
- Standard permitting applies for projects exceeding EO thresholds (180+ days).

Guidelines:
- Be empathetic. These homeowners lost their homes in a fire.
- Give clear, actionable answers grounded in LA municipal code and executive orders.
- When you are unsure, say so and recommend the homeowner contact LADBS or their liaison.
- Do NOT provide legal advice. Recommend consulting an attorney for legal questions.
- Keep answers concise but thorough. Use bullet points when listing steps.
- Reference the user's specific project context when relevant.
"""

# ---------------------------------------------------------------------------
# Module-level lazy-initialised knowledge base
# ---------------------------------------------------------------------------

_knowledge_base = None


def _get_knowledge_base():
    """Return the singleton KnowledgeBase, initialising it on first call."""
    global _knowledge_base
    if _knowledge_base is None:
        try:
            from app.ai.chatbot.knowledge_base import KnowledgeBase

            _knowledge_base = KnowledgeBase()
            logger.info("knowledge_base_initialised")
        except Exception as exc:  # pragma: no cover
            logger.warning("knowledge_base_init_failed", error=str(exc))
            _knowledge_base = None
    return _knowledge_base


# ---------------------------------------------------------------------------
# Chat service
# ---------------------------------------------------------------------------


class ChatService:
    """Async chat service backed by the Claude API."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    async def chat(
        self,
        project_id: str,
        user_message: str,
        conversation_history: list[dict] | None = None,
        parcel_context: dict | None = None,
    ) -> dict:
        """Send a user question with project context to Claude and return an answer.

        Args:
            project_id: UUID of the project being discussed.
            user_message: The latest message from the user.
            conversation_history: Previous messages as a list of
                ``{"role": "user"|"assistant", "content": "..."}`` dicts.
            parcel_context: Dict with project details (address, pathway,
                clearance statuses, overlay flags, etc.).

        Returns:
            A dict with keys:
              - ``"response"`` (str): The AI assistant's answer.
              - ``"sources"`` (list[str]): Titles of knowledge-base documents
                retrieved to inform the answer.
        """
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("chat_service_no_api_key")
            return {
                "response": (
                    "I'm sorry, the AI assistant is not available right now. "
                    "Please contact your permit liaison for help."
                ),
                "sources": [],
            }

        # ------------------------------------------------------------------
        # RAG: retrieve relevant regulatory documents for this query
        # ------------------------------------------------------------------
        source_titles: list[str] = []
        rag_section = ""

        kb = _get_knowledge_base()
        if kb is not None:
            try:
                relevant_docs = kb.search(user_message, top_k=3)
                if relevant_docs:
                    source_titles = [doc.title for doc in relevant_docs]
                    rag_lines = ["\n\nRELEVANT REGULATORY KNOWLEDGE:"]
                    for doc in relevant_docs:
                        rag_lines.append(
                            f"\n### {doc.title}\n"
                            f"Source: {doc.source}\n"
                            f"{doc.content}"
                        )
                    rag_section = "\n".join(rag_lines)
            except Exception as exc:  # pragma: no cover
                logger.warning("knowledge_base_search_failed", error=str(exc))

        # ------------------------------------------------------------------
        # Build system prompt with parcel context + RAG section
        # ------------------------------------------------------------------
        system = SYSTEM_PROMPT

        if parcel_context:
            system += "\n\nCURRENT PROJECT CONTEXT:\n"
            if parcel_context.get("address"):
                system += f"- Address: {parcel_context['address']}\n"
            if parcel_context.get("pathway"):
                system += f"- Permit Pathway: {parcel_context['pathway']}\n"
            if parcel_context.get("status"):
                system += f"- Project Status: {parcel_context['status']}\n"

            overlays = []
            if parcel_context.get("is_coastal_zone"):
                overlays.append("Coastal Zone")
            if parcel_context.get("is_hillside"):
                overlays.append("Hillside")
            if parcel_context.get("is_very_high_fire_severity"):
                overlays.append("Very High Fire Severity Zone")
            if parcel_context.get("is_historic"):
                overlays.append("Historic/HPOZ")
            if overlays:
                system += f"- Overlays: {', '.join(overlays)}\n"

            clearances = parcel_context.get("clearances")
            if clearances:
                system += "- Clearance statuses:\n"
                for c in clearances:
                    dept = c.get("department", "Unknown")
                    status = c.get("status", "unknown")
                    system += f"  - {dept}: {status}\n"

        # Append RAG section (after parcel context so it reads as background knowledge)
        if rag_section:
            system += rag_section

        # ------------------------------------------------------------------
        # Assemble message list
        # ------------------------------------------------------------------
        messages: list[dict] = []
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    if role == "user":
                        messages.append({"role": role, "content": _sanitize_user_input(content)})
                    else:
                        messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": _sanitize_user_input(user_message)})

        # ------------------------------------------------------------------
        # Call Claude
        # ------------------------------------------------------------------
        try:
            client = self._get_client()
            response = await client.messages.create(
                model="claude-sonnet-4-6-20250514",
                max_tokens=1024,
                system=system,
                messages=messages,
            )
            return {
                "response": response.content[0].text,
                "sources": source_titles,
            }

        except Exception as e:
            logger.error("chat_service_error", error=str(e), project_id=project_id)
            return {
                "response": (
                    "I'm sorry, I ran into an issue processing your question. "
                    "Please try again in a moment, or contact your permit liaison for help."
                ),
                "sources": [],
            }
