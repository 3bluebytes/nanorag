from __future__ import annotations

import re

PATTERN_AWS_ACCESS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
PATTERN_GITHUB_PAT = re.compile(r"ghp_[0-9a-zA-Z]{36}")
PATTERN_STRIPE_KEY = re.compile(r"sk_live_[0-9a-zA-Z]{24}")
PATTERN_JWT = re.compile(r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*")
PATTERN_GENERIC_KEY = re.compile(
    r'(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[=:]?\s*["\']?[\w-]{20,}["\']?',
    re.IGNORECASE,
)
CREDENTIAL_PATTERNS = [
    ("credential_aws_access_key", PATTERN_AWS_ACCESS_KEY),
    ("credential_github_pat", PATTERN_GITHUB_PAT),
    ("credential_stripe_key", PATTERN_STRIPE_KEY),
    ("credential_jwt", PATTERN_JWT),
    ("credential_generic_assignment", PATTERN_GENERIC_KEY),
]


def scan(text: str) -> str | None:
    for reason_name, pattern in CREDENTIAL_PATTERNS:
        if pattern.search(text):
            return reason_name
    return None
