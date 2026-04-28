from rag_nano.ingest.credential_scan import scan


SAFE_LINES = [
    "Hello, this is a test message.",
    "The URL is https://example.com/path",
    "My API endpoint is https://api.example.com/v1",
    "Config: base_url = 'https://example.com'",
    "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # truncated JWT prefix only
    "password in quotes: 'abc123xyz'",
    "api_key = ''",  # empty value
    "secret = '12'",  # too short
]


CREDENTIAL_POSITIVES = [
    ("AKIA000000000000FAKE", "credential_aws_access_key"),
    ("ghp" + "_FAKETESTKEY0000000000000000000000000", "credential_github_pat"),
    ("sk_" + "live_FAKETESTKEY0000000000000", "credential_stripe_key"),
    ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozBMNPNtQ", "credential_jwt"),
    ("api_key = AKIA000000000000FAKE", "credential_generic_assignment"),
]


class TestCredentialScan:
    def test_false_positives_safe(self) -> None:
        for line in SAFE_LINES:
            result = scan(line)
            assert result is None, f"False positive on: {line!r} -> {result}"

    def test_aws_key_detected(self) -> None:
        result = scan("aws_access_key_id=AKIA000000000000FAKE")
        assert result == "credential_aws_access_key"

    def test_github_pat_detected(self) -> None:
        result = scan("ghp" + "_FAKETESTKEY0000000000000000000000000")
        assert result == "credential_github_pat"

    def test_stripe_key_detected(self) -> None:
        result = scan("sk_" + "live_FAKETESTKEY0000000000000")
        assert result == "credential_stripe_key"

    def test_jwt_detected(self) -> None:
        result = scan("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozBMNPNtQtR")
        assert result == "credential_jwt"

    def test_generic_assignment_detected(self) -> None:
        result = scan("password = verylongpasswordvalue12345")
        assert result == "credential_generic_assignment"
