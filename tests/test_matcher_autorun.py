"""AutoMatchWorker end-to-end: Kandidat finden, uebernehmen, Cover
dauerhaft speichern (wenn eingestellt) - mit einer Fake-Quelle statt
echtem Netzwerk."""
from __future__ import annotations

from pathlib import Path

from bookdesk import coverstore
from bookdesk.library import STATUS_MATCHED, STATUS_UNSURE, LibraryIndex
from bookdesk.matcher import AutoMatchWorker, MatchConfig
from bookdesk.providers.base import BookInfo, Candidate, MetadataProvider, SearchQuery


class FakeProvider(MetadataProvider):
    name = "fake"
    label = "Fake"

    def available(self):
        return True, ""

    def search(self, query: SearchQuery, limit: int = 10):
        return [Candidate(
            source=self.name, external_id="1", title="Last Licks",
            authors=["M. R. Forbes"], year=2023,
            cover_url="https://example.invalid/cover.jpg")]

    def details(self, candidate: Candidate) -> BookInfo:
        return BookInfo(
            title=candidate.title, authors=candidate.authors, year=candidate.year,
            cover_url=candidate.cover_url, source=candidate.source,
            external_id=candidate.external_id)


class FakeResponse:
    def raise_for_status(self):
        pass

    @property
    def content(self):
        return b"cover-bytes"


def make_library_with_item(tmp_path):
    library = LibraryIndex(tmp_path / "library.sqlite")
    path = tmp_path / "Last Licks.epub"
    path.write_bytes(b"")
    library.mark_scanned(path, tmp_path, title="Die letzte Chance",
                         authors=["M. R. Forbes"])
    return library, path


def test_automatch_sets_match_without_cover_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(coverstore.requests, "get", lambda *a, **k: FakeResponse())
    library, path = make_library_with_item(tmp_path)
    config = MatchConfig(providers=[FakeProvider()])  # cover_storage default: none
    worker = AutoMatchWorker([path], config, library)
    worker.run()

    item = library.get(path)
    assert item.title == "Last Licks"
    assert item.status in (STATUS_MATCHED, STATUS_UNSURE)
    assert item.cover_path is None
    library.close()


def test_automatch_saves_cover_next_to_book_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(coverstore.requests, "get", lambda *a, **k: FakeResponse())
    library, path = make_library_with_item(tmp_path)
    config = MatchConfig(providers=[FakeProvider()],
                         cover_storage=coverstore.STORAGE_NEXT_TO_BOOK)
    worker = AutoMatchWorker([path], config, library)
    worker.run()

    item = library.get(path)
    expected = path.with_suffix(".jpg")
    assert item.cover_path == str(expected)
    assert expected.read_bytes() == b"cover-bytes"
    library.close()


def test_automatch_saves_cover_to_directory_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(coverstore.requests, "get", lambda *a, **k: FakeResponse())
    library, path = make_library_with_item(tmp_path)
    covers_dir = tmp_path / "covers"
    config = MatchConfig(providers=[FakeProvider()],
                         cover_storage=coverstore.STORAGE_DIRECTORY,
                         cover_directory=str(covers_dir))
    worker = AutoMatchWorker([path], config, library)
    worker.run()

    item = library.get(path)
    assert item.cover_path is not None
    assert Path(item.cover_path).parent == covers_dir
    assert Path(item.cover_path).exists()
    library.close()
