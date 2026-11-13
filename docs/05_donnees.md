# 05 — Données du projet : sources externes et données générées

*Semaine 1. Version 1.0 — 2026-10-23.*

## 1. Conclusion de la recherche

Il n'existe pas de jeu de données public qui couvre à la fois : documents de maintenance **en français**, deux familles d'équipements, figures citables, contrôle d'accès et historique d'interventions. Le cœur du projet repose donc sur le **corpus synthétique** ([04_corpus.md](04_corpus.md)). Les sources externes ci-dessous servent de **compléments** (robustesse, pré-entraînement, test de généralisation), à condition de respecter leur licence.

## 2. Sources externes évaluées

| Source | Contenu | Licence | Usage proposé | Verdict |
|---|---|---|---|---|
| [ViDoRe V3 — Industrial](https://huggingface.co/datasets/vidore/vidore_v3_industrial) | 27 manuels techniques (aéronautique militaire, EN), 5 244 pages, 283 questions traduites en 6 langues dont le français, pages pertinentes annotées | Annotations CC BY 4.0 ; licence par document dans `documents_metadata["license"]` | Test de **généralisation** de la recherche visuelle sur de vrais manuels (questions FR, pages EN) | ✅ Recommandé (sem. 2/5) |
| [vidore/vdsid_french](https://huggingface.co/datasets/vidore/vdsid_french) | 5 000 triplets question / page de document en français | MIT (selon la fiche) | Évaluation complémentaire de la recherche image | ✅ Optionnel |
| [mMARCO-fr](https://huggingface.co/datasets/unicamp-dl/mmarco) (MS MARCO traduit) | 539 k questions, 8,8 M passages, négatifs difficiles | Hérite des conditions MS MARCO (usage non commercial / recherche) | **Pré-adaptation** du reranker au français avant l'adaptation au domaine | ⚠️ Possible, usage académique uniquement |
| [PIAF](https://huggingface.co/datasets/AgentPublic/piaf) | 3 835 questions sur Wikipédia FR | MIT (HF) / CC BY-SA (article) | Données générales FR si besoin | ⚠️ Peu utile (hors domaine) |
| [FQuAD](https://huggingface.co/datasets/illuin/fquad) | 25 000 questions FR | CC BY-NC-SA, redistribution interdite | — | ❌ Écarté (licence) |
| [MaintNet](https://arxiv.org/abs/2005.12443) | Journaux de maintenance réels (aviation : 6 169 entrées problème/action ; automobile ; bâtiments), EN | Publié pour la recherche | Inspiration pour le **style** des historiques d'interventions (abréviations, fautes) | ✅ Inspiration seulement |
| [Manuels techniques de l'US Army](https://www.liberatedmanuals.com/TM-5-4320-237-15.pdf) (pompes centrifuges, compresseurs) | Manuels complets avec schémas, tableaux de dépannage, EN | « Approved for public release, distribution unlimited » (domaine public US) | Documents **réels** pour tester l'ingestion (PDF scannés, mises en page complexes) | ✅ Recommandé pour l'ingestion (sem. 2), à garder hors du corpus principal FR |
| [MPMQA / PM209](https://arxiv.org/abs/2304.09660) | 209 manuels grand public, 22 021 questions avec régions visuelles | Non précisée ; manuels sous droits des marques | — | ❌ Licence incertaine |
| [Roboflow — Indicator Lights](https://universe.roboflow.com/indicator-lights-dataset) | ~1 850 images de voyants | Variable selon le projet | Photos réelles de voyants pour tester le VLM | ⚠️ Vérifier la licence projet par projet |
| [INRS ED 6109](https://www.inrs.fr/media.html?refINRS=ED+6109) (consignation) | Guide de référence FR | Droits réservés : reproduction interdite sans autorisation | Lien de référence dans la fiche de limites seulement | ❌ Ne pas intégrer au corpus |

Règle appliquée : une source n'entre dans le dépôt que si sa licence l'autorise **et** qu'elle est consignée ici. Les documents externes sont téléchargés par script (pas commités) et reçoivent `source: autorise` dans le manifeste.

## 3. Données générées pour le projet

| Données | Script | Volume | Usage |
|---|---|---|---|
| Corpus PDF + figures + scan | [corpus/generate_corpus.py](../corpus/generate_corpus.py) | 40 documents, 42 pages, 13 figures | RAG (sem. 2–3) |
| Photos de pupitres | idem | 5 photos | VLM, clarification, injection |
| Utilisateurs, parc, historique, tickets | [data/fixtures/](../data/fixtures/) | 5 utilisateurs, 7 équipements, 9 interventions, 2 tickets | Serveur MCP (sem. 4) |
| **Jeu d'adaptation du reranker** | [datasets/build_reranker_dataset.py](../datasets/build_reranker_dataset.py) | 178 passages, 253 questions, **1 012 triplets** | Fine-tuning et évaluation (sem. 5) |

### Jeu du reranker en détail

- **Passages** : un par paragraphe, liste, ligne de tableau ou légende de figure, avec `document_id`, `page`, `element_id` (les mêmes identifiants que les citations).
- **Questions** : environ 200 générées par gabarits à partir des tableaux (voyants, codes défaut, périodicités, références…), plus 55 rédigées à la main pour les paragraphes et les cas pièges.
- **Négatifs difficiles** (4 par question) : documents « jumeaux » de l'autre famille (383, ex. voyant orange MDP ↔ MDC), même document (438), même famille (186), version remplacée imposée (5).
- **Garde-fou** : un passage qui contient la réponse n'est jamais utilisé comme négatif (`relevant_passage_ids`).
- **Séparation par groupe de documents** (un document et son jumeau MDP/MDC restent ensemble) : train 696 / val 152 / test 164 triplets. Test = fiches codes défaut + guides de dépannage, jamais vus à l'entraînement.
- **Vérification humaine** : `datasets/reranker/review_sample.csv` (10 %, 101 triplets) à annoter `o/n` ; le taux d'erreur est à reporter dans le rapport.
- **Limite** : la cohérence questions/réponses est garantie par construction, mais les questions par gabarits sont plus régulières que des questions réelles de techniciens. Faire reformuler une partie par 2–3 personnes améliorerait le réalisme.

## 4. À faire

- Semaine 2 : script `datasets/download_external.py` pour ViDoRe V3 Industrial et 2–3 manuels US Army (téléchargement + vérification de licence + empreintes).
- Semaine 5 : jeu d'évaluation de 150 scénarios construit sur les mêmes données (40 / 30 / 20 / 20 / 20 / 20).
