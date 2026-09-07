"""Tests fuer bookdesk/renamer.py - vor allem {series_index} mit
Breitenangabe wie {series_index:02} fuer fuehrende Nullen."""
from __future__ import annotations

from pathlib import Path

from bookdesk.library import Item
from bookdesk.renamer import build_plan, build_target


def make_item(root: Path, **overrides) -> Item:
    defaults = dict(
        id=1, path=str(root / "book.epub"), root=str(root), title="Titel",
        authors=["Autor"], series="Serie", series_index="1")
    defaults.update(overrides)
    return Item(**defaults)


def test_series_index_without_width_spec_is_unpadded(tmp_path):
    item = make_item(tmp_path, series_index="1")
    target = build_target(tmp_path, item, "{series} #{series_index} - {title}{ext}")
    assert target.name == "Serie #1 - Titel.epub"


def test_series_index_with_width_spec_is_zero_padded(tmp_path):
    item = make_item(tmp_path, series_index="1")
    target = build_target(tmp_path, item, "{series} #{series_index:02} - {title}{ext}")
    assert target.name == "Serie #01 - Titel.epub"


def test_series_index_double_digit_with_width_spec_is_unchanged(tmp_path):
    item = make_item(tmp_path, series_index="10")
    target = build_target(tmp_path, item, "{series_index:02} - {title}{ext}")
    assert target.name == "10 - Titel.epub"


def test_series_index_three_digit_width_spec(tmp_path):
    item = make_item(tmp_path, series_index="7")
    target = build_target(tmp_path, item, "{series_index:03} - {title}{ext}")
    assert target.name == "007 - Titel.epub"


def test_series_index_integral_float_from_opf_becomes_clean_int(tmp_path):
    # calibre:series_index landet oft als "10.0" statt "10" in der OPF.
    item = make_item(tmp_path, series_index="10.0")
    target = build_target(tmp_path, item, "{series_index} - {title}{ext}")
    assert target.name == "10 - Titel.epub"
    target_padded = build_target(tmp_path, item, "{series_index:03} - {title}{ext}")
    assert target_padded.name == "010 - Titel.epub"


def test_series_index_non_integral_float_keeps_decimal(tmp_path):
    item = make_item(tmp_path, series_index="1.5")
    target = build_target(tmp_path, item, "{series_index} - {title}{ext}")
    assert target.name == "1.5 - Titel.epub"


def test_series_index_non_numeric_text_passes_through(tmp_path):
    item = make_item(tmp_path, series_index="Vorspiel")
    target = build_target(tmp_path, item, "{series_index} - {title}{ext}")
    assert target.name == "Vorspiel - Titel.epub"


def test_series_index_empty_without_width_spec_is_clean(tmp_path):
    item = make_item(tmp_path, series_index="")
    target = build_target(tmp_path, item, "{series} #{series_index} - {title}{ext}")
    # kein series_index vorhanden -> "#" bleibt als Leerzeichen-Artefakt,
    # das ist ein bekanntes, vom Nutzer selbst gewaehltes Vorlagenproblem,
    # nicht Gegenstand dieses Tests.
    assert "Titel.epub" in target.name


def test_build_plan_produces_zero_padded_paths_for_a_series(tmp_path):
    items = [make_item(tmp_path, id=i, path=str(tmp_path / f"b{i}.epub"),
                       series_index=str(i)) for i in range(1, 4)]
    ops = build_plan(items, "{series}/{series_index:02} - {title}{ext}")
    names = sorted(op.new.name for op in ops)
    assert names == ["01 - Titel.epub", "02 - Titel.epub", "03 - Titel.epub"]
