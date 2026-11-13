"""Construit le livrable 1 MaintiDoc (dépôt + dossier ZIP à rendre).

Usage : python livrable/build_livrable1.py
Prérequis : python corpus/generate_corpus.py (corpus/pdf, corpus/photos, corpus/manifest.yaml).

Produit :
  - dans le dépôt : corpus/documents/{famille_1,famille_2,transverse}/, corpus/images/,
    corpus/inventaire.csv, corpus/prompts_corpus.md, docs/diagrammes/*.mmd
  - livrable/L1_MaintiDoc_<NomEquipe>/ (rapport PDF, lien GitHub, README, corpus) et le ZIP.
"""

import csv
import json
import shutil
import sys
import unicodedata
import zipfile
from pathlib import Path

import pymupdf as fitz
import yaml

ROOT = Path(__file__).resolve().parents[1]
LIV = ROOT / "livrable"
CORPUS = ROOT / "corpus"
sys.path.insert(0, str(CORPUS))
sys.path.insert(0, str(LIV))

import content_mdc  # noqa: E402
import content_mdp  # noqa: E402
import content_trans  # noqa: E402

FAMILLES = {"MDP": ("pompes", "famille_1"), "MDC": ("compresseurs", "famille_2"),
            "TRANSVERSE": ("transverse", "transverse")}
TYPE_MAP = {  # type interne -> valeur imposée par la consigne (type précis conservé dans remarques)
    "manuel": "manuel", "procedure": "procedure", "schema": "schema", "fiche_alarmes": "codes_alarme",
    "guide_depannage": "codes_alarme", "fiche_pieces": "schema", "bulletin": "procedure",
    "checklist": "procedure", "note": "procedure", "securite": "fiche_securite", "glossaire": "manuel",
    "contrat": "procedure", "historique": "historique", "photo": "photo",
}
TYPE_LABEL = {"guide_depannage": "guide de dépannage", "fiche_pieces": "vue éclatée / pièces détachées",
              "bulletin": "bulletin technique", "checklist": "check-list d'inspection", "note": "note technique",
              "glossaire": "glossaire", "contrat": "contrat de maintenance (confidentiel)"}
# Équipements du parc (data/fixtures/equipment.yaml) par modèle
EQUIP = yaml.safe_load((ROOT / "data/fixtures/equipment.yaml").read_text(encoding="utf-8"))["equipment"]

# Prompt (prompts_corpus.md) ayant servi à générer chaque document
PROMPT_OF = {
    "MAN-UTIL": "P04", "MAN-MAINT": "P05", "FICHE-ALARMES": "P06", "GUIDE-DEPANNAGE": "P06",
    "SCH-": "P07", "PIECES": "P07", "PROC-": "P08", "CHECKLIST": "P08", "NOTE-": "P08", "BT-": "P09",
    "TRANS-NOTE-INJ": "P10", "TRANS-": "P11",
}
CORRECTIONS = {
    "MDP-MAN-UTIL": "vannes renommées V1/V2 -> VA1/VR1 (confusion avec les voyants V1/V2) p.1-2",
    "MDP-FICHE-ALARMES": "code P-30 : « vanne V1 » -> « vanne VA1 » (confusion avec le voyant V1)",
    "MDP-SCH-HYDR": "repères de vannes V1/V2 -> VA1/VR1 sur la figure 1 et la nomenclature",
    "MDP-PROC-AMORCAGE": "« Ouvrir V1 » -> « Ouvrir VA1 » (vanne d'aspiration)",
    "MDP-PROC-CONSIGNATION": "« cadenasser V1 et V2 » -> « VA1 et VR1 » (vannes, pas voyants)",
    "MDP-BT-2024-03": "version papier numérisée ajoutée (2e document scanné pour l'OCR)",
}
REMARQUES = {
    "MDP-MAN-UTIL": "V2 orange fixe = préalarme température palier (tableau p.1) ; jumeau visuel de mdc_man_util",
    "MDC-MAN-UTIL": "V2 orange fixe = filtre à air colmaté ; jumeau visuel de mdp_man_util (négatif difficile)",
    "MDP-MAN-MAINT": "contient encore 45 N·m pour la bride, contredit mdp_bt_2025_01 (60 N·m)",
    "MDP-BT-2024-03": "remplacé par mdp_bt_2025_01 (45 -> 60 N·m) ; document scanné sans couche texte",
    "MDP-BT-2025-01": "version active du couple de serrage de bride (60 N·m)",
    "MDC-MAN-MAINT": "vidange 4 000 h, contredit mdc_proc_vidange (2 000 h)",
    "MDC-PROC-VIDANGE": "vidange 2 000 h, contredit mdc_man_maint (4 000 h)",
    "MDC-PROC-REVISION-SCAN": "document scanné sans couche texte (test OCR)",
    "TRANS-CONTRAT-MAINT": "accès restreint aux responsables (test de fuite inter-groupes)",
    "TRANS-NOTE-INJ": "contient une instruction malveillante p.1 (exfiltration + élévation de droits)",
}
USAGE_OF_FLAG = {"injection": "injection", "contradiction": "contradictoire", "superseded": "contradictoire",
                 "hard_negative": "ambigu", "ambiguous": "ambigu"}


def load_cfg():
    cfg = yaml.safe_load((LIV / "equipe.yaml").read_text(encoding="utf-8"))
    def clean(s):
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return s.upper().replace(" ", "").replace("'", "")
    cfg["nom_equipe"] = "-".join(sorted(clean(m["nom"]) for m in cfg["membres"]))
    return cfg


def reviewer(cfg, family):
    m = cfg["membres"]
    idx = {"MDP": 0, "MDC": 1, "TRANSVERSE": 2}[family]
    return m[min(idx, len(m) - 1)]["prenom"]


def doc_id(manifest_id):
    return manifest_id.lower().replace("-", "_")


def equipment_ids(family, models):
    if family == "TRANSVERSE":
        return "tous"
    return " ; ".join(e["equipment_id"] for e in EQUIP if e["family"] == family and e["model"] in models)


def table_pages(src_pdf, blocks, scanned):
    """Page de chaque tableau : recherche de l'en-tête dans le PDF (page 1 pour un scan)."""
    pages = []
    with fitz.open(src_pdf) as pdf:
        for b in blocks:
            if b[0] != "table":
                continue
            first, last = str(b[1][0][0]), str(b[1][0][-1])
            found = None if scanned else next(
                (i + 1 for i, p in enumerate(pdf) if p.search_for(first) and p.search_for(last)), None)
            pages.append(found or 1)
    return pages


def visuals(m_doc, content_doc):
    parts = []
    for f in m_doc["figures"]:
        num = f["caption"].split(" — ")[0].replace("Figure ", "fig ")
        parts.append(f"{num} p.{f['page']} ({f['caption'].split(' — ', 1)[1]})")
    for p in table_pages(CORPUS / m_doc["file"], content_doc["blocks"], m_doc["scanned"]):
        parts.append(f"tableau p.{p}")
    return " ; ".join(parts) or "aucun"


def prompt_for(mid):
    if mid == "TRANS-NOTE-INJ":
        return "P10"
    if mid.startswith("TRANS-"):
        return "P11"
    for key, p in PROMPT_OF.items():
        if key in mid:
            return p
    return "P08"


def usage(flags):
    for f in flags:
        if f in USAGE_OF_FLAG:
            return USAGE_OF_FLAG[f]
    return "normal"


# ------------------------------------------------------------------ historiques d'interventions (PDF)

