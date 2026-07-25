from blast_radius.crawl.page_analysis import load_all_page_snapshots
snaps = load_all_page_snapshots()
print(f"Count: {len(snaps)}")
s = snaps[0]
print(f"Type: {type(s)}")
attrs = [a for a in dir(s) if not a.startswith("_")]
print(f"Attrs: {attrs}")
if hasattr(s, "ui_components"):
    uc = s.ui_components
    print(f"ui_components type: {type(uc)}, len: {len(uc) if uc else 0}")
    if uc:
        print(f"First 2: {uc[:2]}")
else:
    print("NO ui_components attr")
    # Check if it's a dict-like
    if hasattr(s, "__dict__"):
        print(f"__dict__ keys: {list(s.__dict__.keys())[:10]}")
