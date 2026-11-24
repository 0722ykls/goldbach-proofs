"""Verify a user's one-time account-link challenge against a GitHub-owned gist."""

import http.client
import json
import re
import secrets
import urllib.error
import urllib.request

PROOF_FILENAME = "goldbach-identity.txt"
HANDLE = r"[a-z0-9]+(?:-[a-z0-9]+)*"
GIST = re.compile(rf"(?:https://gist\.github\.com/(?:{HANDLE}/)?)?([a-f0-9]{{32}})/?", re.I | re.ASCII)
MAX_BYTES = 64 * 1024


class GithubProofError(ValueError):
    def __init__(self, code, status):
        super().__init__(code)
        self.code = code
        self.status = status


def new_challenge():
    return secrets.token_urlsafe(32)


def proof_text(challenge, handle):
    if not (isinstance(handle, str) and len(handle) <= 39
            and re.fullmatch(HANDLE, handle, re.I | re.ASCII)):
        raise GithubProofError("invalid_github_handle", 400)
    if not isinstance(challenge, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", challenge):
        raise GithubProofError("invalid_challenge", 400)
    return f"Goldbach Research: link GitHub @{handle.lower()} to my Zhihu profile. Challenge: {challenge}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_gist(gist, challenge, handle):
    """Return the stable numeric ID and lowercase login. The caller owns expiry and consumption."""
    expected = proof_text(challenge, handle)
    match = GIST.fullmatch(gist.strip()) if isinstance(gist, str) and len(gist) <= 200 else None
    if not match:
        raise GithubProofError("invalid_gist", 400)
    gist_id = match[1].lower()
    request = urllib.request.Request(f"https://api.github.com/gists/{gist_id}", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Goldbach-Research-Identity",
    })
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=6) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise GithubProofError("github_proof_mismatch", 422)
        data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GithubProofError("github_proof_mismatch", 422) from exc
        raise GithubProofError("github_unavailable", 503) from exc
    except (OSError, http.client.HTTPException, json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise GithubProofError("github_unavailable", 503) from exc
    if not isinstance(data, dict) or data.get("id") != gist_id:
        raise GithubProofError("github_proof_mismatch", 422)
    owner, files = data.get("owner"), data.get("files")
    if not isinstance(owner, dict) or not isinstance(files, dict):
        raise GithubProofError("github_proof_mismatch", 422)
    uid, login = owner.get("id"), owner.get("login")
    entry = files.get(PROOF_FILENAME)
    if (type(uid) is not int or not 0 < uid < (1 << 63) or owner.get("type") != "User"
            or not isinstance(login, str) or not login.isascii() or login.lower() != handle.lower()
            or not isinstance(entry, dict) or entry.get("truncated") is not False
            or entry.get("content") not in (expected, expected + "\n", expected + "\r\n")):
        raise GithubProofError("github_proof_mismatch", 422)
    return uid, login.lower()
