"""Einstellungen, gehalten in QSettings."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from PySide6.QtCore import QSettings

from deskkit.settings import as_bool as _bool

from . import coverstore
from .i18n import system_language
from .matcher import DEFAULT_THRESHOLD, MatchConfig
from .providers.base import MetadataProvider
from .providers.googlebooks import GoogleBooksProvider
from .providers.openlibrary import OpenLibraryProvider

#: OpenLibrary erwartet keinen speziellen Sprachcode, die Oberflaechensprache
#: reicht als Sprachfilter fuer die Beschreibung.
_OL_LANGUAGE = {"de": "de", "en": "en"}

RENAME_TEMPLATE_DEFAULT = "{author}/{series} #{series_index} - {title}{ext}"


@dataclass
class Settings:
    book_roots: list[str] = field(default_factory=list)
    use_openlibrary: bool = True
    use_googlebooks: bool = True
    threshold: int = DEFAULT_THRESHOLD
    rename_template: str = RENAME_TEMPLATE_DEFAULT
    language: str = "auto"
    cover_storage: str = coverstore.STORAGE_NONE
    cover_directory: str = ""

    @classmethod
    def load(cls, settings: QSettings) -> Settings:
        settings.beginGroup("bookdesk")
        obj = cls(
            book_roots=json.loads(settings.value("book_roots", "[]") or "[]"),
            use_openlibrary=_bool(settings.value("use_openlibrary"), True),
            use_googlebooks=_bool(settings.value("use_googlebooks"), True),
            threshold=int(settings.value("threshold", DEFAULT_THRESHOLD)),
            rename_template=settings.value(
                "rename_template", RENAME_TEMPLATE_DEFAULT)
            or RENAME_TEMPLATE_DEFAULT,
            language=settings.value("language", "auto") or "auto",
            cover_storage=settings.value("cover_storage", coverstore.STORAGE_NONE)
            or coverstore.STORAGE_NONE,
            cover_directory=settings.value("cover_directory", "") or "",
        )
        settings.endGroup()
        return obj

    def save(self, settings: QSettings) -> None:
        settings.beginGroup("bookdesk")
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                value = json.dumps(value)
            settings.setValue(key, value)
        settings.endGroup()
        settings.sync()

    # ------------------------------------------------------------------
    def ol_language(self) -> str:
        code = system_language() if self.language == "auto" else self.language
        return _OL_LANGUAGE.get(code, "en")

    def build_providers(self) -> list[MetadataProvider]:
        providers: list[MetadataProvider] = []
        if self.use_openlibrary:
            providers.append(OpenLibraryProvider())
        if self.use_googlebooks:
            providers.append(GoogleBooksProvider())
        return providers

    def build_config(self) -> MatchConfig:
        return MatchConfig(
            threshold=self.threshold, providers=self.build_providers(),
            cover_storage=self.cover_storage, cover_directory=self.cover_directory)
