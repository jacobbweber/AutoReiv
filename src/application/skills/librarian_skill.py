"""
Librarian Skill compatibility wrapper (Delegates to universal WikiSkill) [REQ-WIKI-005].
"""

from src.application.skills.wiki_skill import LibrarianSkill, WikiSkill

__all__ = ["WikiSkill", "LibrarianSkill"]
