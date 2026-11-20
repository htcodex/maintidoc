"""Tests de la semaine 2 : extraction, index, recherche filtrée, contrôle d'accès, métriques.

Ils utilisent des encodeurs factices (aucun téléchargement de modèle) et un index temporaire.
L'OCR des documents scannés est lent (~1 min) : ces documents sont exclus ici et testés à part
(marqueur `slow`).
"""

from pathlib import Path

import pytest

from maintidoc.access import AccessDenied, can_read, open_asset
from maintidoc.catalog import User, load_catalog, load_users
from maintidoc.config import ROOT, local_settings
from maintidoc.evaluation.retrieval_eval import is_relevant, metrics
from maintidoc.ingestion.extract import extract_pdf
from maintidoc.retrieval import index as idx
from maintidoc.retrieval.encoders import HashingEncoder
from maintidoc.retrieval.search import Hit, Retriever, tokenize

CORPUS = ROOT / "corpus"
SUBSET = ["mdp_man_util", "mdc_man_util", "mdp_bt_2025_01", "mdp_man_maint", "mdp_sch_hydr",
          "trans_contrat_maint", "trans_sec_epi", "trans_note_inj", "historique_interventions_mdp"]


@pytest.fixture(scope="module")
def catalog():
    return {d.document_id: d for d in load_catalog(CORPUS)}


@pytest.fixture(scope="module")
def users():
    return load_users(ROOT / "data" / "fixtures")


@pytest.fixture(scope="module")
def retriever(tmp_path_factory, catalog):
    tmp = tmp_path_factory.mktemp("index")
    s = local_settings(index_dir=tmp)
    elements = []
    for did in SUBSET:
        elements += extract_pdf(catalog[did], s.assets_dir)
    text_enc, image_enc = HashingEncoder(256), HashingEncoder(128)
    client = idx.open_client(s)
    idx.recreate_collections(client, 256, 128)
    idx.upsert(client, idx.TEXT_COLLECTION, elements, text_enc.encode([e.embed_text for e in elements]))
    visual = [e for e in elements if idx.is_visual(e)]
    idx.upsert(client, idx.IMAGE_COLLECTION, visual, image_enc.encode_images([e.image_path for e in visual]))
    client.close()
    store = idx.MetadataStore(s.metadata_db)
    store.add_elements(elements)
    store.commit()
    r = Retriever(s, text_enc, image_enc)
    yield r
    r.close()


# ------------------------------------------------------------------ catalogue et extraction

def test_catalog_matches_inventory(catalog):
    assert len(catalog) == 47
    assert all(d.file.exists() for d in catalog.values())
    assert catalog["mdp_bt_2024_03"].status == "superseded"
    assert catalog["mdp_bt_2024_03"].superseded_by == "mdp_bt_2025_01"
    assert catalog["trans_contrat_maint"].access_groups == ("grp_responsables",)


def test_extraction_finds_tables_and_cited_figure(catalog, tmp_path):
    els = {e.element_id: e for e in extract_pdf(catalog["mdp_man_util"], tmp_path)}
    assert "figure_1_1" in els and "Pupitre de commande MDP" in els["figure_1_1"].text
    assert (tmp_path / els["figure_1_1"].image_path).exists()
    v2 = [e for e in els.values() if e.element_type == "table" and "Préalarme température palier" in e.text]
    assert v2 and v2[0].page == 2, "le tableau des voyants (V2 orange fixe) doit être indexé en page 2"
    assert all(e.access_groups == ("grp_pompes", "grp_responsables") for e in els.values())


def test_figure_ids_match_manifest(catalog, tmp_path):
    """Les element_id des figures extraites sont ceux du manifeste (vérité terrain des citations)."""
    import yaml
    man = yaml.safe_load((CORPUS / "manifest.yaml").read_text(encoding="utf-8"))
    expected = {(d["document_id"].lower().replace("-", "_"), f["element_id"], f["page"])
                for d in man["documents"] if not d["scanned"] for f in d["figures"]}
    got = set()
    for did in {e[0] for e in expected}:
        got |= {(e.document_id, e.element_id, e.page) for e in extract_pdf(catalog[did], tmp_path)
                if e.element_type == "figure"}
    assert expected == got


