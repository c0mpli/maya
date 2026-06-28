"""maya_embed — optional SEMANTIC embeddings for maya  (TEMPLATE · model-agnostic).

By default maya.Memory uses a deterministic offline `hash_embed` (lexical only). Drop a real
embedding model in here to upgrade recall / analogy / `find_distant` from lexical to *semantic* —
the moment `available()` returns True, memory._default_embed routes through this module.

HOW TO USE
  - Easiest: set OPENAI_API_KEY in your env  ->  semantic embeddings turn on automatically.
  - Any other provider (local sentence-transformers, Cohere, Voyage, ...): just rewrite `_provider`
    to return a DIM-dimensional vector per input string, and make `available()` reflect your setup.
  - Do nothing: maya stays fully working offline on hash_embed.

CONTRACT (all this file must satisfy)
  available() -> bool                         # is a real embedder configured?
  embed(text, dim=DIM) -> np.ndarray[dim]     # one vector
  embed_batch(texts) -> np.ndarray[len, DIM]  # batched (cached)
DIM MUST equal memory.EMBED_DIM.
"""
import os, json, hashlib, pathlib, urllib.request
import numpy as np

DIM = 256                                   # keep == memory.EMBED_DIM
_CACHE = pathlib.Path(os.environ.get("MAYA_EMBED_CACHE",
                      str(pathlib.Path.home() / ".cache" / "maya" / "emb_cache.json")))
_cache = None


def available() -> bool:
    """True iff a real embedder is wired up. Extend the check for your provider."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def _provider(texts):
    """Return a list of DIM-dim float lists, one per input string.  <<< EDIT FOR YOUR MODEL >>>
    Default implementation: OpenAI `text-embedding-3-small` at dimensions=DIM (used iff OPENAI_API_KEY set).
    Replace the body to call any local/remote embedding model instead."""
    key = os.environ.get("OPENAI_API_KEY")
    body = json.dumps({"model": "text-embedding-3-small", "input": texts, "dimensions": DIM}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/embeddings", data=body,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=90).read())
    return [d["embedding"] for d in r["data"]]


# ---- generic disk cache + batching (provider-independent; leave as-is) ----
def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(_CACHE.read_text())
        except Exception:
            _cache = {}
    return _cache


def _save():
    if _cache is not None:
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE.write_text(json.dumps(_cache))


def embed_batch(texts):
    c = _load()
    out = [None] * len(texts); todo = []; idx = []
    for i, t in enumerate(texts):
        h = hashlib.md5((t or "").encode("utf-8")).hexdigest()
        if h in c:
            out[i] = np.asarray(c[h], dtype=np.float32)
        else:
            todo.append(t or ""); idx.append(i)
    B = 128
    for s in range(0, len(todo), B):
        vecs = _provider(todo[s:s + B])
        for j, v in zip(idx[s:s + B], vecs):
            out[j] = np.asarray(v, dtype=np.float32)
            c[hashlib.md5((texts[j] or "").encode("utf-8")).hexdigest()] = [float(x) for x in v]
    _save()
    return np.asarray(out, dtype=np.float32) if out else np.zeros((0, DIM), dtype=np.float32)


def embed(text, dim=DIM):
    return embed_batch([text or ""])[0]
