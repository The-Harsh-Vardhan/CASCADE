import sys
import re
import json
from pathlib import Path
from blast_radius.config import settings
from blast_radius.fusion.mapper import _load_page_analyses_from_outputs, _STOPWORDS
from blast_radius.models import Requirement

req_path = Path(settings.data_dir) / "requirements" / "requirements.json"
reqs = [Requirement.model_validate(r) for r in json.loads(req_path.read_text(encoding="utf-8"))]
pages = _load_page_analyses_from_outputs()


stopwords = set(_STOPWORDS) | {
    "the", "a", "an", "in", "of", "to", "for", "with", "on", "at", "from", "by", "about",
    "as", "into", "like", "through", "after", "over", "between", "out", "against", "during",
    "without", "before", "under", "around", "among", "and", "or", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "can", "could", "should",
    "would", "may", "might", "must", "shall", "will", "this", "that", "these", "those", "it",
    "its", "user", "page", "documenso", "document", "documents"
}

ui_vocab = set()
for page in pages:
    comps = page.get("ui_components", [])
    for comp in comps:
        label = comp if isinstance(comp, str) else comp.get("label", "")
        if label:
            words = set(re.findall(r"\b[a-z]{3,}\b", label.lower())) - stopwords
            ui_vocab.update(words)

absent_count = 0
absent_samples = []
for req in reqs:
    if req.req_type not in ("feature", "user_story"):
        continue
    req_words = set(re.findall(r"\b[a-z]{3,}\b", (req.title + " " + req.text).lower())) - stopwords
    overlap = len(req_words & ui_vocab)
    if overlap < 2:
        absent_count += 1
        absent_samples.append((req.requirement_id, req.title, overlap))

print(f"Filtered absent count: {absent_count}")
print("Sample absent reqs:")
for sample in absent_samples[:10]:
    print(f"  {sample[0]}: {sample[1][:60]} (overlap={sample[2]})")
