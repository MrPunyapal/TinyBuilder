"""Offline-first, explicitly authorized model storage."""
from .catalog import CATALOG, CatalogEntry
from .paths import native_model_dir
from .manager import (
    CancellationToken, DownloadCancelled, DownloadProgress, DownloadRequest,
    ModelError, ModelManager, ModelSelection, ModelStatus, SpaceCheck,
)

__all__ = [
    "CATALOG", "CatalogEntry", "native_model_dir", "CancellationToken",
    "DownloadCancelled", "DownloadProgress", "DownloadRequest", "ModelError",
    "ModelManager", "ModelSelection", "ModelStatus", "SpaceCheck",
]
