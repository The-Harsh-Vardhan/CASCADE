"""
flows/seeder.py — Alias wrapper for blast_radius.flows.seeder.
Allows `from flows.seeder import seed_user_flows` as specified in assignment docs.
"""

from blast_radius.flows.seeder import DOCUMENSO_USER_FLOWS, seed_user_flows

__all__ = ["DOCUMENSO_USER_FLOWS", "seed_user_flows"]
