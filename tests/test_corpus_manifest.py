from pathlib import Path

import pytest
from pydantic import ValidationError

from maintidoc.corpus.schema import DocumentEntry
from maintidoc.corpus.validate import check_manifest, load_manifest

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(CORPUS / "manifest.yaml")


def test_generated_manifest_is_valid(manifest):
    assert check_manifest(manifest, corpus_root=CORPUS) == []


def test_scenario_documents_exist(manifest):
    by_id = {d.document_id: d for d in manifest.documents}
    assert by_id["MDP-BT-2024-03"].status == "superseded"
    assert by_id["MDP-BT-2025-01"].supersedes == "MDP-BT-2024-03"
    assert by_id["TRANS-CONTRAT-MAINT"].access_groups == ["grp_responsables"]
    assert "injection" in by_id["TRANS-NOTE-INJ"].test_flags
    assert by_id["MDC-PROC-REVISION-SCAN"].scanned
    assert by_id["MDP-MAN-UTIL"].figures[0].element_id.startswith("figure_")


def _entry(**overrides):
    base = dict(document_id="MDP-TEST", title="Document de test", version="1.0", date_published="2025-01-01",
                doc_type="procedure", equipment_family="MDP", equipment_models=["MDP-200"],
                access_groups=["grp_pompes"], confidentiality="interne", status="active", language="fr",
                source="synthetique", scanned=False, file="pdf/x.pdf", sha256="0" * 64, pages=1, figures=[],
                test_flags=[])
    base.update(overrides)
    return base


def test_superseded_requires_target():
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(_entry(status="superseded"))


def test_restricted_document_only_for_managers():
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(_entry(confidentiality="restreint", access_groups=["grp_pompes"]))


def test_unknown_group_rejected():
    with pytest.raises(ValidationError):
        DocumentEntry.model_validate(_entry(access_groups=["grp_admin"]))


def test_cross_family_group_is_reported(manifest):
    leaky = manifest.model_copy(deep=True)
    leaky.documents[0].access_groups.append("grp_compresseurs")
    errors = check_manifest(leaky)
    assert any("groupe non autorisé" in e for e in errors)


def test_contractor_cannot_read_technical_docs(manifest):
    leaky = manifest.model_copy(deep=True)
    leaky.documents[0].access_groups.append("grp_prestataires")
    assert any("prestataires" in e for e in check_manifest(leaky))


def test_tampered_file_is_detected(manifest):
    tampered = manifest.model_copy(deep=True)
    tampered.documents[0].sha256 = "f" * 64
    assert any("SHA-256" in e for e in check_manifest(tampered, corpus_root=CORPUS))
