# 06 — Ingestion, recherche texte + image et contrôle d'accès (semaine 2)

*Version 1.0 — 2026-11-20. Résultats chiffrés : [reports/semaine2/](../reports/semaine2/).*

## 1. Ce qui a été construit

| Module | Rôle |
|---|---|
| [catalog.py](../src/maintidoc/catalog.py) | Lit `corpus/inventaire.csv` (registre officiel) + `manifest.yaml` (statut, remplacements, SHA-256) |
| [ingestion/extract.py](../src/maintidoc/ingestion/extract.py) | PDF → éléments citables : paragraphes, tableaux, figures, pages ; OCR des pages scannées |
| [ingestion/ocr.py](../src/maintidoc/ingestion/ocr.py) | OCR local EasyOCR (fr, en), CPU |
| [ingestion/pipeline.py](../src/maintidoc/ingestion/pipeline.py) | Extraction → embeddings → Qdrant + SQLite + `index_manifest.json` |
| [retrieval/encoders.py](../src/maintidoc/retrieval/encoders.py) | BGE-M3 (texte), CLIP ViT-B/32 (images) + CLIP multilingue (requêtes FR) ; encodeur factice pour les tests |
| [retrieval/index.py](../src/maintidoc/retrieval/index.py) | Collections Qdrant `elements_text` / `elements_image`, filtre d'accès, métadonnées SQLite |
| [retrieval/search.py](../src/maintidoc/retrieval/search.py) | BM25 + dense + visuel, fusion RRF, pénalité des documents remplacés, reranker optionnel |
| [storage.py](../src/maintidoc/storage.py) | PostgreSQL (métadonnées, journal d'accès) et stockage S3, ou SQLite / dossier local |
| [access.py](../src/maintidoc/access.py) | Règle d'accès, ouverture contrôlée des images, journal d'accès sans contenu |
| [evaluation/retrieval_eval.py](../src/maintidoc/evaluation/retrieval_eval.py) | 30 questions pilotes, Recall@5 / nDCG@5 / MRR@10, tests de fuite |

## 2. Commandes

```bash
pip install -e ".[corpus,retrieval,dev]"
python -m maintidoc.ingestion.pipeline                 # index réel (télécharge BGE-M3 et CLIP au 1er lancement)
python -m maintidoc.retrieval.cli --user u_tech_p01 "Que signifie le voyant V2 orange fixe ?"
python -m maintidoc.retrieval.cli --user u_tech_p01 --photo corpus/images/photo_pupitre_mdp_orange_nette.png "Que signifie ce voyant ?"
python -m maintidoc.evaluation.retrieval_eval          # écrit reports/semaine2/
pytest                                                 # tests rapides (encodeurs factices)
pytest -m slow                                         # test OCR
```

**Services** : `docker compose up -d postgres qdrant s3` puis renseigner `.env` (copie de `.env.example`) :
`QDRANT_URL`, `DATABASE_URL`, `S3_*`. Utiliser `127.0.0.1` plutôt que `localhost` (sous Windows, `localhost`
est d'abord résolu en IPv6 et les ports Docker ne sont publiés qu'en IPv4). Sans ces variables, le même code
fonctionne en mode autonome : Qdrant embarqué, SQLite, dossier local (tests, CI).

**MinIO → SeaweedFS** : l'image MinIO n'est plus téléchargeable (pull refusé sur Docker Hub et quay.io).
SeaweedFS fournit la même API S3 (client boto3 inchangé), sous licence Apache 2.0.

## 3. Ingestion

1. **Contrôle d'intégrité** : chaque fichier de l'inventaire doit exister et avoir l'empreinte SHA-256 du manifeste.
2. **Page scannée ?** Une page dont la couche texte fait moins de 20 caractères est rendue à 300 dpi et passée à l'OCR.
3. **Texte** : blocs PyMuPDF ; en-tête de document (titre, « Réf. », « Modèles ») et pied de page exclus ; les
   paragraphes sont regroupés sous leur rubrique (titre de section en gras), 1 000 caractères au plus.
4. **Tableaux** : structure par `find_tables()`, texte relu cellule par cellule (`get_textbox`), car `extract()`
   supprime les espaces sur ces PDF. Chaque ligne est sérialisée « en-tête : valeur » pour rester lisible seule.
5. **Figures** : légende « Figure n — … » + groupe de dessins vectoriels juste au-dessus (`cluster_drawings`),
   zone élargie aux libellés. L'image est découpée (150 dpi) et ses libellés indexés. Les `element_id`
   (`figure_<page>_<rang>`) sont **identiques au manifeste** : c'est vérifié par un test.
6. **Pages** : chaque page est aussi un élément visuel (PNG 110 dpi) — canal image et futur VLM.
7. **Photos** : élément `photo` ; texte = titre + éléments visuels de l'inventaire + texte lu par OCR.
8. **Métadonnées** recopiées sur chaque élément : document, version, page, élément, type, famille, équipements,
   statut, `superseded_by`, groupes d'accès, confidentialité, SHA-256.

Le texte OCR (étiquette d'injection, document scanné) est indexé comme une **donnée** ; il n'est jamais
concaténé à des instructions.

## 4. Recherche

```
utilisateur ──► groupes ──► éléments autorisés (filtre AVANT récupération)
                                │
          ┌─────────────────────┼─────────────────────┐
        BM25               BGE-M3 (Qdrant,        CLIP (Qdrant, filtre)
   (sur les autorisés)     filtre access_groups)  requête texte FR + photo
          └─────────────────────┼─────────────────────┘
                     Reciprocal Rank Fusion (k = 60)
                 documents remplacés × 0,5 (signalés, pas masqués)
                                │
                  reranker (optionnel, 20 premiers)
                                │
              re-contrôle d'accès de chaque résultat ──► top k
```

## 5. Contrôle d'accès

| Point | Mécanisme | Vérifié par |
|---|---|---|
| Avant récupération | BM25 calculé sur les seuls éléments autorisés ; filtre `access_groups` (MatchAny) dans chaque requête Qdrant | `test_search_never_returns_forbidden_documents`, évaluation (0 fuite) |
| Après fusion | Chaque résultat est re-vérifié ; un écart serait journalisé | idem |
| Ouverture d'une image | `open_asset` lève `AccessDenied` (message générique) | `test_open_asset_refused_without_rights`, évaluation |
| Journal | `data/index/access_log.jsonl` : utilisateur, action, cible, décision — jamais la question ni le contenu | — |

## 6. Limites et suites

- Corpus court (47 éléments sources, 136 éléments indexés) : les scores sont élevés par construction ; ils servent de
  référence pour mesurer l'effet du reranker adapté en semaine 5, pas de garantie générale.
- CLIP ViT-B/32 lit mal le texte des schémas : le canal visuel apporte surtout pour les photos de pupitre.
- OCR CPU lent (~50 s pour une page scannée) : acceptable à l'ingestion, pas en ligne.
- Canal visuel : en RRF non pondérée, CLIP ramène des pages entières et dégrade nDCG@5 ; la requête texte → CLIP
  est pondérée à 0,25, la photo jointe à 1 (voir `channel_weights` dans config.py et les résultats).
- Reranker d'origine sur CPU : ~40 s par requête pour 20 candidats ; inutilisable en ligne sans GPU.
