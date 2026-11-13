"""Sources Mermaid des diagrammes du livrable 1 (écrites dans docs/diagrammes/*.mmd)."""

DIAGRAMS = {
    "architecture_blocs": """
flowchart TB
    U[Interface web<br/>question + photo] -- "question, photo, identité" --> API
    API[API + authentification<br/>CP1 : identité et groupes] -- "requête + groupes autorisés" --> O
    O[Orchestration de l'agent<br/>budgets : 3 MCP, 6 modèle, 60 s]
    O -- "image" --> VLM[Modèle vision-langage<br/>description, réponse JSON]
    VLM -- "observations, réponse" --> O
    O -- "requête + filtre de groupes" --> R[Recherche documentaire<br/>CP2 : filtre d'accès avant récupération]
    R -- "passages, tableaux, figures (ids, pages)" --> O
    R <--> S[(Stockage : index vectoriel,<br/>métadonnées, fichiers)]
    O -- "réponse + citations" --> C[Vérification des citations<br/>CP3]
    C -- "réponse sourcée / clarification / abstention" --> API
    O -- "brouillon de ticket" --> H[Validation humaine<br/>CP4 : approbation explicite]
    H -- "jeton signé (utilisateur + hash)" --> M
    O -- "historique, tickets ouverts" --> M[Outil MCP maintenance<br/>CP5 : droits, jeton, idempotence]
    M -- "interventions, n° ticket" --> O
    M <--> T[(Service de maintenance fictif)]
    API -- "réponse, sources, brouillon" --> U
""",
    "flux_ingestion": """
flowchart LR
    D[PDF et photos du corpus] --> Q{PDF scanné ?}
    D -- "originaux conservés" --> F[(Stockage fichiers)]
    Q -- non --> X[Extraction texte, tableaux, figures]
    Q -- oui --> OCR[OCR local] --> X
    X --> DEC[Découpage : paragraphes, tableaux, figures]
    DEC --> E[Embeddings texte et image]
    DEC --> META[Métadonnées : document, version, page, élément, famille, groupes, statut]
    E --> IDX[(Index vectoriel)]
    META --> IDX
    META --> PG[(Base de métadonnées)]
""",
    "flux_requete": """
sequenceDiagram
    actor T as Technicien
    participant A as API
    participant O as Orchestration
    participant V as VLM
    participant R as Recherche
    participant M as MCP
    T->>A: question + photo
    A->>A: CP1 identité, groupes
    A->>O: requête autorisée
    O->>V: photo
    V-->>O: équipement identifié ? voyant observé
    O->>R: requête + filtre groupes (CP2)
    R-->>O: passages et figures autorisés
    O->>M: historique de l'équipement (CP5)
    M-->>O: interventions
    O->>V: rédaction de la réponse (sources = données)
    V-->>O: réponse JSON + citations
    O->>O: CP3 vérification des citations
    O-->>A: réponse / clarification / abstention
    A-->>T: réponse sourcée
""",
    "flux_ticket": """
flowchart LR
    B[Brouillon de ticket préparé par l'agent] --> AFF[Affichage du contenu exact]
    AFF --> Q{Approbation humaine ? CP4}
    Q -- non / modification --> FIN[Aucun ticket créé]
    Q -- oui --> J[Jeton signé : utilisateur + hash du contenu + clé d'idempotence]
    J --> MCP[Appel MCP create_ticket]
    MCP --> V{Serveur : droits, jeton, hash, idempotence ? CP5}
    V -- invalide --> REF[Refus journalisé]
    V -- clé déjà vue --> EX[Ticket existant renvoyé, pas de doublon]
    V -- valide --> OK[Ticket créé, n° renvoyé à l'utilisateur]
""",
}
