"""AstraCare backend package. Importing it loads backend/.env before any module reads the environment."""
from app import config as _config  # noqa: F401
