# 🐳 Guide de Test avec Docker Compose

Ce guide te montre comment lancer le service RAG avec Docker Compose et tester la nouvelle route `/list`.

## 📋 Prérequis

- Docker et Docker Compose installés
- Port 8000 (API) et 6333 (Qdrant) disponibles

## 🚀 Étape 1 : Lancer les services

```bash
cd /Users/timothe/Work/blaise/retrieval-plugin

# Build et démarrage des services
docker-compose up --build
```

**Ce qui se passe :**
- ✅ Build de l'image Docker avec Python 3.10
- ✅ Installation des dépendances (Poetry)
- ✅ Téléchargement des modèles BGE-M3 et reranker (première fois uniquement, ~2GB)
- ✅ Démarrage de Qdrant (base vectorielle)
- ✅ Démarrage du service RAG sur port 8000

**Attendre que tu voies :**
```
retrieval-1  | INFO:     Application startup complete.
retrieval-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🧪 Étape 2 : Tester la route `/list` (dans un autre terminal)

### Test 1 : Vérifier que l'API répond

```bash
curl http://localhost:8000/docs
```

Si ça retourne du HTML, l'API fonctionne ! ✅

### Test 2 : Uploader des documents de test

```bash
curl -X POST "http://localhost:8000/upsert" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "Paris est la capitale de la France. Elle compte environ 2 millions d habitants dans la ville et 12 millions dans l agglomération.",
        "metadata": {
          "source": "file",
          "author": "Alice",
          "created_at": "2025-01-15T10:00:00Z"
        }
      },
      {
        "text": "Berlin est la capitale de l Allemagne depuis la réunification en 1990. C est une ville historique importante avec plus de 3.5 millions d habitants.",
        "metadata": {
          "source": "file",
          "author": "Bob",
          "created_at": "2025-01-15T11:00:00Z"
        }
      },
      {
        "text": "Madrid est la capitale de l Espagne. Elle est située au centre géographique du pays et compte environ 3.3 millions d habitants.",
        "metadata": {
          "source": "email",
          "author": "Alice",
          "created_at": "2025-01-15T12:00:00Z"
        }
      },
      {
        "text": "Rome est la capitale de l Italie. C est une ville millénaire qui fut le centre de l Empire romain.",
        "metadata": {
          "source": "file",
          "author": "Charlie",
          "created_at": "2025-01-15T13:00:00Z"
        }
      }
    ]
  }'
```

**Réponse attendue :**
```json
{
  "ids": ["uuid-1", "uuid-2", "uuid-3", "uuid-4"]
}
```

### Test 3 : Liste TOUS les documents

```bash
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "offset": 0}' | jq .
```

**Réponse attendue :**
```json
{
  "documents": [
    {
      "document_id": "uuid-1",
      "chunk_count": 1,
      "metadata": {
        "source": "file",
        "author": "Alice",
        "created_at": "2025-01-15T10:00:00Z",
        "source_id": null,
        "url": null
      },
      "sample_text": "Paris est la capitale de la France. Elle compte environ 2 millions d habitants dans la ville et 12 millions dans l agglomération."
    },
    {
      "document_id": "uuid-2",
      "chunk_count": 1,
      "metadata": {
        "source": "file",
        "author": "Bob",
        "created_at": "2025-01-15T11:00:00Z",
        "source_id": null,
        "url": null
      },
      "sample_text": "Berlin est la capitale de l Allemagne depuis la réunification en 1990..."
    },
    ...
  ],
  "total": 4
}
```

### Test 4 : Filtrer par auteur

```bash
# Seulement les documents d'Alice
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "filter": {
      "author": "Alice"
    }
  }' | jq .
```

**Résultat attendu :** 2 documents (Paris et Madrid)

### Test 5 : Filtrer par source

```bash
# Seulement les documents de type "file"
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "filter": {
      "source": "file"
    }
  }' | jq .
```

**Résultat attendu :** 3 documents (Paris, Berlin, Rome)

### Test 6 : Filtrer par auteur ET source

```bash
# Documents de type "file" écrits par Alice
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "filter": {
      "source": "file",
      "author": "Alice"
    }
  }' | jq .
```

**Résultat attendu :** 1 document (Paris)

### Test 7 : Pagination

```bash
# Première page (limite 2)
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit": 2, "offset": 0}' | jq .

# Deuxième page
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit": 2, "offset": 2}' | jq .
```

### Test 8 : Vérifier dans Qdrant directement

```bash
# Voir la collection dans Qdrant
curl http://localhost:6333/collections/document_chunks | jq .

