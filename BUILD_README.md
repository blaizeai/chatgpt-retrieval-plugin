# Guide de Build du Service RAG

## Vue d'ensemble

Le service RAG est compilé en binaire standalone avec PyInstaller et intégré dans l'application Tauri.

**Avantages** :
- ✅ Pas besoin de Python sur la machine client
- ✅ Configuration externe (fichier `rag.env`)
- ✅ Support de plusieurs bearer tokens
- ✅ Modèles ML téléchargés automatiquement au premier lancement

## Build du binaire

### Prérequis

- Python 3.10
- Poetry (`pip install poetry`)

### Étapes

```bash
cd retrieval-plugin
./build_binary.sh
```

Le script va :
1. Installer les dépendances
2. Compiler avec PyInstaller (~10-15 min)
3. Copier le binaire dans `tauri-app/src-tauri/resources/bin/darwin-arm64/` (ou autre plateforme)

### Taille du binaire

- **Binaire sans modèles** : ~300-500 MB
- **Modèles téléchargés** : ~2 GB (au premier lancement)
  - `BAAI/bge-m3` : ~2 GB
  - `BAAI/bge-reranker-v2-m3` : ~500 MB
- **Total** : ~2.5 GB (mais modèles dans le cache utilisateur)

## Configuration post-installation

### Emplacement du fichier de config

Le fichier `rag.env` est créé automatiquement au premier lancement :

- **macOS** : `~/Library/Application Support/Blaise/rag.env`
- **Linux** : `~/.config/blaise/rag.env`
- **Windows** : `%APPDATA%\Blaise\rag.env`

### Modifier les bearer tokens

Éditez le fichier `rag.env` :

```bash
# Un seul token
BEARER_TOKEN=votre-token-secret

# Plusieurs tokens (séparés par des virgules)
BEARER_TOKEN=token1,token2,token3
```

Pas besoin de recompiler ! Redémarrez juste l'application.

### Autres configurations

Le fichier `rag.env` contient aussi :

```bash
# Base de données vectorielle
DATASTORE=chroma  # ou qdrant, pinecone, etc.

# Service d'embeddings
EMBEDDING_SERVICE=bge  # local, ou openai pour API

# Port du service
RAG_PORT=8000

# Reranking
RERANK_ENABLE=true
RERANK_K=5
RERANK_FINAL_N=3
```

## Tester le binaire

```bash
# Lancer manuellement
cd tauri-app/src-tauri/resources/bin/darwin-arm64
./rag-service

# Le service démarre sur http://127.0.0.1:8000
# Les modèles se téléchargent automatiquement au premier lancement
```

## Intégration dans Tauri

Le binaire sera lancé automatiquement par Tauri au démarrage de l'application via `main.rs`.

### Test de l'API

```bash
# Vérifier que le service fonctionne
curl http://127.0.0.1:8000/health

# Uploader un document (remplacez le token)
curl -X POST "http://127.0.0.1:8000/upsert" \
  -H "Authorization: Bearer votre-token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "text": "Test document",
      "metadata": {"source": "test"}
    }]
  }'

# Query
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Authorization: Bearer votre-token" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [{
      "query": "test",
      "top_k": 3
    }]
  }'
```

## Troubleshooting

### Le binaire ne démarre pas

1. Vérifiez les logs dans la console
2. Vérifiez que le port 8000 est disponible
3. Vérifiez les permissions du binaire : `chmod +x rag-service`

### Les modèles ne se téléchargent pas

1. Vérifiez la connexion Internet
2. Les modèles vont dans `~/.cache/huggingface/`
3. Première exécution : peut prendre 10-15 minutes

### Erreur d'authentification

1. Vérifiez le fichier `rag.env`
2. Vérifiez que le `BEARER_TOKEN` est correct
3. Redémarrez l'application après modification

## Build pour distribution

Pour créer un build de production :

```bash
cd retrieval-plugin
./build_binary.sh

cd ../tauri-app
npm run tauri:build
```

Le binaire RAG sera automatiquement inclus dans l'installeur Tauri.
