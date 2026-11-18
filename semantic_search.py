"""Find relevant assessment evidence with a pretrained sentence transformer.

The model converts text into vectors. Similar vectors suggest related meaning;
that score is a search aid, never a crop suitability score or probability.
"""

from functools import lru_cache
import os
from pathlib import Path
from threading import RLock

from assessment_summary import build_summary
from evidence import assessment_facts

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_CACHE = Path(
    os.environ.get("CROPNOVA_MODEL_CACHE", Path(__file__).parent / "instance" / "models")
)
MODEL_LOCK = RLock()
_encoder = None


class SearchUnavailable(RuntimeError):
    """The local model has not been prepared or could not be loaded."""


def load_encoder(*, allow_download=False):
    """Load once on CPU. Web requests never start a model download."""
    global _encoder
    with MODEL_LOCK:
        if _encoder is not None:
            return _encoder
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(2)
            _encoder = SentenceTransformer(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_folder=str(MODEL_CACHE),
                device="cpu",
                local_files_only=not allow_download,
                trust_remote_code=False,
                token=False,
                model_kwargs={"use_safetensors": True},
            )
        except (ImportError, OSError, ValueError, RuntimeError) as error:
            raise SearchUnavailable("The local evidence-search model is not ready.") from error
        return _encoder


def assessment_documents(report):
    """Build searchable notes from this saved assessment, not unrelated crops.

    Recheck source review and fact scope before exposing agricultural references.
    An unanswered input check may still be explained as an assessment finding.
    """
    summary = build_summary(report)
    sources = {
        s["source_id"]: s
        for s in report.get("evidence", [])
        if s.get("review_status") == "reviewed_for_inclusion"
    }
    facts = assessment_facts(report)
    eligible_ids = {fact["fact_id"] for fact in facts}
    records = []
    for crop in summary["candidates"]:
        supported_sources = {
            sid for f in facts if f.get("crop_id") in {crop["id"], "all"} for sid in f["source_ids"]
        }
        overview, overview_sources = [], {}
        for index, check in enumerate(crop["checks"]):
            # A shared source URL is not enough: this exact finding must use
            # eligible facts, including its own region and property.
            if not set(check["fact_ids"]).issubset(eligible_ids):
                continue
            check_sources = [s for s in check["sources"] if s["source_id"] in supported_sources]
            # Do not turn unreviewed, out-of-region or other-crop evidence into a
            # search result simply because its wording looks similar.
            if check["sources"] and len(check_sources) != len(check["sources"]):
                continue
            text = (
                f"{crop['name']}. {check['name']}. Finding: "
                f"{ {'satisfied':'matches','violated':'needs attention','unknown':'unresolved'}[check['status']] }. "
                f"Your entry: {check['entered']}. Reference: {check['reference']}. {check['reason']}"
            )
            records.append(
                {
                    "id": f"{crop['id']}:check:{index}",
                    "crop_id": crop["id"],
                    "title": crop["name"] + " · " + check["name"],
                    "text": text,
                    "sources": check_sources,
                }
            )
            overview.append(check["name"] + ": " + check["reason"])
            overview_sources.update({s["source_id"]: s for s in check_sources})
        if overview:
            records.append(
                {
                    "id": crop["id"] + ":overview",
                    "crop_id": crop["id"],
                    "title": crop["name"] + " · Overall finding",
                    "text": crop["name"] + ". " + crop["label"] + ". " + " ".join(overview),
                    "sources": list(overview_sources.values()),
                }
            )
    return records


@lru_cache(maxsize=32)
def document_vectors(texts):
    # Normalised vectors make a dot product equivalent to cosine similarity.
    return load_encoder().encode(list(texts), normalize_embeddings=True, show_progress_bar=False)


def search_assessment(report, question, crop_id=None, *, top_k=3, minimum_similarity=0.28):
    records = assessment_documents(report)
    if crop_id:
        records = [record for record in records if record["crop_id"] == crop_id]
    if not records:
        return []
    try:
        import numpy as np

        with MODEL_LOCK:
            vectors = document_vectors(tuple(record["text"] for record in records))
            query = load_encoder().encode(
                [question], normalize_embeddings=True, show_progress_bar=False
            )[0]
            scores = np.asarray(vectors) @ np.asarray(query)
        if not np.isfinite(scores).all():
            raise SearchUnavailable("Search returned invalid similarity values.")
        ordered = np.argsort(-scores, kind="stable")[:top_k]
        return [
            {**records[int(index)], "similarity": float(scores[index])}
            for index in ordered
            if scores[index] >= minimum_similarity
        ]
    except SearchUnavailable:
        raise
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        raise SearchUnavailable("Evidence search is temporarily unavailable.") from error
