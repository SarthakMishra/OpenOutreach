# tests/linkedin/touchpoints/test_factory.py
"""Test touchpoint factory."""

import sys
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock the circular import before importing models
sys.modules["linkedin.sessions.account"] = MagicMock()

# Import models first to avoid circular import issues
# Import factory after models
from linkedin.touchpoints.factory import create_touchpoint, create_touchpoint_from_model  # noqa: E402
from linkedin.touchpoints.models import (  # noqa: E402
    ConnectInput,
    DirectMessageInput,
    InMailInput,
    PostCommentInput,
    PostReactInput,
    ProfileEnrichInput,
    TouchpointType,
)


class TestCreateTouchpoint:
    """Test create_touchpoint() function."""

    def test_create_profile_enrich_touchpoint(self):
        """Test creating ProfileEnrichTouchpoint."""
        input_data = {
            "type": "profile_enrich",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "url": "https://www.linkedin.com/in/test/",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.PROFILE_ENRICH
        assert touchpoint.input.url == input_data["url"]

    def test_create_profile_visit_touchpoint(self):
        """Test creating ProfileVisitTouchpoint."""
        input_data = {
            "type": "profile_visit",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "url": "https://www.linkedin.com/in/test/",
            "duration_s": 10.0,
            "scroll_depth": 5,
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.PROFILE_VISIT
        assert touchpoint.input.duration_s == 10.0
        assert touchpoint.input.scroll_depth == 5

    def test_create_connect_touchpoint(self):
        """Test creating ConnectTouchpoint."""
        input_data = {
            "type": "connect",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "url": "https://www.linkedin.com/in/test/",
            "note": "Test note",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.CONNECT
        assert touchpoint.input.note == "Test note"

    def test_create_direct_message_touchpoint(self):
        """Test creating DirectMessageTouchpoint."""
        input_data = {
            "type": "direct_message",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "url": "https://www.linkedin.com/in/test/",
            "message": "Test message",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.DIRECT_MESSAGE
        assert touchpoint.input.message == "Test message"

    def test_create_post_react_touchpoint(self):
        """Test creating PostReactTouchpoint."""
        input_data = {
            "type": "post_react",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "post_url": "https://www.linkedin.com/feed/update/test/",
            "reaction": "LIKE",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.POST_REACT
        assert touchpoint.input.reaction == "LIKE"

    def test_create_post_comment_touchpoint(self):
        """Test creating PostCommentTouchpoint."""
        input_data = {
            "type": "post_comment",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "post_url": "https://www.linkedin.com/feed/update/test/",
            "comment_text": "Test comment",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.POST_COMMENT
        assert touchpoint.input.comment_text == "Test comment"

    def test_create_inmail_touchpoint(self):
        """Test creating InMailTouchpoint."""
        input_data = {
            "type": "inmail",
            "handle": "test_account",
            "run_id": str(uuid4()),
            "profile_url": "https://www.linkedin.com/in/test/",
            "subject": "Test subject",
            "body": "Test body",
        }
        touchpoint = create_touchpoint(input_data)
        assert touchpoint.input.type == TouchpointType.INMAIL
        assert touchpoint.input.subject == "Test subject"
        assert touchpoint.input.body == "Test body"

    def test_missing_type_field(self):
        """Test that missing type field raises ValueError."""
        input_data = {
            "handle": "test_account",
            "run_id": str(uuid4()),
            "url": "https://www.linkedin.com/in/test/",
        }
        with pytest.raises(ValueError, match="must include 'type' field"):
            create_touchpoint(input_data)

    def test_invalid_type(self):
        """Test that invalid type raises ValueError."""
        input_data = {
            "type": "invalid_type",
            "handle": "test_account",
            "run_id": str(uuid4()),
        }
        with pytest.raises(ValueError, match="Invalid touchpoint type"):
            create_touchpoint(input_data)

    def test_invalid_run_id_format(self):
        """Test that invalid run_id format raises validation error."""
        input_data = {
            "type": "profile_visit",
            "handle": "test_account",
            "run_id": "not-a-uuid",
            "url": "https://www.linkedin.com/in/test/",
        }
        with pytest.raises(ValueError, match="run_id must be a valid UUID"):
            create_touchpoint(input_data)


class TestCreateTouchpointFromModel:
    """Test create_touchpoint_from_model() function."""

    def test_create_from_profile_enrich_model(self):
        """Test creating touchpoint from ProfileEnrichInput model."""
        input_model = ProfileEnrichInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.PROFILE_ENRICH

    def test_create_from_connect_model(self):
        """Test creating touchpoint from ConnectInput model."""
        input_model = ConnectInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            note="Test note",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.CONNECT

    def test_create_from_direct_message_model(self):
        """Test creating touchpoint from DirectMessageInput model."""
        input_model = DirectMessageInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            message="Test message",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.DIRECT_MESSAGE

    def test_create_from_post_react_model(self):
        """Test creating touchpoint from PostReactInput model."""
        input_model = PostReactInput(
            handle="test_account",
            run_id=str(uuid4()),
            post_url="https://www.linkedin.com/feed/update/test/",
            reaction="CELEBRATE",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.POST_REACT
        assert touchpoint.input.reaction == "CELEBRATE"

    def test_create_from_post_comment_model(self):
        """Test creating touchpoint from PostCommentInput model."""
        input_model = PostCommentInput(
            handle="test_account",
            run_id=str(uuid4()),
            post_url="https://www.linkedin.com/feed/update/test/",
            comment_text="Test comment",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.POST_COMMENT

    def test_create_from_inmail_model(self):
        """Test creating touchpoint from InMailInput model."""
        input_model = InMailInput(
            handle="test_account",
            run_id=str(uuid4()),
            profile_url="https://www.linkedin.com/in/test/",
            body="Test body",
        )
        touchpoint = create_touchpoint_from_model(input_model)
        assert touchpoint.input.type == TouchpointType.INMAIL
