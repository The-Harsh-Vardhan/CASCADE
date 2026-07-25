import json
import random

with open("../outputs/requirements/requirements.json") as f:
    reqs = json.load(f)

for r in random.sample(reqs, 10):
    print(f"[{r['id']}] {r['title']}")
    print(f"  Source: {r['source']} | Area: {r['feature_area']}")
    print(f"  Description: {r['description'][:100]}")
    print()