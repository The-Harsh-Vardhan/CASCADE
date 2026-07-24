"""
pipeline/offline.py — Root alias wrapper for blast_radius.pipeline.offline.
"""

from blast_radius.pipeline.offline import run_offline_pipeline

__all__ = ["run_offline_pipeline"]

if __name__ == "__main__":
    run_offline_pipeline()
