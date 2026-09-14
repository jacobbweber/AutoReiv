"""
AutoReiv FastAPI Domain Routers.
"""

# CARD-313: ensure migrate routes mount onto settings.router
from src.web.routers import data_dir_migrate as _card313_data_dir_migrate  # noqa: F401
