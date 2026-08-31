"""Minimal pure-Python + numpy TF-IDF and cosine similarity.

Deliberately avoids scikit-learn/scipy: on some locked-down Windows setups
an Application Control policy blocks scipy's compiled binaries (which
scikit-learn depends on internally) while numpy's still load fine. The
corpora here are small (a resume's worth of bullets, saved job
descriptions, a Q&A bank) so a dense numpy implementation is plenty fast.
"""
import math
import re
from collections import Counter

import numpy as np

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "did", "do", "does", "doing", "down", "for", "from", "had", "has",
    "have", "having", "he", "her", "here", "hers", "him", "his", "how", "i",
    "if", "in", "into", "is", "it", "its", "itself", "me", "more", "most",
    "my", "no", "nor", "not", "of", "on", "once", "only", "or", "other",
    "our", "ours", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them",
    "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "we", "were", "what",
    "when", "where", "which", "while", "who", "whom", "why", "will",
    "with", "you", "your", "yours", "yourself",
}


def tokenize(text: str) -> list[str]:
    words = [w for w in _TOKEN_RE.findall(text.lower()) if w not in _STOPWORDS]
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return words + bigrams


class TfidfIndex:
    """Fit on a list of raw document strings, then query with cosine similarity."""

    def __init__(self, documents: list[str]):
        self.n_docs = len(documents)
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None
        self.matrix: np.ndarray | None = None

        if not documents:
            return

        doc_tokens = [tokenize(doc) for doc in documents]
        doc_freq: Counter[str] = Counter()
        for tokens in doc_tokens:
            doc_freq.update(set(tokens))

        self.vocab = {term: i for i, term in enumerate(sorted(doc_freq))}
        vocab_size = len(self.vocab)

        # smooth idf, matching sklearn's default: ln((1+n)/(1+df)) + 1
        self.idf = np.zeros(vocab_size)
        for term, idx in self.vocab.items():
            self.idf[idx] = math.log((1 + self.n_docs) / (1 + doc_freq[term])) + 1.0

        self.matrix = np.zeros((self.n_docs, vocab_size))
        for row, tokens in enumerate(doc_tokens):
            counts = Counter(tokens)
            for term, count in counts.items():
                idx = self.vocab.get(term)
                if idx is not None:
                    self.matrix[row, idx] = count * self.idf[idx]

        self.matrix = _l2_normalize_rows(self.matrix)

    def _vectorize_query(self, text: str) -> np.ndarray:
        vec = np.zeros(len(self.vocab))
        counts = Counter(tokenize(text))
        for term, count in counts.items():
            idx = self.vocab.get(term)
            if idx is not None:
                vec[idx] = count * self.idf[idx]
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def query(self, text: str) -> np.ndarray:
        """Returns a cosine-similarity score per document, in the original document order."""
        if self.matrix is None or self.n_docs == 0:
            return np.array([])
        query_vec = self._vectorize_query(text)
        return self.matrix @ query_vec


def _l2_normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms
