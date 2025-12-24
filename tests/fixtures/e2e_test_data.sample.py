# tests/fixtures/e2e_test_data.py.sample
"""E2E test data fixtures.

This file contains all test data used in e2e tests.
Copy this file to e2e_test_data.py and update with your own test data.
"""

# Profile Visit Test Data
PROFILE_VISIT_DATA = {
    "url": "https://www.linkedin.com/in/example-profile/",
    "duration_s": 3.0,
    "scroll_depth": 2,
    "tags": {"test": "e2e_profile_visit"},
}

# Connection Request Test Data
CONNECT_DATA = {
    "url": "https://www.linkedin.com/in/example-profile/",
    "public_identifier": "example-profile",
    "note": None,
    "tags": {"test": "e2e_connect"},
}

CONNECT_WITH_NOTE_DATA = {
    "url": "https://www.linkedin.com/in/example-profile/",
    "public_identifier": "example-profile",
    "note": "Your custom connection note here",
    "tags": {"test": "e2e_connect_with_note"},
}

# InMail Test Data
INMAIL_DATA = {
    "profile_url": "https://www.linkedin.com/in/example-profile/",
    "subject": "Your InMail subject",
    "body": "Your InMail body text here",
    "tags": {"test": "e2e_inmail"},
}

# Direct Message Test Data
DIRECT_MESSAGE_DATA = {
    "url": "https://www.linkedin.com/in/example-profile/",
    "public_identifier": "example-profile",
    "message": "Your direct message text here",
    "tags": {"test": "e2e_direct_message"},
}

# Post Comment Test Data
POST_COMMENT_DATA = {
    "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:EXAMPLE/",
    "comment_text": "Your comment text here",
    "tags": {"test": "e2e_post_comment"},
}

# Post React Test Data
POST_REACT_DATA = {
    "post_url": "https://www.linkedin.com/feed/update/urn:li:activity:EXAMPLE/",
    "reaction": "LIKE",
    "tags": {"test": "e2e_post_react"},
}

