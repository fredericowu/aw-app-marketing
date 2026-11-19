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
    # Declared in the manifest; the workspace runtime renders
    # gateway-profiles.json from it on every activation and DELETES an
    # undeclared one (aw-workspace src/apps/gateway_profiles.py).
    return _manifest()["contributes"]["mcp"]["profiles"]


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
    assert "meta-ads__*" not in spec["tools_allow"]

    def allowed(qualified):
        return any(fnmatch.fnmatchcase(qualified, p) for p in spec["tools_allow"])

    assert allowed("marketing__marketing_activate_campaign")
    assert allowed("meta-ads__ads_create_campaign")
    assert allowed("meta-ads__ads_get_ad_accounts")
    assert allowed("kb__load_skill")
    assert not allowed("kb__delete_knowledge_base")


# Every Meta tool that can turn an entity ACTIVE or change one that already
# exists. The gateway's approval gate covers agent/workflow RUNS, not upstream
# tool calls, so the profile is the only enforcement: activation must go
# through marketing_activate_campaign's human approval, and edits to budget /
# targeting / status are a human's job in Ads Manager (prompt rule 3).
FORBIDDEN_META = [
    "ads_activate_entity", "ads_update_entity", "ads_duplicate_entity",
    "ads_boost_ig_post", "ads_creative_update", "ads_creative_delete",
    "ads_delete_custom_audience", "ads_delete_local_ad_image",
    "ads_create_custom_audience", "ads_update_custom_audience",
    "ads_catalog_update_product", "ads_pixel_event_create",
    "ads_experiment_abtest_create_test", "ads_dataset_create",
]


def test_marketing_profile_cannot_activate_or_edit_meta_entities():
    spec = _profiles()["marketing"]

    def allowed(qualified):
        return any(fnmatch.fnmatchcase(qualified, p) for p in spec["tools_allow"])

    for tool in FORBIDDEN_META:
        assert not allowed(f"meta-ads__{tool}"), tool


def test_marketing_profile_allows_the_meta_tools_the_skills_use():
    """Don't lock the flow out of its own steps: every ads_* tool the two
    skills name is reachable, except the ones forbidden above."""
    import re

    spec = _profiles()["marketing"]
    used = set()
    for skill in ("aw-marketing", "aw-meta-ads"):
        used |= set(re.findall(r"\bads_[a-z_]+", (ROOT / "skills" / skill / "SKILL.md").read_text()))
    used -= {"ads_manager_url", "ads_mcp_management"}  # not tool names
    for tool in sorted(used - set(FORBIDDEN_META)):
        assert any(fnmatch.fnmatchcase(f"meta-ads__{tool}", p) for p in spec["tools_allow"]), tool


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
