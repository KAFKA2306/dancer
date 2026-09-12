import re
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "production.yml"


def test_yt3_publication_uses_exact_revision_and_records_provenance():
    text = WORKFLOW.read_text(encoding="utf-8")

    match = re.search(r'YT3_REVISION:\s*"([0-9a-f]{40})"', text)
    assert match, "YT3_REVISION must be pinned to a full commit SHA"

    assert "git clone --depth 1 https://github.com/KAFKA2306/yt3.git" not in text
    assert 'git -C "$RUNNER_TEMP/yt3" fetch --depth 1 origin "$YT3_REVISION"' in text
    assert 'git -C "$RUNNER_TEMP/yt3" checkout --detach "$YT3_REVISION"' in text
    assert 'git -C "$RUNNER_TEMP/yt3" rev-parse HEAD' in text
    assert '"$actual_revision" != "$YT3_REVISION"' in text

    assert 'publication["dancer_revision"] = dancer_revision' in text
    assert 'publication["yt3_revision"] = yt3_revision' in text
    assert '"dancer_revision": dancer_revision' in text
    assert '"yt3_revision": yt3_revision' in text


def test_pull_request_stops_before_yt3_checkout():
    text = WORKFLOW.read_text(encoding="utf-8")
    pr_guard = text.index('if [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]')
    checkout = text.index('git init "$RUNNER_TEMP/yt3"')
    assert pr_guard < checkout
