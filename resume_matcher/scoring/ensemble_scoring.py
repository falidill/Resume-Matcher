from __future__ import annotations
from typing import List, Dict, Tuple
import re
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer, util

_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL

def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def split_sentences(t: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", t) if s.strip()]

def embedding_similarity(resume_chunks: List[str], jd_chunks: List[str]) -> float:
    if not resume_chunks or not jd_chunks:
        return 0.0
    model = _get_model()
    R = model.encode(resume_chunks, normalize_embeddings=True)
    J = model.encode(jd_chunks, normalize_embeddings=True)
    sim = util.cos_sim(R, J).cpu().numpy()
    k = min(3, sim.shape[1])
    topk = np.partition(sim, -k, axis=1)[:, -k:]
    score = float(topk.mean())
    return (score + 1) / 2

def load_ontology(path: str | Path) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def extract_terms(text: str, vocab: List[str]) -> List[str]:
    t = text.lower()
    found = []
    for term in vocab:
        term_l = term.lower().strip()
        pattern = r"(?<![\w\-])" + re.escape(term_l).replace(r"\ ", r"[ \-]") + r"(?![\w\-])"
        if re.search(pattern, t):
            found.append(term)
    return found

def skills_coverage(resume_text: str, jd_text: str, ontology: Dict[str, List[str]]) -> Tuple[float, List[str], List[Tuple[str, float]]]:
    skills_vocab = sorted({s for bucket in ontology.values() for s in bucket})
    jd_skills = set(extract_terms(jd_text, skills_vocab))
    res_skills = set(extract_terms(resume_text, skills_vocab))
    if not jd_skills:
        return 0.0, sorted(list(res_skills)), []
    inter = jd_skills & res_skills
    jd_weight = len(jd_skills) or 1
    hit_weight = len(inter)
    coverage = hit_weight / jd_weight
    missing = [(s, 1.0) for s in sorted(jd_skills - res_skills)]
    return float(coverage), sorted(list(inter)), missing

DEFAULT_VERBS = [
    "built","designed","automated","optimized","deployed","analyzed","modeled",
    "visualized","orchestrated","led","improved","reduced","increased","streamlined",
    "migrated","integrated","refactored","monitored","tested","validated"
]

def keyword_alignment(resume_text: str, jd_text: str, verbs: List[str] | None = None) -> float:
    verbs = verbs or DEFAULT_VERBS
    r = set(extract_terms(resume_text, verbs))
    j = set(extract_terms(jd_text, verbs))
    if not j:
        return 0.0
    return len(r & j) / len(j)

_METRIC_RE = re.compile(r"(\d+(\.\d+)?%|\$?\d+[kKmM]?|\b\d+\b (days?|weeks?|months?|hours?))")

def evidence_score(resume_lines: List[str]) -> float:
    if not resume_lines:
        return 0.0
    metric_lines = sum(1 for line in resume_lines if _METRIC_RE.search(line))
    return min(1.0, metric_lines / max(1, len(resume_lines)))

def compute_score(resume_text: str, jd_text: str, ontology_path: str | Path) -> Dict:
    resume_text = clean_text(resume_text)
    jd_text = clean_text(jd_text)
    resume_chunks = split_sentences(resume_text)
    jd_chunks = split_sentences(jd_text)

    emb = embedding_similarity(resume_chunks, jd_chunks)
    cov, aligned, missing = skills_coverage(resume_text, jd_text, load_ontology(ontology_path))
    verbs = keyword_alignment(resume_text, jd_text)
    evid = evidence_score(resume_chunks)

    total = 40*emb + 30*cov + 15*verbs + 15*evid
    total = max(0.0, min(100.0, round(total, 1)))

    return {
        "total_score": total,
        "subscores": {
            "embedding_similarity": round(100*emb, 1),
            "skills_coverage": round(100*cov, 1),
            "keyword_alignment": round(100*verbs, 1),
            "evidence": round(100*evid, 1),
        },
        "aligned_skills": aligned,
        "missing_skills": [{"term": t, "importance": w} for t, w in missing],
    }