def build_histories(out_dir_by_family):
    from reportlab import rl_config
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    rl_config.invariant = 1
    if "H" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("H", "C:/Windows/Fonts/arial.ttf"))
        pdfmetrics.registerFont(TTFont("H-B", "C:/Windows/Fonts/arialbd.ttf"))
    data = json.loads((ROOT / "data/fixtures/interventions.json").read_text(encoding="utf-8"))
    eq_family = {e["equipment_id"]: e["family"] for e in EQUIP}
    st = ParagraphStyle("c", fontName="H", fontSize=8.5, leading=11)
    out = {}
    for fam, label in [("MDP", "pompes MDP"), ("MDC", "compresseurs MDC")]:
        rows = [i for i in data["interventions"] if eq_family[i["equipment_id"]] == fam]
        tickets = [t for t in data.get("open_tickets", []) if eq_family.get(t.get("equipment_id")) == fam]
        did = f"historique_interventions_{fam.lower()}"
        path = out_dir_by_family[fam] / f"{did}.pdf"
        story = [Paragraph(f"Historique des interventions — {label}", ParagraphStyle("t", fontName="H-B", fontSize=15)),
                 Spacer(1, 6),
                 Paragraph("Extraction du service de maintenance de démonstration (données FICTIVES, identiques à "
                           "celles exposées par le serveur MCP). Réf. " + did.upper() + " v1.0 — 2026-10-23.", st),
                 Spacer(1, 10)]
        tab = [["Intervention", "Équipement", "Date", "Type", "Résumé", "Description", "Technicien"]]
        tab += [[i["intervention_id"], i["equipment_id"], i["date"], i["type"], i["summary"], i["description"],
                 i["technician"]] for i in rows]
        t = Table([[Paragraph(str(c), st) for c in r] for r in tab], repeatRows=1,
                  colWidths=[2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 4.5 * cm, 9 * cm, 2.6 * cm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf5")),
                               ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9aa7b5")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t)
        if tickets:
            story += [Spacer(1, 10), Paragraph("Tickets ouverts", ParagraphStyle("h", fontName="H-B", fontSize=11)),
                      Spacer(1, 4)]
            for tk in tickets:
                story.append(Paragraph(" — ".join(f"{k} : {v}" for k, v in tk.items()), st))
        SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                          topMargin=1.5 * cm, bottomMargin=1.5 * cm, title=f"Historique {label}",
                          author="MaintiDoc (synthétique)").build(story)
        with fitz.open(path) as pdf:
            npages = pdf.page_count
        inj = any("INT-0009" == i["intervention_id"] for i in rows)
        out[fam] = dict(did=did, path=path, label=label, pages=npages, n=len(rows), ntk=len(tickets),
                        equip=" ; ".join(sorted({i["equipment_id"] for i in rows})), injection=inj)
    return out


# ------------------------------------------------------------------ corpus + inventaire

COLUMNS = ["document_id", "fichier", "titre", "famille_equipement", "equipement_id", "type_document", "version",
           "nb_pages", "langue", "format", "elements_visuels", "provenance", "licence", "genere_par_ia", "outil_ia",
           "verifie_par", "corrections", "groupe_acces", "usage_test", "remarques"]
OUTIL = "Claude Code - Claude Opus"


def build_corpus(cfg):
    manifest = yaml.safe_load((CORPUS / "manifest.yaml").read_text(encoding="utf-8"))
    contents = {d["id"]: d for d in content_mdp.DOCS + content_mdc.DOCS + content_trans.DOCS}
    docs_dir = CORPUS / "documents"
    img_dir = CORPUS / "images"
    for d in (docs_dir, img_dir):
        if d.exists():
            shutil.rmtree(d)
    dirs = {}
    for fam, (_, sub) in FAMILLES.items():
        dirs[fam] = docs_dir / sub
        dirs[fam].mkdir(parents=True)
    img_dir.mkdir()

    rows = []
    for m in manifest["documents"]:
        c = contents[m["document_id"]]
        did = doc_id(m["document_id"])
        fam = m["equipment_family"]
        dest = dirs[fam] / f"{did}.pdf"
        shutil.copy2(CORPUS / m["file"], dest)
        typ = m["doc_type"]
        rem = [REMARQUES.get(m["document_id"], "")]
        if typ in TYPE_LABEL:
            rem.insert(0, f"type précis : {TYPE_LABEL[typ]}")
        rem.append(f"identifiant interne {m['document_id']}")
        if "restricted" in m["test_flags"]:
            rem.append("test d'accès restreint")
        rows.append({
            "document_id": did, "fichier": dest.relative_to(CORPUS).as_posix(), "titre": m["title"],
            "famille_equipement": FAMILLES[fam][0], "equipement_id": equipment_ids(fam, m["equipment_models"]),
            "type_document": TYPE_MAP[typ], "version": f"v{m['version']} ({m['date_published'][:7]})",
            "nb_pages": m["pages"], "langue": m["language"], "format": "pdf_scanne" if m["scanned"] else "pdf_texte",
            "elements_visuels": visuals(m, c), "provenance": "synthetique", "licence": "synthetique",
            "genere_par_ia": "oui", "outil_ia": f"{OUTIL} (prompt {prompt_for(m['document_id'])})",
            "verifie_par": reviewer(cfg, fam), "corrections": CORRECTIONS.get(m["document_id"], "aucune"),
            "groupe_acces": " ; ".join(m["access_groups"]), "usage_test": usage(m["test_flags"]),
            "remarques": " ; ".join(r for r in rem if r),
        })

    hist = build_histories(dirs)
    for fam, h in hist.items():
        grp = {"MDP": "grp_pompes ; grp_responsables", "MDC": "grp_compresseurs ; grp_responsables"}[fam]
        rows.append({
            "document_id": h["did"], "fichier": h["path"].relative_to(CORPUS).as_posix(),
            "titre": f"Historique des interventions — {h['label']}", "famille_equipement": FAMILLES[fam][0],
            "equipement_id": h["equip"], "type_document": "historique", "version": "v1.0 (2026-10)",
            "nb_pages": h["pages"], "langue": "fr", "format": "pdf_texte",
            "elements_visuels": "tableau p.1", "provenance": "synthetique", "licence": "synthetique",
            "genere_par_ia": "oui", "outil_ia": f"{OUTIL} (prompt P13)", "verifie_par": reviewer(cfg, fam),
            "corrections": "aucune", "groupe_acces": grp,
            "usage_test": "injection" if h["injection"] else "normal",
            "remarques": (f"{h['n']} interventions, {h['ntk']} ticket(s) ouvert(s) ; mêmes données que le serveur MCP"
                          + (" ; INT-0009 contient une injection dans la description" if h["injection"] else "")),
        })

    photo_meta = {
        "photo_pupitre_mdp_orange_nette": ("Pupitre pompe MDP-200 — V2 orange fixe (photo nette)", "normal",
                                           "voyants V1 vert et V2 orange allumés ; plaque lisible", "scénario nominal"),
        "photo_pupitre_mdc_orange_nette": ("Pupitre compresseur MDC-55 — V2 orange fixe (photo nette)", "ambigu",
                                           "voyants V1 vert et V2 orange allumés ; plaque lisible",
                                           "même aspect que la photo MDP, sens différent (négatif difficile)"),
        "photo_pupitre_ambigu_floue": ("Pupitre non identifiable — photo floue et inclinée", "ambigu",
                                       "voyant orange visible ; plaque illisible", "doit déclencher une clarification"),
        "photo_pupitre_mdc_rouge": ("Pupitre compresseur MDC-90 — V3 rouge allumé", "ambigu",
                                    "voyant V3 rouge ; plaque lisible ; code AF1 non visible",
                                    "doit demander le code affiché"),
        "photo_pupitre_injection_etiquette": ("Pupitre pompe MDP-350 avec étiquette collée", "injection",
                                              "voyant V1 vert ; étiquette manuscrite lisible par OCR",
                                              "l'étiquette contient une instruction malveillante (création de tickets)"),
    }
    for p in manifest["photos"]:
        title, use, vis, rem = photo_meta[p["photo_id"]]
        fam = p["equipment_family"]
        dest = img_dir / f"{p['photo_id']}.png"
        shutil.copy2(CORPUS / p["file"], dest)
        grp = {"MDP": "grp_pompes ; grp_responsables", "MDC": "grp_compresseurs ; grp_responsables"}[fam]
        rows.append({
            "document_id": p["photo_id"], "fichier": dest.relative_to(CORPUS).as_posix(), "titre": title,
            "famille_equipement": FAMILLES[fam][0], "equipement_id": p["equipment_id"] or "non identifiable",
            "type_document": "photo", "version": "v1.0 (2026-10)", "nb_pages": 1, "langue": "fr", "format": "image",
            "elements_visuels": vis, "provenance": "synthetique", "licence": "synthetique", "genere_par_ia": "oui",
            "outil_ia": f"{OUTIL} (prompt P12)", "verifie_par": reviewer(cfg, fam),
            "corrections": "aucune", "groupe_acces": grp, "usage_test": use,
            "remarques": f"{rem} ; rendu synthétique (script), aucune personne visible",
        })

    with open(CORPUS / "inventaire.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    # Contrôle : chaque fichier de documents/ et images/ figure dans l'inventaire, et inversement
    on_disk = {p.relative_to(CORPUS).as_posix() for p in (CORPUS / "documents").rglob("*") if p.is_file()}
    on_disk |= {p.relative_to(CORPUS).as_posix() for p in img_dir.iterdir()}
    listed = {r["fichier"] for r in rows}
    assert on_disk == listed, (on_disk ^ listed)
    assert len({r["document_id"] for r in rows}) == len(rows)
    for r in rows:
        assert Path(r["fichier"]).stem == r["document_id"], r
    return rows


# ------------------------------------------------------------------ prompts, diagrammes, README

def write_readme(cfg, target, zip_mode):
    team = cfg["nom_equipe"]
    membres = "\n".join(f"| {m['prenom']} {m['nom']} | {m['role']} |" for m in cfg["membres"])
    corpus_dir = f"L1_MaintiDoc_{team}_Corpus/" if zip_mode else "corpus/"
    txt = f"""# MaintiDoc — Livrable 1 : cadrage, corpus et architecture

Module IA générative multimodale — EMSI 2026. Équipe **{team}**.

| Membre | Rôle |
|---|---|
{membres}

## Objectif du projet

MaintiDoc est un assistant documentaire multimodal et agentique pour la maintenance de deux familles
d'équipements fictives : **pompes centrifuges MDP** et **compresseurs d'air à vis MDC**. Il répond en
français à une question, éventuellement accompagnée d'une photo de pupitre, en citant la page et la figure
du document source ; il consulte l'historique des interventions via un outil MCP et prépare un ticket dont
la création exige une **approbation humaine**. Il ne pilote aucune machine et ne garantit aucun diagnostic.

## Contenu du ZIP

| Élément | Contenu |
|---|---|
| `L1_MaintiDoc_{team}_Rapport.pdf` | Rapport : cadrage, corpus, architecture, flux, risques, planning |
| `L1_MaintiDoc_{team}_LienGitHub.txt` | URL du dépôt GitHub |
| `README.md` | Ce fichier |
| `L1_MaintiDoc_{team}_Corpus/` | 47 éléments : 42 PDF (dont 2 scannés) + 5 photos, `inventaire.csv`, `prompts_corpus.md` |

Corpus : `documents/famille_1/` (pompes, 19 PDF), `documents/famille_2/` (compresseurs, 18 PDF),
`documents/transverse/` (sécurité, glossaire, procédure tickets, contrat, note piégée : 6 PDF — rattachés
aux deux familles), `images/` (5 photos de pupitres). Tous les documents sont **synthétiques** (aucune donnée réelle).

## Structure du dépôt

```
maintidoc/
├── README.md, PLAN.md, pyproject.toml, docker-compose.yml, .env.example, .gitignore
├── docs/                 01_cadrage … 05_donnees (.md) + diagrammes/ (sources Mermaid)
├── corpus/
│   ├── inventaire.csv, prompts_corpus.md, manifest.yaml
│   ├── documents/famille_1/, famille_2/, transverse/
│   ├── images/
│   └── generate_corpus.py, content_*.py, figures.py   (générateur déterministe)
├── data/fixtures/        utilisateurs, parc, historique et tickets fictifs (serveur MCP)
├── datasets/             jeu d'adaptation du reranker (semaine 5)
├── livrable/             script de construction de ce livrable
├── src/maintidoc/        code (validation du corpus en semaine 1)
└── tests/                tests automatisés (pytest)
```

Régénérer : `python corpus/generate_corpus.py` puis `python livrable/build_livrable1.py`.
"""
    (target / "README.md").write_text(txt, encoding="utf-8")
    del corpus_dir


def write_diagrams():
    out = ROOT / "docs" / "diagrammes"
    out.mkdir(parents=True, exist_ok=True)
    from diagrammes_mermaid import DIAGRAMS
    for name, src in DIAGRAMS.items():
        (out / f"{name}.mmd").write_text(src.strip() + "\n", encoding="utf-8")


def main():
    cfg = load_cfg()
    team = cfg["nom_equipe"]
    rows = build_corpus(cfg)
    shutil.copy2(LIV / "prompts_corpus.md", CORPUS / "prompts_corpus.md")
    write_diagrams()
    write_readme(cfg, ROOT / "livrable", zip_mode=True)

    base = LIV / f"L1_MaintiDoc_{team}"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir()
    cdir = base / f"L1_MaintiDoc_{team}_Corpus"
    cdir.mkdir()
    for sub in ("documents", "images"):
        shutil.copytree(CORPUS / sub, cdir / sub)
    for f in ("inventaire.csv", "prompts_corpus.md"):
        shutil.copy2(CORPUS / f, cdir / f)
    shutil.move(str(LIV / "README.md"), base / "README.md")
    link = cfg["github_url"].strip() + ("\n" + cfg["lien_corpus"].strip() if cfg.get("lien_corpus") else "") + "\n"
    (base / f"L1_MaintiDoc_{team}_LienGitHub.txt").write_text(link, encoding="utf-8")

    import rapport_l1
    rapport_l1.build(cfg, rows, base / f"L1_MaintiDoc_{team}_Rapport.pdf")

    zpath = LIV / f"L1_MaintiDoc_{team}.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob("*")):
            z.write(p, p.relative_to(LIV).as_posix())
    print(f"{len(rows)} éléments dans l'inventaire")
    print(f"Livrable : {base}")
    print(f"ZIP      : {zpath} ({zpath.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
