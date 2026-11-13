# 03 — Analyse des risques MaintiDoc

*Livrable 1 (partie risques) — semaine 1. Version 1.0 — 2026-10-23.*

Échelles : probabilité (P) et impact (I) de 1 (faible) à 3 (fort). Criticité = P × I. Seuil d'action : ≥ 4.

## 1. Registre des risques

### Sécurité et conformité

| ID | Risque | P | I | C | Mesure | Test / preuve | Sem. |
|---|---|---|---|---|---|---|---|
| S1 | Injection de prompt via texte d'un document | 3 | 3 | 9 | Documents encapsulés comme données ; outils autorisés par liste blanche dans le graphe ; aucune destination réseau sortante hors services internes | `TRANS-NOTE-INJ` + 20 scénarios d'injection | 3–5 |
| S2 | Injection via texte OCR d'une image ou d'une photo | 2 | 3 | 6 | Même encapsulation ; l'OCR n'est jamais concaténé au prompt système | Cas OCR dans le jeu d'injection | 5 |
| S3 | Injection via réponse MCP (champ `description` d'une intervention) | 2 | 3 | 6 | Réponses MCP validées par schéma, traitées comme données | Intervention piégée dans `interventions.json` | 4–5 |
| S4 | Fuite inter-groupes (document ou image d'un autre groupe dans le contexte ou à l'affichage) | 2 | 3 | 6 | Filtre Qdrant avant récupération + contrôle à l'ouverture des fichiers MinIO (URL présignées après vérification) | 20 scénarios d'accès ; objectif 0 fuite | 2, 5 |
| S5 | Création de ticket sans approbation, ou avec contenu modifié après approbation | 2 | 3 | 6 | Jeton HMAC lié à l'utilisateur + hash du contenu ; vérifié côté serveur MCP | Tests unitaires de falsification de jeton | 4 |
| S6 | Création en double | 2 | 2 | 4 | Clé d'idempotence stockée côté serveur | Rejeu de la même requête | 4 |
| S7 | Fuite de secrets (clés, mots de passe) dans Git, prompts ou journaux | 2 | 3 | 6 | `.env` hors Git, `.env.example` sans valeur ; scan de secrets en CI ; journaux sans contenu brut | gitleaks en CI | 1, 6 |
| S8 | Usage hors rôle (demande de contournement d'une sécurité, pilotage) | 2 | 3 | 6 | Statut `refused` ; rappel du rôle documentaire | Scénarios dédiés | 3, 5 |
| S9 | Licences AGPL (PyMuPDF, MinIO) incompatibles avec une diffusion | 1 | 2 | 2 | Usage académique non distribué ; plan B documenté | Fiche de limites | 6 |

### Qualité des réponses

| ID | Risque | P | I | C | Mesure | Test / preuve | Sem. |
|---|---|---|---|---|---|---|---|
| Q1 | Hallucination ou citation qui ne soutient pas l'affirmation | 3 | 3 | 9 | Citations restreintes aux IDs récupérés ; vérification des preuves (prompt `evidence_check`) ; abstention | Taux de citations soutenues ≥ 90 % (objectif) | 3, 5 |
| Q2 | Confusion entre familles d'équipements (voyants similaires) | 3 | 2 | 6 | Identification de l'équipement exigée ; filtre `equipment_family` ; reranker entraîné sur négatifs difficiles | Paires MDP/MDC dans le jeu de test | 2, 5 |
| Q3 | Citation d'un document remplacé | 2 | 2 | 4 | Champ `status` + `superseded_by` ; documents remplacés dépriorisés et signalés | Scénario couple de serrage | 2–3 |
| Q4 | Contradiction non signalée entre documents actifs | 2 | 2 | 4 | Le prompt exige de signaler les divergences ; statut `needs_clarification` | Scénario vidange MDC | 3, 5 |
| Q5 | Diagnostic présenté comme certain sur la base d'une ressemblance visuelle | 2 | 3 | 6 | Distinction sources / observations / hypothèses dans le schéma de sortie | Revue manuelle des cas image | 3, 5 |
| Q6 | OCR de mauvaise qualité sur document scanné | 2 | 1 | 2 | Image originale conservée et transmise au VLM | Document scanné `MDC-PROC-REVISION-SCAN` | 2 |

### Technique et performance

| ID | Risque | P | I | C | Mesure | Sem. |
|---|---|---|---|---|---|---|
| T1 | GPU 24 Go insuffisant pour Qwen2.5-VL-7B + embeddings + reranker | 2 | 3 | 6 | Quantification 4 bits, limite de pixels d'image, embeddings sur CPU si nécessaire, repli Qwen2.5-VL-3B | 3 |
| T2 | Pas d'accès GPU du tout pendant le développement | 2 | 3 | 6 | Interface `VLMClient` abstraite avec implémentation factice pour tests ; développement CPU avec modèle 3B | 1–3 |
| T3 | vLLM ne prend pas en charge la configuration retenue | 2 | 1 | 2 | Transformers par défaut | 3 |
| T4 | Latence p95 > 30 s | 2 | 2 | 4 | Budgets d'appels, cache des embeddings, réduction des images | 6 |
| T5 | Incompatibilités de versions LangChain / LangGraph / MCP | 2 | 2 | 4 | Dépendances figées ; tests d'intégration en CI | 2, 6 |

### Données et projet

| ID | Risque | P | I | C | Mesure | Sem. |
|---|---|---|---|---|---|---|
| D1 | Corpus synthétique trop simple → métriques flatteuses | 3 | 2 | 6 | Pièges volontaires (négatifs difficiles, contradictions, scan, remplacements) ; split par document/famille | 1, 5 |
| D2 | Pas assez de triplets vérifiés (800–1 500) pour le fine-tuning | 2 | 2 | 4 | Génération semi-automatique + vérification humaine d'un échantillon ; rapport honnête si le gain est nul | 5 |
| D3 | Fuite entre jeux d'entraînement et de test du reranker | 2 | 2 | 4 | Séparation stricte par `document_id` | 5 |
| P1 | Retard sur l'intégration bout en bout | 2 | 3 | 6 | Squelette bout en bout « fil fin » dès la semaine 3 avec composants factices | 3 |

## 2. Modèle de menaces (résumé)

| Actif | Menace | Point de contrôle |
|---|---|---|
| Documents confidentiels | Lecture par un groupe non autorisé | Filtre Qdrant + contrôle MinIO + API |
| Service de tickets | Création non approuvée, doublon | Serveur MCP : autorisation, jeton, idempotence |
| Secrets | Exposition | Injection à l'exécution, scan CI |
| Comportement de l'agent | Détournement par contenu non fiable | Encapsulation, liste blanche d'outils, budgets, absence d'accès réseau sortant |

Hypothèse de confiance : seuls le code du dépôt, la configuration et l'utilisateur authentifié sont de confiance. Documents, OCR, photos et réponses d'outils sont **non fiables**.

## 3. Suivi

Le registre est revu à la fin de chaque semaine ; toute modification est datée dans ce fichier.

| Date | Modification |
|---|---|
| 2026-10-23 | Création du registre (semaine 1) |
