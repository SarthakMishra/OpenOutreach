# linkedin/touchpoints/factory.py
from __future__ import annotations

from typing import Any, Dict

from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.connect import ConnectTouchpoint
from linkedin.touchpoints.enrich import ProfileEnrichTouchpoint
from linkedin.touchpoints.inmail import InMailTouchpoint
from linkedin.touchpoints.message import DirectMessageTouchpoint
from linkedin.touchpoints.models import (
    ConnectInput,
    DirectMessageInput,
    InMailInput,
    PostCommentInput,
    PostReactInput,
    ProfileEnrichInput,
    ProfileVisitInput,
    TouchpointInput,
    TouchpointType,
)
from linkedin.touchpoints.post_comment import PostCommentTouchpoint
from linkedin.touchpoints.post_react import PostReactTouchpoint
from linkedin.touchpoints.visit import ProfileVisitTouchpoint

logger = None


def create_touchpoint(input_data: Dict[str, Any]) -> Touchpoint:
    """
    Create a touchpoint instance from input data.

    Args:
        input_data: Dictionary containing touchpoint input (must include 'type')

    Returns:
        Touchpoint instance

    Raises:
        ValueError: If touchpoint type is unsupported or input is invalid
    """
    # Parse touchpoint type
    touchpoint_type_str = input_data.get("type")
    if not touchpoint_type_str:
        raise ValueError("Touchpoint input must include 'type' field")

    try:
        touchpoint_type = TouchpointType(touchpoint_type_str)
    except ValueError as e:
        raise ValueError(f"Invalid touchpoint type: {touchpoint_type_str}") from e

    # Create appropriate input model and touchpoint instance
    if touchpoint_type == TouchpointType.PROFILE_ENRICH:
        input_model = ProfileEnrichInput(**input_data)
        return ProfileEnrichTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.PROFILE_VISIT:
        input_model = ProfileVisitInput(**input_data)
        return ProfileVisitTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.CONNECT:
        input_model = ConnectInput(**input_data)
        return ConnectTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
        input_model = DirectMessageInput(**input_data)
        return DirectMessageTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.POST_REACT:
        input_model = PostReactInput(**input_data)
        return PostReactTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.POST_COMMENT:
        input_model = PostCommentInput(**input_data)
        return PostCommentTouchpoint(input_model)

    elif touchpoint_type == TouchpointType.INMAIL:
        input_model = InMailInput(**input_data)
        return InMailTouchpoint(input_model)

    else:
        raise ValueError(f"Touchpoint type {touchpoint_type} not yet implemented")


def create_touchpoint_from_model(input_model: TouchpointInput) -> Touchpoint:
    """
    Create a touchpoint instance from a validated input model.

    Args:
        input_model: Validated TouchpointInput instance

    Returns:
        Touchpoint instance

    Raises:
        ValueError: If touchpoint type is unsupported
    """
    if isinstance(input_model, ProfileEnrichInput):
        return ProfileEnrichTouchpoint(input_model)
    elif isinstance(input_model, ProfileVisitInput):
        return ProfileVisitTouchpoint(input_model)
    elif isinstance(input_model, ConnectInput):
        return ConnectTouchpoint(input_model)
    elif isinstance(input_model, DirectMessageInput):
        return DirectMessageTouchpoint(input_model)
    elif isinstance(input_model, PostReactInput):
        return PostReactTouchpoint(input_model)
    elif isinstance(input_model, PostCommentInput):
        return PostCommentTouchpoint(input_model)
    elif isinstance(input_model, InMailInput):
        return InMailTouchpoint(input_model)
    else:
        raise ValueError(f"Touchpoint type {input_model.type} not yet implemented")
