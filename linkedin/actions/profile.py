# linkedin/actions/profile.py
import json
import logging
from pathlib import Path
from typing import Any, Dict

from linkedin.conf import FIXTURE_PROFILES_DIR
from linkedin.sessions.registry import AccountSessionRegistry, SessionKey

from ..api.client import PlaywrightLinkedinAPI

logger = logging.getLogger(__name__)


def scrape_profile(key: SessionKey, profile: dict):
    url = profile["url"]

    session = AccountSessionRegistry.get_or_create(
        handle=key.handle,
        run_id=key.run_id,
    )

    # ── Existing enrichment logic (100% unchanged) ──
    session.ensure_browser()
    session.wait()

    api = PlaywrightLinkedinAPI(session=session)

    logger.info("Enriching profile → %s", url)
    result = api.get_profile(profile_url=url)
    profile: dict | None = None
    data: Any = None
    if result[0] is not None:
        profile, data = result
        if profile:
            logger.info("Profile enriched – %s", profile.get("public_identifier"))
    else:
        profile, data = result

    return profile, data


def _save_profile_to_fixture(enriched_profile: Dict[str, Any], path: str | Path) -> None:
    """Utility to save enriched profile as test fixture."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(enriched_profile, f, indent=2, ensure_ascii=False, default=str)
    logger.info("Enriched profile saved to fixture → %s", path)


if __name__ == "__main__":
    import sys

    FIXTURE_PATH = FIXTURE_PROFILES_DIR / "linkedin_profile.json"

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) != 2:
        logger.error("Usage: python -m linkedin.actions.profile <handle>")
        sys.exit(1)

    import uuid

    handle = sys.argv[1]
    run_id = str(uuid.uuid4())
    key = SessionKey(handle=handle, run_id=run_id)

    test_profile = {
        "url": "https://www.linkedin.com/in/lexfridman/",
    }

    profile, data = scrape_profile(key, test_profile)

    _save_profile_to_fixture(data, FIXTURE_PATH)
    logger.info("Fixture saved → %s", FIXTURE_PATH)
