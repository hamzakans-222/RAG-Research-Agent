# MémoRAG — RAG Research Agent

Recherche sémantique locale dans un PDF avec Python, LangChain, Ollama et
PostgreSQL/pgvector. Le programme charge le document, le découpe en passages,
calcule leurs embeddings et retrouve les trois passages les plus proches d'une
question, avec leur source et leur numéro de page.

Cette version couvre l'indexation et la recherche documentaire. La génération
d'une réponse rédigée par un modèle de langage n'est pas encore implémentée.

## Prérequis

- Python 3.10 ou supérieur (testé avec Python 3.10).
- Docker avec Docker Compose.
- Ollama installé et démarré sur `http://localhost:11434`.

## Installation

Depuis la racine du projet, dans PowerShell :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Renseigner `POSTGRES_PASSWORD` dans `.env` avec un mot de passe personnel.
Pour générer une valeur aléatoire :

```powershell
python -c "import secrets; print(secrets.token_hex(24))"
```

Le fichier `.env.example` contient uniquement des paramètres locaux génériques.
Le fichier `.env`, les clés privées, les caches et les sauvegardes sont exclus de Git.

## Démarrage et test

```powershell
ollama pull nomic-embed-text:latest
docker compose up -d --wait
python Test.py
```

Ollama doit être actif avant de lancer le test. Le modèle produit des vecteurs
de 768 dimensions. La table `public.rag_documents` est créée lors de la première
indexation. Les identifiants déterministes permettent de réindexer les mêmes
passages sans ajouter de doublons.

Le PDF fourni, `rag_test_novatech.pdf`, contient uniquement des informations
fictives destinées à la démonstration. Il produit 13 passages avec le découpage
actuel. Exemple de question : `Qui dirige le projet Atlas ?`
Les passages retrouvés doivent mentionner Omar Lahlou.

Les numéros de page affichés commencent à zéro. Les autres PDF sont ignorés par
Git par défaut pour garder les documents personnels locaux.

## Consulter la base

Ouvrir [Adminer](http://localhost:18080) :

- Système : `PostgreSQL`
- Serveur : `pgvector`
- Utilisateur : `rag_user`
- Mot de passe : valeur `POSTGRES_PASSWORD` de votre `.env`
- Base de données : `RAG_agent`
- Table : `rag_documents`

Depuis une application locale, utiliser `127.0.0.1:15432`.
Les services Docker sont accessibles uniquement sur l'interface locale.

Pour vérifier les vecteurs dans la console SQL :

```sql
SELECT count(*) AS vecteurs,
       min(vector_dims(embedding)) AS dimension_min,
       max(vector_dims(embedding)) AS dimension_max
FROM public.rag_documents;
```

## Structure

- `Test.py` : point d'entrée interactif.
- `Rag_architecture/Loading.py` : extraction des pages du PDF.
- `Rag_architecture/chunking.py` : découpage en passages.
- `Rag_architecture/Embedding.py` : embeddings locaux avec Ollama.
- `Rag_architecture/indexing.py` : stockage et recherche avec pgvector.
- `compose.yaml` : PostgreSQL/pgvector et Adminer.
- `docker/init/01-pgvector.sql` : activation de l'extension vectorielle.

## Arrêt

```powershell
docker compose stop
```

Les données restent dans le volume Docker `rag-agent_pgdata`, qui n'est pas
publié sur GitHub. `docker compose down` conserve ce volume ; ajouter `-v`
supprime le volume et ses données.
