"""Tests for the investigator agent's safety checks and the law index's rule-number repair.

Run:  python -m pytest tests
These need no database and no AWS access.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import ACCUSE, _check_citations, _nums, _remove_accusing_sentences, _strip_quotes  # noqa: E402
from pipeline.build_law_index import _chain, _variants  # noqa: E402


# ---------- numbers ----------
def test_nums_reads_bangla_digits_and_commas():
    assert _nums("২৫.৭০ কোটি টাকা, ১,৮১৬টি চুক্তি") == {"25.7", "1816"}


def test_nums_matches_tool_format():
    tool = '{"total_value": "Tk 25.70 crore", "contracts_won": 26}'
    brief = "The firm won 26 contracts worth Tk 25.70 crore [S1]."
    assert _nums(brief.replace("[S1]", "")) <= _nums(tool)


# ---------- citations ----------
def test_unknown_citations_are_removed():
    text, bad = _check_citations("Fact one [S1]. Fact two [S9]. Both [S1, S2].", {"S1", "S2"})
    assert text == "Fact one [S1]. Fact two. Both [S1][S2]."
    assert bad == ["S9"]


# ---------- wording ----------
def test_accusing_words_found_in_english_and_bangla():
    assert ACCUSE.search("The firm is corrupt")
    assert ACCUSE.search("possible collusion with the office")
    assert ACCUSE.search("এই প্রতিষ্ঠান দুর্নীতি করেছে")
    assert not ACCUSE.search("The firm was officially debarred for a fake payment certificate")


def test_quoted_official_reason_is_not_counted():
    assert not ACCUSE.search(_strip_quotes('The reason on record is "fraudulent practice in tender 1".'))


def test_accusing_sentence_removed_but_heading_and_rest_kept():
    text, removed = _remove_accusing_sentences("### Summary\nThe firm won 26 contracts [S1]. It is clearly corrupt.")
    assert removed == 1
    assert text == "### Summary\nThe firm won 26 contracts [S1]."


# ---------- law index: rule numbers misread by machine reading ----------
def test_variants_cover_common_misreads():
    assert 40 in _variants("৮০")        # ৪ read as ৮
    assert 68 in _variants("৬৮১")       # danda । read as ১
    assert 66 in _variants("৬৬")


def test_chain_repairs_sequence_and_drops_impossible_numbers():
    raw = ["১", "২", "৩", "৮", "৫", "৬", "২২৯", "৭"]     # "৮" should be 4, "২২৯" is noise
    cands = [{"opts": _variants(s)} for s in raw]
    got = _chain(cands)
    assert [got[i] for i in sorted(got)] == [1, 2, 3, 4, 5, 6, 7]
    assert 6 not in got                    # the noisy heading is not given a number


def test_citation_ranges_are_expanded():
    text, bad = _check_citations("Recent work [S2-S4] and [S5–6].", {"S2", "S3", "S4", "S5", "S6"})
    assert text == "Recent work [S2][S3][S4] and [S5][S6]."
    assert bad == []


def test_hindi_letters_swapped_for_bangla_and_danda_kept():
    from app.agent import _fix_script
    assert _fix_script("প্রদर्शन।") == "প্রদর্শন।"
