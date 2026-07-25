import json
import re
from pathlib import Path

html_path = Path("data/graph_explorer.html")
json_path = Path("data/graph_data.json")

print("Reading HTML file...")
content = html_path.read_text(encoding="utf-8")

m = re.search(r"let fullGraphData = (\{.*?\});", content, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    print(f"Extracted {len(data.get('nodes', []))} nodes and {len(data.get('links', []))} links.")
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Successfully saved graph data to {json_path}")
else:
    print("fullGraphData token not found in graph_explorer.html")
