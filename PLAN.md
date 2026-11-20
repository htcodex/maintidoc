# MaintiDoc — Plan de projet

Assistant documentaire multimodal et agentique pour la maintenance.
Référence : *Projet IA Générative Multi Modale V2.pdf* (cahier des charges).

Légende : ✅ fait · 🔄 en cours · ⬜ à faire

---

## Vue d'ensemble (6 semaines)

| Sem. | Thème | Livrables de fin de semaine | Critère de sortie |
|---|---|---|---|
| **1** | Cadrage, corpus, architecture, risques | Livrable 1 (cadrage + architecture), corpus synthétique v1, manifeste validé, squelette du dépôt | Corpus de 30–50 docs généré et validé par script ; docs de cadrage relus |
| **2** ✅ | Ingestion, recherche texte + image, accès | Pipeline PyMuPDF + OCR → PostgreSQL/MinIO/Qdrant ; recherche hybride + RRF filtrée par groupe | Recall@5 mesuré sur 30 questions pilotes ; 0 fuite inter-groupe |
| 3 | VLM, citations, sorties structurées | Qwen2.5-VL servi (Transformers/vLLM) ; prompts v1 ; schéma Pydantic ; vérification des citations | Réponse sourcée page+figure sur le scénario nominal |
| 4 | LangGraph, serveur MCP, validation humaine | Graphe complet avec budgets ; serveur MCP (3 outils) ; jeton d'approbation + idempotence | Ticket créé uniquement après approbation, contenu identique |
| 5 | Reranker adapté, évaluation, injections | Jeu 800–1 500 triplets ; reranker fine-tuné ; jeu de 150 scénarios ; rapport MLflow | Comparaison sans / origine / adapté (nDCG@5, MRR@10) |
| 6 | Déploiement, optimisation, doc, soutenance | Docker Compose complet ; CI ; fiche de limites ; démo 7 étapes | Démo bout en bout reproductible depuis un clone propre |

---

## Semaine 1 — Cadrage, corpus, architecture, risques (détail)

### 1.1 Cadrage
- ✅ Note de cadrage : objectifs, utilisateurs, périmètre, hors périmètre → [docs/01_cadrage.md](docs/01_cadrage.md)
- ✅ Personas, groupes d'accès et matrice des droits → [docs/01_cadrage.md](docs/01_cadrage.md#5-utilisateurs-groupes-et-droits)
- ✅ Scénarios de démonstration cibles (fil rouge) → [docs/01_cadrage.md](docs/01_cadrage.md#7-scénarios-fil-rouge)
- ✅ Objectifs chiffrés (non acquis) et budgets du prototype

### 1.2 Corpus
- ✅ Spécification du corpus et du schéma de métadonnées → [docs/04_corpus.md](docs/04_corpus.md)
- ✅ Choix des deux familles d'équipements fictives : pompes centrifuges **MDP** et compresseurs à vis **MDC**
- ✅ Générateur de corpus synthétique (PDF texte, tableaux, figures, 1 scan pour l'OCR) → [corpus/generate_corpus.py](corpus/generate_corpus.py)
- ✅ Pièges volontaires : voyants similaires entre familles (négatifs difficiles), bulletins contradictoires, document d'injection, document restreint
- ✅ Photos de démonstration synthétiques (nette, floue/ambiguë)
- ✅ Données fictives : utilisateurs, parc d'équipements, historique d'interventions (pour le serveur MCP de la semaine 4)
- ✅ Manifeste + validation Pydantic + tests → [src/maintidoc/corpus/](src/maintidoc/corpus/), [tests/](tests/)

### 1.3 Architecture
- ✅ Architecture logique, flux de données, séquence de la requête nominale → [docs/02_architecture.md](docs/02_architecture.md)
- ✅ Choix techniques + licences à figer → [docs/02_architecture.md](docs/02_architecture.md#4-choix-techniques-et-licences)
- ✅ Squelette du dépôt, `.env.example`, `docker-compose.yml` (services d'infrastructure)

### 1.4 Risques
- ✅ Registre des risques (techniques, sécurité, données, planning) → [docs/03_analyse_risques.md](docs/03_analyse_risques.md)
- ✅ Modèle de menaces (injection, fuite inter-groupes, action non approuvée)

### 1.5 Points ouverts à trancher avant la semaine 2
- ⬜ Confirmer le matériel GPU réellement disponible (24 Go visé) → conditionne vLLM vs Transformers + quantification
- ⬜ Figer les révisions exactes des modèles (hash Hugging Face) et vérifier les licences sur les fiches officielles
- ⬜ Relecture humaine de 10 % du corpus généré (cohérence technique)

---

## Semaines 2 à 6 — tâches prévues

### Semaine 2 — Ingestion et recherche ✅ (voir [docs/06_ingestion_recherche.md](docs/06_ingestion_recherche.md))
- ✅ Extraction PyMuPDF : paragraphes, tableaux, figures (bbox, ids du manifeste), pages ; OCR EasyOCR (fr) des pages scannées et photos
- ✅ Métadonnées complètes par élément ; Qdrant (texte BGE-M3, image CLIP), PostgreSQL, stockage S3 (SeaweedFS au lieu de MinIO)
- ✅ Filtrage par `access_groups` dans la requête Qdrant + re-contrôle + ouverture d'image contrôlée ; journal d'accès
- ✅ BM25 + dense + visuel, RRF pondérée, reranker d'origine branché
- ✅ 30 questions pilotes ; Recall@5 / nDCG@5 / MRR@10 ; 0 fuite inter-groupes → [reports/semaine2/](reports/semaine2/)

### Semaine 3 — VLM et réponses sourcées
- Service d'inférence Qwen2.5-VL-7B-Instruct (quantifié si nécessaire) ; limites d'image/contexte/tokens
- `prompts/answer_v1.yaml`, `visual_analysis_v1.yaml`, `evidence_check_v1.yaml`, `ticket_draft_v1.yaml`
- Schéma Pydantic `MaintiDocResponse` (status, answer, citations, uncertainties, clarification_question, proposed_action)
- Vérificateur de citations : la citation existe parmi les éléments récupérés **et** soutient l'affirmation
- Traçage MLflow : versions modèle / prompt / reranker / index par exécution

### Semaine 4 — Agent et MCP
- Graphe LangGraph : accès → analyse → recherche → historique MCP → réponse → vérification → clarification → brouillon ticket → `interrupt` → création
- Serveur MCP : `get_equipment_history`, `get_open_tickets`, `create_ticket` ; autorisation à chaque appel
- Jeton d'approbation signé (HMAC) lié à l'utilisateur + hash du contenu exact ; clé d'idempotence
- Budgets codés : 3 appels MCP, 6 appels modèle, 60 s
- API FastAPI (auth) + interface Streamlit (question + photo, affichage sources, écran d'approbation)

### Semaine 5 — Fine-tuning et évaluation
- Construction de 800–1 500 triplets (question, positif, négatif difficile) vérifiés ; split par document/famille
- Fine-tuning du reranker ; comparaisons sans / origine / adapté
- Jeu de 150 scénarios (40 / 30 / 20 / 20 / 20 / 20) ; métriques de la section 10
- Tests d'injection (texte, OCR, réponses MCP)

### Semaine 6 — Déploiement et soutenance
- Docker Compose complet, CI (tests, scan de secrets, audit dépendances)
- Mesures de latence p50/p95, mémoire, GPU ; optimisations
- Fiche de limites, README final, procédure de retour arrière
- Répétition de la démonstration (7 étapes du cahier des charges)
