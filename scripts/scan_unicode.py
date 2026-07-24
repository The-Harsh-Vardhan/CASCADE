import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

hits = []
for root, _, files in os.walk('blast_radius'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            text = open(path, encoding='utf-8').read()
            for i, line in enumerate(text.splitlines(), 1):
                if '\u2192' in line or '\u2500' in line:
                    hits.append(f"{path}:{i}: {line.strip()[:80]}")

if hits:
    print("Files with Unicode arrows/box chars in print/code lines:")
    for h in hits:
        print(h)
else:
    print("No Unicode arrows found.")
