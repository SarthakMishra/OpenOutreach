# campaigns/connect_follow_up.py
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin.actions.connection_status import get_connection_status
from linkedin.db.profiles import set_profile_state, get_profile, save_scraped_profile
from linkedin.navigation.enums import MessageStatus
from linkedin.navigation.enums import ProfileState
from linkedin.navigation.exceptions import (
    TerminalStateError,
    SkipProfile,
    ReachedConnectionLimit,
)
from linkedin.navigation.utils import save_page
from linkedin.sessions.registry import SessionKey

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)

# ———————————————————————————————— USER CONFIGURATION ————————————————————————————————
CAMPAIGN_NAME = "connect_follow_up"
INPUT_CSV_PATH = Path("./assets/inputs/urls.csv")

# ———————————————————————————————— Template Config ————————————————————————————————

FOLLOWUP_TEMPLATE_FILE = "./assets/templates/prompts/followup.j2"
FOLLOWUP_TEMPLATE_TYPE = "ai_prompt"

# ———————————————————————————————— CSV Overrides (no-AI path) ————————————————————————————————
# If these columns exist in your input CSV, the campaign can use them directly.
#
# - followup_message: exact DM text to send once connected (bypasses templates/AI)
# - connect_note: optional connection note to send with the invite (off by default)
FOLLOWUP_MESSAGE_CSV_COLUMN = "followup_message"
CONNECT_NOTE_CSV_COLUMN = "connect_note"
SEND_CONNECT_NOTE = False  # set True to enable sending the CSV connect_note

message_status_to_state = {
    MessageStatus.SENT: ProfileState.COMPLETED,
    MessageStatus.SKIPPED: ProfileState.CONNECTED,
}


# ———————————————————————————————— Core Logic ————————————————————————————————
def process_profile_row(
    key: SessionKey,
    session: "AccountSession",
    profile: dict,
    perform_connections=True,
):
    from linkedin.actions.connect import send_connection_request
    from linkedin.actions.message import send_follow_up_message
    from linkedin.actions.profile import scrape_profile

    url = profile["url"]
    public_identifier = profile["public_identifier"]
    csv_followup_message = profile.get(FOLLOWUP_MESSAGE_CSV_COLUMN)
    csv_connect_note = profile.get(CONNECT_NOTE_CSV_COLUMN)
    profile_row = get_profile(session, public_identifier)

    if profile_row:
        current_state = ProfileState(profile_row.state)  # ← string → enum
        enriched_profile = profile_row.profile or profile
    else:
        current_state = ProfileState.DISCOVERED
        enriched_profile = profile

    logger.debug(f"Actual state: {public_identifier}  {current_state}")

    new_state = None
    match current_state:
        case ProfileState.COMPLETED | ProfileState.FAILED:
            return None

        case ProfileState.DISCOVERED:
            enriched_profile, data = scrape_profile(key=key, profile=enriched_profile)
            if enriched_profile is None:
                new_state = ProfileState.FAILED
            else:
                # Preserve campaign-specific CSV fields across enrichment
                if csv_followup_message is not None:
                    enriched_profile[FOLLOWUP_MESSAGE_CSV_COLUMN] = csv_followup_message
                if csv_connect_note is not None:
                    enriched_profile[CONNECT_NOTE_CSV_COLUMN] = csv_connect_note
                new_state = ProfileState.ENRICHED
                save_scraped_profile(session, url, enriched_profile, data)

        case ProfileState.ENRICHED:
            if not perform_connections:
                return None
            note = csv_connect_note if SEND_CONNECT_NOTE else None
            new_state = send_connection_request(
                key=key, profile=enriched_profile, note=note
            )
            enriched_profile = (
                None if new_state != ProfileState.CONNECTED else enriched_profile
            )
        case ProfileState.PENDING:
            new_state = get_connection_status(session, profile)
            enriched_profile = (
                None if new_state != ProfileState.CONNECTED else enriched_profile
            )
        case ProfileState.CONNECTED:
            # If CSV provides an explicit message, use it (bypasses templates/AI).
            if isinstance(csv_followup_message, str) and csv_followup_message.strip():
                status = send_follow_up_message(
                    key=key,
                    profile=enriched_profile,
                    message=csv_followup_message.strip(),
                )
            else:
                status = send_follow_up_message(
                    key=key,
                    profile=enriched_profile,
                    template_file=FOLLOWUP_TEMPLATE_FILE,
                    template_type=FOLLOWUP_TEMPLATE_TYPE,
                )
            new_state = message_status_to_state.get(status, ProfileState.CONNECTED)
            enriched_profile = (
                None if status != MessageStatus.SENT else enriched_profile
            )

        case _:
            raise TerminalStateError(f"Profile {public_identifier} is {current_state}")

    set_profile_state(session, public_identifier, new_state.value)

    return enriched_profile


def process_profiles(key, session, profiles: list[dict]):
    perform_connections = True
    for profile in profiles:
        go_ahead = True
        while go_ahead:
            try:
                profile = process_profile_row(
                    key=key,
                    session=session,
                    profile=profile,
                    perform_connections=perform_connections,
                )
                go_ahead = bool(profile)
            except SkipProfile as e:
                public_identifier = profile["public_identifier"]
                logger.info(
                    f"\033[91mSkipping profile: {public_identifier} reason: {e}\033[0m"
                )
                save_page(session, profile)
                go_ahead = False
            except ReachedConnectionLimit as e:
                perform_connections = False
                public_identifier = profile["public_identifier"]
                logger.info(
                    f"\033[91mSkipping profile: {public_identifier} reason: {e}\033[0m"
                )