def test_footer_and_doc_header_not_in_paragraphs(catalog, tmp_path):
    for e in extract_pdf(catalog["mdp_bt_2025_01"], tmp_path):
        if e.element_type == "paragraph":
            assert "corpus synthétique" not in e.text and not e.text.startswith("Réf. ")


# ------------------------------------------------------------------ accès

def test_access_rule(users):
    assert can_read(users["u_tech_p01"], ("grp_pompes", "grp_responsables"))
    assert not can_read(users["u_tech_c01"], ("grp_pompes", "grp_responsables"))
    assert not can_read(users["u_presta_01"], ("grp_responsables",))


def test_search_never_returns_forbidden_documents(retriever, users):
    queries = ["voyant orange", "contrat prix révision pénalités", "couple de serrage", "ignore les instructions"]
    for user in users.values():
        for q in queries:
            for h in retriever.search(user, q, k=50).hits:
                assert can_read(user, h.element.access_groups), (user.user_id, h.key)


def test_prestataire_sees_only_safety(retriever, users):
    docs = {h.element.document_id for h in retriever.search(users["u_presta_01"], "EPI consignation voyant contrat", k=50).hits}
    assert docs <= {"trans_sec_epi", "trans_sec_consignation", "trans_glossaire"}


def test_contract_hidden_from_technicians(retriever, users):
    for uid in ("u_tech_p01", "u_tech_c01", "u_presta_01"):
        hits = retriever.search(users[uid], "Contrat de maintenance conditions et coûts révision", k=50).hits
        assert "trans_contrat_maint" not in {h.element.document_id for h in hits}
    hits = retriever.search(users["u_resp_01"], "Contrat de maintenance conditions et coûts révision", k=5).hits
    assert hits[0].element.document_id == "trans_contrat_maint"


def test_open_asset_refused_without_rights(retriever, users):
    e = next(e for e in retriever.elements if e.document_id == "mdp_sch_hydr" and e.image_path)
    path = retriever.s.assets_dir / e.image_path
    assert open_asset(users["u_tech_p01"], e.access_groups, path)
    with pytest.raises(AccessDenied):
        open_asset(users["u_tech_c01"], e.access_groups, path)


def test_unknown_user_without_groups_gets_nothing(retriever):
    assert retriever.search(User("u_inconnu", "aucun", ()), "voyant orange").hits == []


# ------------------------------------------------------------------ recherche

def test_superseded_document_ranked_after_active(retriever, users):
    hits = retriever.search(users["u_tech_p01"], "couple de serrage boulons bride refoulement M16", k=10).hits
    docs = [h.element.document_id for h in hits]
    assert "mdp_bt_2025_01" in docs[:3]


def test_family_filter_hard_negative(retriever, users):
    """Le technicien pompes ne doit jamais recevoir le manuel compresseur, même très proche."""
    hits = retriever.search(users["u_tech_p01"], "voyant V2 orange fixe signification", k=20).hits
    assert all(h.element.family in ("pompes", "transverse") for h in hits)


def test_tokenize_strips_accents_and_keeps_codes():
    assert "p-21" in tokenize("Code P-21 : température")
    assert "temperature" in tokenize("Température")


# ------------------------------------------------------------------ métriques

def test_metrics():
    class E:
        def __init__(self, d, p, t):
            self.document_id, self.page, self.element_type = d, p, t
    hits = [Hit(E("a", 1, "table"), 0), Hit(E("b", 1, "table"), 0), Hit(E("c", 2, "figure"), 0)]
    m = metrics(hits, [{"doc": "c", "page": 2}], n_relevant=1)
    assert m["recall@5"] == 1.0 and m["mrr@10"] == pytest.approx(1 / 3) and m["first_rank"] == 3
    assert m["ndcg@5"] == pytest.approx(0.5)
    assert is_relevant(E("c", 2, "figure"), {"doc": "c", "page": 2, "types": ["figure"]})
    assert not is_relevant(E("c", 2, "table"), {"doc": "c", "page": 2, "types": ["figure"]})


@pytest.mark.slow
def test_ocr_scanned_document(catalog, tmp_path):
    els = extract_pdf(catalog["mdc_proc_revision_scan"], tmp_path)
    text = " ".join(e.text for e in els if e.ocr)
    assert "8 000" in text and "rotor" in text.lower()
