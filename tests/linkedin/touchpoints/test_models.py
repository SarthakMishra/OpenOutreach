# tests/linkedin/touchpoints/test_models.py
"""Test touchpoint models."""

# Mock the circular import before importing models
import sys
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

# Mock AccountSession before any imports that might trigger circular import
sys.modules["linkedin.sessions.account"] = MagicMock()

# Now import models - this should work since AccountSession is mocked
from linkedin.touchpoints.models import (  # noqa: E402
    ConnectInput,
    DirectMessageInput,
    InMailInput,
    PostCommentInput,
    PostReactInput,
    ProfileEnrichInput,
    ProfileVisitInput,
    TouchpointType,
)


class TestTouchpointInput:
    """Test TouchpointInput base model validation."""

    def test_valid_run_id(self):
        """Test that valid UUID format is accepted."""
        run_id = str(uuid4())
        input_data = ProfileEnrichInput(
            handle="test_account",
            run_id=run_id,
            url="https://www.linkedin.com/in/test/",
        )
        assert input_data.run_id == run_id
        # Verify it's a valid UUID
        UUID(input_data.run_id)

    def test_invalid_run_id_format(self):
        """Test that invalid UUID format raises ValueError."""
        with pytest.raises(ValueError, match="run_id must be a valid UUID"):
            ProfileEnrichInput(
                handle="test_account",
                run_id="not-a-uuid",
                url="https://www.linkedin.com/in/test/",
            )

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ProfileEnrichInput(
                handle="test_account",
                # Missing run_id and url/public_identifier
            )


class TestProfileEnrichInput:
    """Test ProfileEnrichInput validation."""

    def test_valid_with_url(self):
        """Test that url alone is valid."""
        input_data = ProfileEnrichInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
        )
        assert input_data.url == "https://www.linkedin.com/in/test/"

    def test_valid_with_public_identifier(self):
        """Test that public_identifier alone is valid."""
        input_data = ProfileEnrichInput(
            handle="test_account",
            run_id=str(uuid4()),
            public_identifier="testuser",
        )
        assert input_data.public_identifier == "testuser"

    def test_valid_with_both(self):
        """Test that both url and public_identifier are valid."""
        input_data = ProfileEnrichInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            public_identifier="testuser",
        )
        assert input_data.url is not None
        assert input_data.public_identifier is not None

    def test_missing_both_identifiers(self):
        """Test that missing both url and public_identifier raises ValueError."""
        with pytest.raises(ValueError, match="Either public_identifier or url must be provided"):
            ProfileEnrichInput(
                handle="test_account",
                run_id=str(uuid4()),
            )


class TestProfileVisitInput:
    """Test ProfileVisitInput validation."""

    def test_valid_input(self):
        """Test valid ProfileVisitInput."""
        input_data = ProfileVisitInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            duration_s=10.0,
            scroll_depth=5,
        )
        assert input_data.duration_s == 10.0
        assert input_data.scroll_depth == 5

    def test_default_values(self):
        """Test that default values are applied."""
        input_data = ProfileVisitInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
        )
        assert input_data.duration_s == 5.0
        assert input_data.scroll_depth == 3

    def test_negative_duration(self):
        """Test that negative duration raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ProfileVisitInput(
                handle="test_account",
                run_id=str(uuid4()),
                url="https://www.linkedin.com/in/test/",
                duration_s=-1.0,
            )

    def test_negative_scroll_depth(self):
        """Test that negative scroll_depth raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ProfileVisitInput(
                handle="test_account",
                run_id=str(uuid4()),
                url="https://www.linkedin.com/in/test/",
                scroll_depth=-1,
            )


class TestConnectInput:
    """Test ConnectInput validation."""

    def test_valid_with_note(self):
        """Test ConnectInput with note."""
        input_data = ConnectInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            note="Test note",
        )
        assert input_data.note == "Test note"

    def test_valid_without_note(self):
        """Test ConnectInput without note."""
        input_data = ConnectInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
        )
        assert input_data.note is None


class TestDirectMessageInput:
    """Test DirectMessageInput validation."""

    def test_valid_message(self):
        """Test valid DirectMessageInput."""
        input_data = DirectMessageInput(
            handle="test_account",
            run_id=str(uuid4()),
            url="https://www.linkedin.com/in/test/",
            message="Test message",
        )
        assert input_data.message == "Test message"

    def test_empty_message(self):
        """Test that empty message raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            DirectMessageInput(
                handle="test_account",
                run_id=str(uuid4()),
                url="https://www.linkedin.com/in/test/",
                message="",
            )


class TestPostReactInput:
    """Test PostReactInput validation."""

    def test_valid_reactions(self):
        """Test all valid reaction types."""
        valid_reactions = ["LIKE", "CELEBRATE", "SUPPORT", "LOVE", "INSIGHTFUL", "CURIOUS"]
        for reaction in valid_reactions:
            input_data = PostReactInput(
                handle="test_account",
                run_id=str(uuid4()),
                post_url="https://www.linkedin.com/feed/update/test/",
                reaction=reaction,
            )
            assert input_data.reaction == reaction

    def test_invalid_reaction(self):
        """Test that invalid reaction raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PostReactInput(
                handle="test_account",
                run_id=str(uuid4()),
                post_url="https://www.linkedin.com/feed/update/test/",
                reaction="INVALID",
            )


class TestPostCommentInput:
    """Test PostCommentInput validation."""

    def test_valid_comment(self):
        """Test valid PostCommentInput."""
        input_data = PostCommentInput(
            handle="test_account",
            run_id=str(uuid4()),
            post_url="https://www.linkedin.com/feed/update/test/",
            comment_text="Test comment",
        )
        assert input_data.comment_text == "Test comment"

    def test_empty_comment(self):
        """Test that empty comment raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PostCommentInput(
                handle="test_account",
                run_id=str(uuid4()),
                post_url="https://www.linkedin.com/feed/update/test/",
                comment_text="",
            )


class TestInMailInput:
    """Test InMailInput validation."""

    def test_valid_with_subject(self):
        """Test InMailInput with subject."""
        input_data = InMailInput(
            handle="test_account",
            run_id=str(uuid4()),
            profile_url="https://www.linkedin.com/in/test/",
            subject="Test subject",
            body="Test body",
        )
        assert input_data.subject == "Test subject"
        assert input_data.body == "Test body"

    def test_valid_without_subject(self):
        """Test InMailInput without subject."""
        input_data = InMailInput(
            handle="test_account",
            run_id=str(uuid4()),
            profile_url="https://www.linkedin.com/in/test/",
            body="Test body",
        )
        assert input_data.subject is None
        assert input_data.body == "Test body"

    def test_empty_body(self):
        """Test that empty body raises ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            InMailInput(
                handle="test_account",
                run_id=str(uuid4()),
                profile_url="https://www.linkedin.com/in/test/",
                body="",
            )


class TestTouchpointType:
    """Test TouchpointType enum."""

    def test_all_types_exist(self):
        """Test that all expected touchpoint types exist."""
        expected_types = {
            "profile_enrich",
            "profile_visit",
            "connect",
            "direct_message",
            "post_react",
            "post_comment",
            "inmail",
        }
        actual_types = {t.value for t in TouchpointType}
        assert actual_types == expected_types

    def test_type_equality(self):
        """Test that enum values match string values."""
        assert TouchpointType.PROFILE_ENRICH == "profile_enrich"
        assert TouchpointType.CONNECT == "connect"
        assert TouchpointType.INMAIL == "inmail"