# Compte total de points (chunks)
curl http://localhost:6333/collections/document_chunks | jq '.result.points_count'
```

---

## 🎯 Test Complet : Query + List

```bash
# 1. Upload un document
curl -X POST "http://localhost:8000/upsert" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "text": "Le plan Schuman a été proposé en 1950 par Robert Schuman.",
      "metadata": {"source": "file", "author": "Historien"}
    }]
  }'

# 2. Liste pour vérifier qu'il est là
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit": 100}' | jq '.total'

# Devrait afficher le nombre total de documents

# 3. Recherche sémantique
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [{
      "query": "Qui a proposé le plan Schuman ?",
      "top_k": 3
    }]
  }' | jq .

# 4. Delete le document
ID=$(curl -s -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit":1,"filter":{"author":"Historien"}}' | jq -r '.documents[0].document_id')

curl -X DELETE "http://localhost:8000/delete" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d "{\"filter\":{\"document_id\":\"$ID\"}}"

# 5. Vérifie qu'il a été supprimé
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit":100,"filter":{"author":"Historien"}}' | jq '.total'

# Devrait afficher 0
```

---

## 📊 Utiliser Swagger UI (Interface graphique)

1. Ouvre ton navigateur : `http://localhost:8000/docs`

2. **Authentification** :
   - Clique sur "Authorize" (cadenas en haut à droite)
   - Entre : `dev-secret`
   - Clique sur "Authorize" puis "Close"

3. **Teste POST /list** :
   - Trouve la section `POST /list`
   - Clique sur "Try it out"
   - Modifie le JSON :
   ```json
   {
     "limit": 10,
     "offset": 0
   }
   ```
   - Clique sur "Execute"
   - Voir la réponse en dessous !

---

## 🛑 Arrêter les services

```bash
# Arrêter les conteneurs
docker-compose down

# Arrêter ET supprimer les volumes (données Qdrant)
docker-compose down -v
```

---

## 🐛 Troubleshooting

### Le build prend beaucoup de temps

**Normal !** La première fois :
- Téléchargement des modèles BGE (~2GB)
- Compilation de tiktoken (nécessite Rust)
- ~5-10 minutes

Les prochains builds seront beaucoup plus rapides grâce au cache Docker et au volume `hf_cache`.

### Erreur : "Port 8000 already in use"

```bash
# Trouver qui utilise le port
lsof -i :8000

# Tuer le processus
kill -9 <PID>

# Ou change le port dans docker-compose.yml
ports:
  - "8001:8000"  # Expose sur 8001 au lieu de 8000
```

### Erreur : "Connection refused"

```bash
# Vérifie que les conteneurs tournent
docker-compose ps

# Regarde les logs
docker-compose logs retrieval
docker-compose logs qdrant
```

### Les modèles ne se téléchargent pas

```bash
# Vérifie les logs du conteneur
docker-compose logs -f retrieval

# Tu devrais voir :
# "Downloading BAAI/bge-m3..."
```

### Erreur 401 Unauthorized

```bash
# Vérifie le token
# Par défaut : "dev-secret"
# Défini dans docker-compose.yml : BEARER_TOKEN=${RAG_BEARER_TOKEN:-dev-secret}

# Si tu as RAG_BEARER_TOKEN dans ton .env, utilise-le
cat .env | grep RAG_BEARER_TOKEN
```

---

## 📦 Variables d'environnement Docker Compose

Les variables sont définies dans `docker-compose.yml` :

```yaml
environment:
  - DATASTORE=qdrant
  - QDRANT_URL=http://qdrant:6333
  - BEARER_TOKEN=${RAG_BEARER_TOKEN:-dev-secret}  # Depuis .env ou "dev-secret"
  - EMBEDDING_PROVIDER=bge
  - EMBEDDING_MODEL=BAAI/bge-m3
  - EMBEDDING_DIMENSION=1024
  - RERANK_K=5
  - RERANK_FINAL_N=3
```

Pour changer le token, crée un fichier `.env` :
```bash
echo "RAG_BEARER_TOKEN=mon-super-token-secret" >> .env
docker-compose up --build
```

---

## ✅ Checklist de test complète

- [ ] `docker-compose up --build` démarre sans erreur
- [ ] L'API répond sur `http://localhost:8000/docs`
- [ ] Upload de documents fonctionne (`POST /upsert`)
- [ ] Liste des documents fonctionne (`POST /list`)
- [ ] Filtre par auteur fonctionne
- [ ] Filtre par source fonctionne
- [ ] Pagination fonctionne
- [ ] Recherche sémantique fonctionne (`POST /query`)
- [ ] Suppression fonctionne (`DELETE /delete`)
- [ ] Qdrant est accessible sur `http://localhost:6333`

---

🎉 **Tu es prêt à tester !** Lance `docker-compose up --build` et suis les étapes ci-dessus.
