import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
GROUPS = {"grp_pompes", "grp_compresseurs", "grp_responsables", "grp_prestataires"}


def _yaml(name):
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


def test_users_reference_known_groups():
    data = _yaml("users.yaml")
    assert set(data["group_families"]) == GROUPS
    for user in data["users"]:
        assert set(user["groups"]) <= GROUPS, user["user_id"]


def test_history_references_existing_equipment_and_users():
    equipment = {e["equipment_id"] for e in _yaml("equipment.yaml")["equipment"]}
    users = {u["user_id"] for u in _yaml("users.yaml")["users"]}
    history = json.loads((FIXTURES / "interventions.json").read_text(encoding="utf-8"))
    for item in history["interventions"]:
        assert item["equipment_id"] in equipment
        assert item["technician"] in users
    for ticket in history["open_tickets"]:
        assert ticket["equipment_id"] in equipment
        assert ticket["created_by"] in users


def test_photos_match_equipment_fleet():
    equipment = {e["equipment_id"]: e for e in _yaml("equipment.yaml")["equipment"]}
    manifest = yaml.safe_load((ROOT / "corpus" / "manifest.yaml").read_text(encoding="utf-8"))
    for photo in manifest["photos"]:
        if photo["equipment_id"]:
            assert equipment[photo["equipment_id"]]["family"] == photo["equipment_family"]
