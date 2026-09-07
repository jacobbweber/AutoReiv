"""
Unit tests for Transcript Secret Scrubber [CARD-168].
"""

from src.domain.security.scrubber import TranscriptScrubber


def test_transcript_scrubber_masks_single_and_multiple_secrets():
    scrubber = TranscriptScrubber(secrets=["ghp_abc1234567890", "super_secret_ssh_key_xyz"])

    text = "Connecting to git with token ghp_abc1234567890 and key super_secret_ssh_key_xyz."
    scrubbed = scrubber.scrub(text)

    assert "ghp_abc1234567890" not in scrubbed
    assert "super_secret_ssh_key_xyz" not in scrubbed
    assert "***MASKED***" in scrubbed


def test_transcript_scrubber_handles_nested_dicts():
    scrubber = TranscriptScrubber(secrets=["my_db_password_999"])

    payload = {
        "output": {
            "stdout": "DATABASE_URL=postgres://user:my_db_password_999@localhost/db",
            "exit_code": 0,
        },
        "message": "Connected using password my_db_password_999",
    }

    scrubbed = scrubber.scrub_object(payload)
    assert "my_db_password_999" not in scrubbed["output"]["stdout"]
    assert "my_db_password_999" not in scrubbed["message"]
    assert "***MASKED***" in scrubbed["output"]["stdout"]
