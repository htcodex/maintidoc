"""Tests d'intégration avec les services docker compose (PostgreSQL, S3, Qdrant serveur).

Ignorés automatiquement si les services ne sont pas configurés (.env) ou pas démarrés.
Lancer : docker compose up -d postgres qdrant s3 ; python -m maintidoc.ingestion.pipeline ; pytest -m services
"""

import pytest

from maintidoc.access import AccessDenied, can_read, open_asset
from maintidoc.catalog import load_users
from maintidoc.config import ROOT, get_settings

pytestmark = pytest.mark.services


@pytest.fixture(scope="module")
def settings():
    s = get_settings()
    if not (s.database_url and s.s3_endpoint and s.qdrant_url):
        pytest.skip("services non configurés dans .env")
    return s


@pytest.fixture(scope="module")
def store(settings):
    from maintidoc.storage import open_metadata_store
    try:
        st = open_metadata_store(settings)
    except Exception as exc:
        pytest.skip(f"PostgreSQL indisponible : {exc}")
    if not st.all_elements():
        pytest.skip("index vide : lancer python -m maintidoc.ingestion.pipeline")
    yield st
    st.close()


def test_sql_access_filter_matches_python_rule(store):
    users = load_users(ROOT / "data" / "fixtures")
    elements = store.all_elements()
    for u in users.values():
        sql = set(store.elements_for_groups(u.groups))
        py = {e.key for e in elements if can_read(u, e.access_groups)}
        assert sql == py, u.user_id


def test_s3_assets_readable_only_with_rights(settings, store):
    from maintidoc.storage import open_asset_store
    assets = open_asset_store(settings)
    users = load_users(ROOT / "data" / "fixtures")
    fig = next(e for e in store.all_elements() if e.document_id == "mdp_man_util" and e.element_id == "figure_1_1")
    data = open_asset(users["u_tech_p01"], fig.access_groups, fig.image_path, store=assets)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    with pytest.raises(AccessDenied):
        open_asset(users["u_tech_c01"], fig.access_groups, fig.image_path, store=assets)


def test_qdrant_server_filter(settings, store):
    from qdrant_client import models

    from maintidoc.retrieval import index as idx
    client = idx.open_client(settings)
    pts, _ = client.scroll(idx.TEXT_COLLECTION, scroll_filter=idx.access_filter(["grp_prestataires"]), limit=500,
                           with_payload=["document_id"])
    assert {p.payload["document_id"] for p in pts} <= {"trans_sec_epi", "trans_sec_consignation", "trans_glossaire"}
    n = client.count(idx.TEXT_COLLECTION, count_filter=models.Filter(must=[models.FieldCondition(
        key="document_id", match=models.MatchValue(value="trans_contrat_maint"))])).count
    assert n > 0
    client.close()
