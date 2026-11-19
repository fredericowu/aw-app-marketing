"""The agent config names gateway profiles; a profile nobody defines answers
404 at /mcp/<name> and the agent comes up with ZERO tools, silently. That was
live until v0.10 for `marketing`, so pin both halves together."""
from __future__ import annotations

import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _manifest():
    return json.loads((ROOT / "aw-app.json").read_text())


def _profiles():
    return json.loads((ROOT / "gateway-profiles.json").read_text())["profiles"]


def _servers():
    cfg = _manifest()["contributes"]["agents"]["agent_configs"][0]
    return {s["name"]: s for s in cfg["mcp_servers"]}


def test_marketing_profile_is_defined_by_this_app():
    servers = _servers()
    assert servers["marketing"]["profile"] == "marketing"
    assert "marketing" in _profiles()


def test_marketing_profile_covers_own_and_meta_tools_and_skill_loading():
    spec = _profiles()["marketing"]
    assert {"marketing", "meta-ads", "kb"} <= set(spec["upstreams"])

    def allowed(qualified):
        return any(fnmatch.fnmatchcase(qualified, p) for p in spec["tools_allow"])

    assert allowed("marketing__marketing_activate_campaign")
    assert allowed("meta-ads__ads_create_campaign")
    assert allowed("kb__load_skill")
    assert not allowed("kb__delete_knowledge_base")


def test_google_ads_profile_is_wired_but_owned_by_the_google_ads_app():
    servers = _servers()
    assert servers["google-ads"] == {"name": "google-ads", "server": "aw-gateway",
                                     "profile": "google-ads"}
    # Defining it here too would be a cross-app name collision, which the
    # gateway resolves by dropping the profile from BOTH apps.
    assert "google-ads" not in _profiles()


def test_prompt_keeps_google_ads_read_only():
    prompt = (ROOT / "agents" / "prompts" / "marketing.md").read_text()
    assert "aw-google-ads" in prompt
    assert "só leitura" in prompt
