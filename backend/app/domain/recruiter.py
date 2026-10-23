"""Recruiter roles. Pure Python, no I/O.

An Admin is a Recruiter whose role is ``admin``. The role is the single source
of truth: the roster shows an Admin's Regions as ``*``, but nothing decides
Admin-ness from that. The RLS policy (migration 0002) checks the same role.
"""

ADMIN_ROLE = "admin"


def is_admin(role: str) -> bool:
    return role == ADMIN_ROLE
