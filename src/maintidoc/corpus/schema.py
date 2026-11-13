"""Schéma Pydantic du manifeste de corpus (corpus/manifest.yaml)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AccessGroup = Literal["grp_pompes", "grp_compresseurs", "grp_responsables", "grp_prestataires"]
Family = Literal["MDP", "MDC", "TRANSVERSE"]
DocType = Literal["manuel", "procedure", "schema", "fiche_alarmes", "fiche_pieces", "bulletin",
                  "checklist", "guide_depannage", "note", "securite", "glossaire", "contrat"]
TestFlag = Literal["injection", "contradiction", "superseded", "restricted", "ocr", "hard_negative",
                   "nominal", "ambiguous", "clarification"]

ID_PATTERN = r"^(MDP|MDC|TRANS)(-[A-Z0-9]+)+$"


class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str = Field(pattern=r"^figure_\d+_\d+$")
    page: int = Field(ge=1)
    caption: str = Field(min_length=5)


class DocumentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=5)
    version: str = Field(pattern=r"^\d+\.\d+$")
    date_published: date
    doc_type: DocType
    equipment_family: Family
    equipment_models: list[str]
    access_groups: list[AccessGroup] = Field(min_length=1)
    confidentiality: Literal["interne", "restreint"]
    status: Literal["active", "superseded"]
    supersedes: str | None = None
    superseded_by: str | None = None
    language: Literal["fr"]
    source: Literal["synthetique", "autorise"]
    scanned: bool
    file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pages: int = Field(ge=1)
    figures: list[Figure]
    test_flags: list[TestFlag]

    @model_validator(mode="after")
    def check_consistency(self):
        if self.status == "superseded" and not self.superseded_by:
            raise ValueError(f"{self.document_id}: un document remplacé doit indiquer superseded_by")
        if self.status == "active" and self.superseded_by:
            raise ValueError(f"{self.document_id}: un document actif ne peut pas être remplacé")
        if any(f.page > self.pages for f in self.figures):
            raise ValueError(f"{self.document_id}: figure hors des pages du document")
        if self.equipment_family != "TRANSVERSE":
            if not self.document_id.startswith(self.equipment_family):
                raise ValueError(f"{self.document_id}: préfixe incohérent avec la famille")
            if not self.equipment_models:
                raise ValueError(f"{self.document_id}: modèles d'équipement manquants")
        if self.confidentiality == "restreint" and set(self.access_groups) != {"grp_responsables"}:
            raise ValueError(f"{self.document_id}: un document restreint est réservé à grp_responsables")
        return self


class PhotoEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    photo_id: str = Field(pattern=r"^photo_[a-z0-9_]+$")
    file: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    equipment_family: Literal["MDP", "MDC"]
    equipment_id: str | None = Field(default=None, pattern=r"^EQ-[PC]-\d{3}$")
    description: str
    expected_behaviour: str
    test_flags: list[TestFlag]


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corpus_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    generator: str
    seed: int
    documents: list[DocumentEntry]
    photos: list[PhotoEntry]
