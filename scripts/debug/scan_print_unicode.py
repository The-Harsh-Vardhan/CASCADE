import os, ast, sys
sys.stdout.reconfigure(encoding='utf-8')

# Find print() calls that contain Unicode arrow/box characters
problematic = []
for root, _, files in os.walk('blast_radius'):
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        lines = open(path, encoding='utf-8').readlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith('print(') and ('\u2192' in stripped or '\u2500' in stripped):
                problematic.append(f"{path}:{i}: {stripped[:100]}")

if problematic:
    print("PROBLEMATIC print() statements with Unicode arrows:")
    for p in problematic:
        print(p)
else:
    print("All print() statements are safe for Windows CP1252.")
