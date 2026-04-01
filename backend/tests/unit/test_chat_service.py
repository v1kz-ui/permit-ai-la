"""Tests for the AI chat service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestChatService:
    """Test chat service responses."""

    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        from app.services.chat_service import ChatService
        from app.config import settings

        service = ChatService()
        with patch.object(service, "_get_client") as mock_get, \
             patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Your permit is in review.")]
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await service.chat(
                project_id="00000000-0000-0000-0000-000000000001",
                user_message="What is the status of my permit?",
                conversation_history=[],
                parcel_context={
                    "address": "1000 PALISADES DR",
                    "pathway": "eo1_like_for_like",
                    "clearances": [],
                },
            )
            # chat() now returns {"response": str, "sources": list[str]}
            assert isinstance(result, dict)
            assert isinstance(result["response"], str)
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_chat_includes_project_context(self):
        from app.services.chat_service import ChatService
        from app.config import settings

        service = ChatService()
        with patch.object(service, "_get_client") as mock_get, \
             patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Based on your coastal zone...")]
            mock_client = MagicMock()
            create_mock = AsyncMock(return_value=mock_response)
            mock_client.messages.create = create_mock
            mock_get.return_value = mock_client

            await service.chat(
                project_id="00000000-0000-0000-0000-000000000002",
                user_message="Do I need a coastal permit?",
                conversation_history=[],
                parcel_context={
                    "address": "700 PALISADES BEACH RD",
                    "pathway": "eo1_like_for_like",
                    "overlays": {"coastal": True},
                    "clearances": [
                        {"department": "dcp", "type": "coastal_development_permit", "status": "in_review"}
                    ],
                },
            )
            call_args = create_mock.call_args
            assert call_args is not None, "Claude API was not called"
            system = call_args.kwargs.get("system", "")
            messages = call_args.kwargs.get("messages", [])
            full_text = str(system) + str(messages)
            assert "700 PALISADES BEACH RD" in full_text or "coastal" in full_text.lower()

    @pytest.mark.asyncio
    async def test_chat_handles_api_error(self):
        from app.services.chat_service import ChatService
        from app.config import settings

        service = ChatService()
        with patch.object(service, "_get_client") as mock_get, \
             patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
            mock_get.return_value = mock_client

            result = await service.chat(
                project_id="00000000-0000-0000-0000-000000000003",
                user_message="hello",
                conversation_history=[],
            )
            # chat() returns {"response": str, "sources": list[str]} even on error
            assert isinstance(result, dict)
            assert isinstance(result["response"], str)
            assert len(result["response"]) > 0  # Should return fallback message


class TestNotificationTemplates:
    """Test notification template coverage for all languages."""

    def test_all_templates_have_five_languages(self):
        from app.services.notification_service import NOTIFICATION_TEMPLATES

        for event_type, langs in NOTIFICATION_TEMPLATES.items():
            for lang in ("en", "es", "ko", "zh", "tl"):
                assert lang in langs, f"Missing {lang} template for {event_type}"
                assert "title" in langs[lang]
                assert "body" in langs[lang]

    def test_template_placeholders_are_valid(self):
        from app.services.notification_service import NOTIFICATION_TEMPLATES

        for event_type, langs in NOTIFICATION_TEMPLATES.items():
            for lang, template in langs.items():
                # Body should contain at least one {placeholder}
                assert "{" in template["body"], (
                    f"Template {event_type}/{lang} has no placeholders"
                )
