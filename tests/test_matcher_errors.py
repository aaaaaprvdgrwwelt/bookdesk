"""collect_candidates()/identify(): ein Fehler bei einer Quelle (z. B.
ein erschoepftes Google-Books-Tageslimit) soll sichtbar werden, statt
ununterscheidbar von einem echten "kein Treffer" zu sein."""
from __future__ import annotations

import requests

from bookdesk.matcher import MatchConfig, collect_candidates, identify
from bookdesk.providers.base import (
    Candidate, MetadataProvider, SearchQuery,
)


class RateLimitedProvider(MetadataProvider):
    name = "ratelimited"
    label = "Ratelimited"

    def available(self):
        return True, ""

    def search(self, query, limit=10):
        response = requests.Response()
        response.status_code = 429
        raise requests.HTTPError(response=response)


class BrokenProvider(MetadataProvider):
    name = "broken"
    label = "Broken"

    def available(self):
        return True, ""

    def search(self, query, limit=10):
        raise ValueError("irgendwas ging schief")


class WorkingProvider(MetadataProvider):
    name = "working"
    label = "Working"

    def available(self):
        return True, ""

    def search(self, query, limit=10):
        return [Candidate(source=self.name, external_id="1", title=query.title,
                          authors=query.authors)]


def test_collect_candidates_records_rate_limit_error():
    errors: list[str] = []
    config = MatchConfig(providers=[RateLimitedProvider()])
    candidates = collect_candidates(SearchQuery(title="x"), config, errors=errors)
    assert candidates == []
    assert errors == ["Ratelimited: Tageslimit erreicht"]


def test_collect_candidates_records_generic_error():
    errors: list[str] = []
    config = MatchConfig(providers=[BrokenProvider()])
    collect_candidates(SearchQuery(title="x"), config, errors=errors)
    assert errors == ["Broken: Fehler"]


def test_collect_candidates_without_errors_list_still_works():
    config = MatchConfig(providers=[RateLimitedProvider()])
    candidates = collect_candidates(SearchQuery(title="x"), config)
    assert candidates == []


def test_one_provider_failing_does_not_block_another():
    config = MatchConfig(providers=[RateLimitedProvider(), WorkingProvider()])
    candidates = collect_candidates(SearchQuery(title="Titel"), config)
    assert len(candidates) == 1
    assert candidates[0].source == "working"


def test_identify_surfaces_rate_limit_in_note_when_nothing_found():
    config = MatchConfig(providers=[RateLimitedProvider()])
    info, score, note = identify(SearchQuery(title="x"), config)
    assert info is None
    assert score == 0
    assert "Tageslimit erreicht" in note


def test_identify_still_returns_plain_kein_treffer_without_provider_error():
    class EmptyProvider(MetadataProvider):
        name = "empty"
        label = "Empty"

        def available(self):
            return True, ""

        def search(self, query, limit=10):
            return []

    config = MatchConfig(providers=[EmptyProvider()])
    info, score, note = identify(SearchQuery(title="x"), config)
    assert note == "kein Treffer"
