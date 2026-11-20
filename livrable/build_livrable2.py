"""Construit le livrable 2 MaintiDoc (semaine 2 : ingestion, recherche texte + image, gestion des accès).

Prérequis : index réel construit et évaluation lancée
  python -m maintidoc.ingestion.pipeline
  python -m maintidoc.evaluation.retrieval_eval
Usage : python livrable/build_livrable2.py
Produit livrable/L2_MaintiDoc_<NomEquipe>/ (rapport PDF, lien GitHub, README) et le ZIP.
"""

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIV = ROOT / "livrable"
sys.path.insert(0, str(LIV))
sys.path.insert(0, str(ROOT / "src"))

from build_livrable1 import load_cfg  # noqa: E402


def git_info():
    def g(*args):
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            return ""
    return {"commit": g("rev-parse", "--short", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD")}


def write_readme(cfg, target: Path, results: dict, index: dict):
    team = cfg["nom_equipe"]
    best = max(results["summary"].items(), key=lambda kv: kv[1]["ndcg@5"])
    membres = "\n".join(f"- {m['prenom']} {m['nom']}" + (f" — {m['role']}" if m.get("role") else "")
                        for m in cfg["membres"])
    txt = f"""# MaintiDoc — Livrable 2 : ingestion, recherche texte et image, gestion des accès

Module IA générative multimodale — EMSI 2026. Équipe **{team}**. Dépôt : {cfg['github_url']}

Membres :

{membres}

## Ce que fait le code de la semaine 2

- **Ingestion** des {index['documents']} éléments du corpus en **{index['elements']} éléments citables**
  (paragraphes, tableaux, figures, pages, texte OCR, photos), avec document, version, page, `element_id`,
  famille, statut et groupes d'accès. OCR local pour les 2 documents scannés et les photos.
- **Recherche hybride** : BM25 + embeddings BGE-M3 + recherche visuelle CLIP (requête texte ou photo),
  fusion RRF pondérée, reranker d'origine optionnel.
- **Services Docker Compose** : Qdrant (vecteurs), PostgreSQL (métadonnées, journal d'accès), stockage S3
  SeaweedFS (pages, figures, photos ; remplace MinIO, dont l'image n'est plus téléchargeable).
- **Contrôle d'accès** avant récupération (filtre dans la requête Qdrant), re-contrôle des résultats et
  à l'ouverture des images ; journal d'accès sans contenu.
- **Évaluation** sur 30 questions pilotes annotées : meilleure configuration `{best[0]}` —
  Recall@5 {best[1]['recall@5']:.2f}, nDCG@5 {best[1]['ndcg@5']:.2f}, MRR@10 {best[1]['mrr@10']:.2f} ;
  **{results['access']['leaks']} fuite** entre groupes sur {results['access']['verified_results']} résultats vérifiés.

## Reproduire

```bash
python -m venv .venv && .venv\\Scripts\\activate          # Linux/macOS : source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[corpus,retrieval,dev]"
copy .env.example .env    # puis renseigner les mots de passe (jamais commités)
docker compose up -d postgres qdrant s3
python corpus/generate_corpus.py && python livrable/build_livrable1.py     # corpus + inventaire
python -m maintidoc.ingestion.pipeline                                     # index (~10 min CPU)
python -m maintidoc.evaluation.retrieval_eval                              # reports/semaine2/
python -m maintidoc.retrieval.cli --user u_tech_p01 "Que signifie le voyant V2 orange fixe ?"
pytest                      # tests rapides, sans services
pytest -m services          # intégration Docker
```

## Contenu du ZIP

| Élément | Contenu |
|---|---|
| `L2_MaintiDoc_{team}_Rapport.pdf` | Rapport de la semaine 2 |
| `L2_MaintiDoc_{team}_LienGitHub.txt` | URL du dépôt |
| `README.md` | Ce fichier |

## Nouveaux éléments du dépôt

```
src/maintidoc/catalog.py, config.py, access.py
src/maintidoc/ingestion/   extract.py, ocr.py, elements.py, pipeline.py
src/maintidoc/retrieval/   encoders.py, index.py, search.py, cli.py
src/maintidoc/evaluation/  retrieval_eval.py
data/eval/pilot_questions.yaml          30 questions annotées
reports/semaine2/                       résultats (JSON, CSV)
docs/06_ingestion_recherche.md          documentation technique
src/maintidoc/storage.py                PostgreSQL / S3 (ou SQLite / dossier local)
tests/test_ingestion_retrieval.py       14 tests (accès, extraction, recherche, métriques)
tests/test_services.py                  3 tests d'intégration Docker
requirements.lock, config/models.lock.yaml   versions figées
```
"""
    (target / "README.md").write_text(txt, encoding="utf-8")


def main():
    cfg = load_cfg()
    team = cfg["nom_equipe"]
    results = json.loads((ROOT / "reports/semaine2/retrieval_results.json").read_text(encoding="utf-8"))
    index = json.loads((ROOT / "data/index/index_manifest.json").read_text(encoding="utf-8"))
    base = LIV / f"L2_MaintiDoc_{team}"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir()
    write_readme(cfg, base, results, index)
    (base / f"L2_MaintiDoc_{team}_LienGitHub.txt").write_text(cfg["github_url"].strip() + "\n", encoding="utf-8")
    import rapport_l2
    rapport_l2.build(cfg, results, index, git_info(), base / f"L2_MaintiDoc_{team}_Rapport.pdf")
    zpath = LIV / f"L2_MaintiDoc_{team}.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob("*")):
            z.write(p, p.relative_to(LIV).as_posix())
    print(f"Livrable : {base}\nZIP      : {zpath} ({zpath.stat().st_size / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
