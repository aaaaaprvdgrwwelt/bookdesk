from bookdesk.matcher import score_candidate
from bookdesk.providers.base import Candidate, SearchQuery, author_overlap


def test_author_overlap_full_match():
    assert author_overlap(["J.R.R. Tolkien"], ["J.R.R. Tolkien"]) == 1.0


def test_author_overlap_partial_match():
    overlap = author_overlap(["Tolkien", "Someone Else"], ["Tolkien"])
    assert overlap == 0.5


def test_author_overlap_empty_side_is_zero():
    # Fehlende Autorenangabe darf den Titel-Treffer nicht zunichtemachen -
    # dafuer muss author_overlap hier 0 statt eine Exception liefern.
    assert author_overlap([], ["Tolkien"]) == 0.0
    assert author_overlap(["Tolkien"], []) == 0.0


def test_author_overlap_ignores_case_and_punctuation():
    assert author_overlap(["j.r.r. tolkien"], ["J R R Tolkien"]) == 1.0


def test_score_candidate_exact_title_and_author_is_high():
    query = SearchQuery(title="The Hobbit", authors=["J.R.R. Tolkien"])
    candidate = Candidate(source="openlibrary", external_id="1",
                          title="The Hobbit", authors=["J.R.R. Tolkien"])
    score = score_candidate(query, candidate)
    assert score == 100


def test_score_candidate_title_only_still_scores_via_title_weight():
    query = SearchQuery(title="The Hobbit", authors=[])
    candidate = Candidate(source="openlibrary", external_id="1",
                          title="The Hobbit", authors=["J.R.R. Tolkien"])
    score = score_candidate(query, candidate)
    assert score == 70  # nur der Titel-Anteil (70%), Autor-Anteil bleibt 0


def test_score_candidate_unrelated_titles_score_low():
    query = SearchQuery(title="The Hobbit", authors=["J.R.R. Tolkien"])
    candidate = Candidate(source="openlibrary", external_id="1",
                          title="Pride and Prejudice", authors=["Jane Austen"])
    score = score_candidate(query, candidate)
    assert score < 30


def test_score_candidate_caps_at_100():
    query = SearchQuery(title="Dune", authors=["Frank Herbert"])
    candidate = Candidate(source="openlibrary", external_id="1",
                          title="Dune", authors=["Frank Herbert"])
    assert score_candidate(query, candidate) <= 100
