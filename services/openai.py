# services/openai.py
"""
Wrapper unifié d'embeddings (compat 2 usages) :
- EMBEDDING_PROVIDER=openai  -> embeddings via API OpenAI
- EMBEDDING_PROVIDER=bge     -> embeddings locaux via BGE-M3 (FlagEmbedding)

Expose :
- get_embeddings() -> objet client avec .embed_documents(List[str]) et .embed_query(str)
- get_embeddings(List[str]) -> List[List[float]]  (documents)
- get_embeddings(str)       -> List[float]        (requête)
- embed_documents(List[str]) / embed_query(str)   (helpers)
"""

import os
from typing import List, Optional, Union

_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()


class _EmbeddingsClient:
    def __init__(self):
        self.provider = _PROVIDER
        if self.provider in ("bge", "local-bge", "bge-m3"):
            # Backend local BGE-M3
            from .bge import embed_documents as _bge_docs, embed_query as _bge_query
            self._docs = _bge_docs
            self._query = _bge_query
            self._mode = "bge"
        else:
            # Backend OpenAI
            try:
                from openai import OpenAI  # type: ignore
            except Exception as e:
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=openai mais le SDK 'openai' n'est pas installé. "
                    "Installe : pip install openai"
                ) from e
            self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self._model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
            self._mode = "openai"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self._mode == "bge":
            return self._docs(texts)
        resp = self._client.embeddings.create(model=self._model_name, input=texts)
        return [item.embedding for item in resp.data]

    def embed_query(self, text: str) -> List[float]:
        if self._mode == "bge":
            return self._query(text)
        resp = self._client.embeddings.create(model=self._model_name, input=[text])
        return resp.data[0].embedding


_CLIENT: Optional[_EmbeddingsClient] = None


def _get_client() -> _EmbeddingsClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _EmbeddingsClient()
    return _CLIENT


# --------- API attendue ailleurs dans le code ---------
# Compat 1: usage "usine" -> get_embeddings() renvoie le client
# Compat 2: usage "fonction" -> get_embeddings(arg) renvoie les vecteurs
def get_embeddings(arg: Optional[Union[str, List[str]]] = None):
    """
    - Sans argument: renvoie le client
    - Avec List[str]: renvoie embeddings documents
    - Avec str: renvoie embedding de la requête
    """
    cli = _get_client()
    if arg is None:
        return cli
    if isinstance(arg, list):
        return cli.embed_documents(arg)
    if isinstance(arg, str):
        return cli.embed_query(arg)
    raise TypeError("get_embeddings: argument must be None, str, or List[str]")


# Helpers (si ailleurs on importe directement ces fonctions)
def embed_documents(texts: List[str]) -> List[List[float]]:
    return _get_client().embed_documents(texts)


def embed_query(text: str) -> List[float]:
    return _get_client().embed_query(text)
