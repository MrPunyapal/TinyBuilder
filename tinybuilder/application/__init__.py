"""Framework-independent application primitives; no backend wiring yet."""
from .session import Session, DownloadOffer, Permissions, Cancelled

__all__ = ["Session", "DownloadOffer", "Permissions", "Cancelled"]
