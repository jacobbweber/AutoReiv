"""
Librarian Tools compatibility wrapper (Delegates to universal WikiTools) [REQ-WIKI-005].
"""

from src.application.skills.wiki_tools import LibrarianTools, WikiTools

__all__ = ["WikiTools", "LibrarianTools"]
