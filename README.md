# MaintiDoc

Assistant documentaire multimodal et agentique pour la maintenance : recherche documentaire, analyse d'images, outils MCP et réponses sourcées.

> Aide documentaire uniquement. MaintiDoc ne pilote aucun équipement, ne garantit aucun diagnostic et ne remplace ni les procédures de sécurité ni un technicien habilité. Toutes les données du dépôt sont fictives.

## État d'avancement

Semaine 1 terminée (cadrage, corpus, architecture, risques). Voir [PLAN.md](PLAN.md).

| Document | Contenu |
|---|---|
| [docs/01_cadrage.md](docs/01_cadrage.md) | Objectifs, périmètre, utilisateurs, droits, scénarios |
| [docs/02_architecture.md](docs/02_architecture.md) | Diagrammes, flux, choix techniques, licences |
| [docs/03_analyse_risques.md](docs/03_analyse_risques.md) | Registre des risques, modèle de menaces |
| [docs/04_corpus.md](docs/04_corpus.md) | Composition du corpus, pièges, métadonnées |
| [docs/05_donnees.md](docs/05_donnees.md) | Sources externes évaluées (licences), jeu d'adaptation du reranker |

## Démarrage rapide

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate   —   Linux/macOS : source .venv/bin/activate
pip install -e ".[corpus,dev]"

python corpus/generate_corpus.py                        # génère 40 PDF, 5 photos, le manifeste
python -m maintidoc.corpus.validate corpus/manifest.yaml
python datasets/build_reranker_dataset.py             # 1 012 triplets pour le reranker
pytest
```

Infrastructure (à partir de la semaine 2) :

```bash
cp .env.example .env    # puis renseigner les secrets localement
docker compose up -d    # PostgreSQL, Qdrant, MinIO, MLflow
```

## Arborescence

```
docs/            cadrage, architecture, risques, corpus
corpus/          générateur, manifeste, PDF et photos générés
data/fixtures/   utilisateurs, parc, historique et tickets fictifs
src/maintidoc/   code (corpus en semaine 1 ; ingestion, recherche, agent, MCP ensuite)
tests/           tests automatisés
```
