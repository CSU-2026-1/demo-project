from __future__ import annotations

from abc import ABC

from app.repositories.base import BaseRepository


class BaseService(ABC):
    """Base class to keep shared typing and helpers for services."""

    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository
