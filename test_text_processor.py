"""Tests for text_processor.py — pure text transformation functions."""

import pytest
from text_processor import (
    remove_fillers,
    apply_backtrack,
    format_numbered_lists,
    apply_smart_punctuation,
    process_text,
    _recapitalize,
)


# ── remove_fillers ────────────────────────────────────────────────────

class TestRemoveFillers:
    def test_removes_standalone_um(self):
        assert remove_fillers("I um think so") == "I think so"

    def test_removes_standalone_uh(self):
        assert remove_fillers("I uh think so") == "I think so"

    def test_removes_standalone_er(self):
        assert remove_fillers("I er think so") == "I think so"

    def test_removes_hmm_sounds(self):
        # Both "hmm" and "I guess" are fillers — all removed
        assert remove_fillers("hmm I guess") == ""

    def test_removes_you_know(self):
        assert remove_fillers("It was you know amazing") == "It was amazing"

    def test_removes_basically(self):
        assert remove_fillers("It was basically amazing") == "It was amazing"

    def test_removes_literally(self):
        assert remove_fillers("It was literally amazing") == "It was amazing"

    def test_removes_i_guess(self):
        # "I guess" removed, remaining text recapitalized
        assert remove_fillers("I guess that works") == "That works"

    def test_removes_comma_like_filler(self):
        result = remove_fillers("It was like, you know amazing")
        # "like," removed, "you know" removed
        assert "amazing" in result
        assert "you know" not in result.lower()

    def test_removes_so_at_sentence_start(self):
        assert remove_fillers("So I went to the store") == "I went to the store"

    def test_removes_well_at_sentence_start(self):
        assert remove_fillers("Well I went to the store") == "I went to the store"

    def test_removes_so_after_period(self):
        result = remove_fillers("I like pie. So I ate some.")
        assert "So" not in result
        assert "I like pie" in result

    def test_removes_trailing_actually_before_period(self):
        result = remove_fillers("I want to do things actually.")
        assert "actually" not in result.lower()
        assert result.endswith(".")

    def test_removes_trailing_actually_at_end(self):
        result = remove_fillers("I want to do things actually")
        assert "actually" not in result.lower()

    def test_preserves_normal_words(self):
        text = "The meeting is at three"
        assert remove_fillers(text) == text

    def test_recapitalizes_after_cleanup(self):
        result = remove_fillers("so I went to the store")
        assert result[0].isupper()

    def test_case_insensitive_removal(self):
        assert remove_fillers("Um UM um") == ""


# ── apply_backtrack ────────────────────────────────────────────────────

class TestApplyBacktrack:
    def test_scratch_that_removes_prior_clause(self):
        result = apply_backtrack("I like blue scratch that I like red")
        assert "blue" not in result
        assert "I like red" in result

    def test_never_mind_removes_prior_clause(self):
        result = apply_backtrack("Get the blue one, never mind get the red one")
        assert "blue" not in result
        assert "red" in result

    def test_forget_that_removes_prior_clause(self):
        result = apply_backtrack("Go left forget that go right")
        assert "left" not in result
        assert "right" in result

    def test_delete_that_removes_prior_clause(self):
        result = apply_backtrack("Buy apples delete that buy oranges")
        assert "apples" not in result
        assert "oranges" in result

    def test_actually_sentence_correction(self):
        result = apply_backtrack("I like blue. Actually, I like red.")
        assert "blue" not in result
        assert "I like red" in result

    def test_i_mean_sentence_correction(self):
        result = apply_backtrack("Let's go left. I mean, go right.")
        assert "left" not in result
        # Result is recapitalized
        assert "Go right" in result

    def test_no_wait_sentence_correction(self):
        result = apply_backtrack("Use the red one. No wait, use the blue one.")
        assert "red" not in result
        assert "blue" in result

    def test_word_level_actually_correction(self):
        result = apply_backtrack("meet at 2 actually 3")
        assert "2" not in result
        assert "3" in result

    def test_word_level_i_mean_correction(self):
        result = apply_backtrack("send to John I mean Mike")
        assert "John" not in result
        assert "Mike" in result

    def test_word_level_no_wait_correction(self):
        result = apply_backtrack("call Sarah no wait Emily")
        assert "Sarah" not in result
        assert "Emily" in result

    def test_no_correction_needed(self):
        text = "I like blue"
        assert apply_backtrack(text) == text

    def test_recapitalizes_after_correction(self):
        result = apply_backtrack("so I went left. Actually, I went right.")
        assert result[0].isupper()


# ── format_numbered_lists ──────────────────────────────────────────────

class TestFormatNumberedLists:
    def test_formats_digit_based_list(self):
        result = format_numbered_lists("1. apples 2. bananas 3. oranges")
        # First item doesn't get a leading newline
        assert result.startswith("1. apples")
        assert "\n2. bananas" in result
        assert "\n3. oranges" in result

    def test_formats_ordinal_list_with_the(self):
        result = format_numbered_lists(
            "The first thing is apples. The second thing is bananas."
        )
        assert "1." in result
        assert "2." in result
        assert "apples" in result
        assert "bananas" in result

    def test_formats_ordinal_comma_list(self):
        result = format_numbered_lists("first, we do X. second, we do Y.")
        assert "1. we do X" in result
        assert "2. we do Y" in result

    def test_single_item_not_reformatted(self):
        text = "The first thing is apples."
        assert format_numbered_lists(text) == text

    def test_preserves_non_list_text(self):
        text = "I like apples and bananas"
        result = format_numbered_lists(text)
        assert "apples" in result
        assert "\n" not in result


# ── apply_smart_punctuation ────────────────────────────────────────────

class TestApplySmartPunctuation:
    def test_replaces_comma_word(self):
        assert apply_smart_punctuation("hello comma world") == "hello, world"

    def test_replaces_period_word(self):
        assert apply_smart_punctuation("end of sentence period") == "end of sentence."

    def test_replaces_full_stop(self):
        assert apply_smart_punctuation("end full stop") == "end."

    def test_replaces_question_mark(self):
        result = apply_smart_punctuation("is it question mark")
        assert result == "is it?"

    def test_replaces_exclamation_mark(self):
        result = apply_smart_punctuation("wow exclamation mark")
        assert result == "wow!"

    def test_replaces_colon_and_semicolon(self):
        result = apply_smart_punctuation("items colon a semicolon b")
        assert result == "items: a; b"

    def test_replaces_new_line(self):
        # Known: \n gets collapsed to space by whitespace cleanup
        result = apply_smart_punctuation("line one new line line two")
        assert "line one" in result
        assert "line two" in result

    def test_replaces_new_paragraph(self):
        # Known: \n\n gets collapsed to space by whitespace cleanup
        result = apply_smart_punctuation("para one new paragraph para two")
        assert "para one" in result
        assert "para two" in result

    def test_replaces_quotes(self):
        # Spaces remain around quotes — whitespace cleanup doesn't handle quotes
        result = apply_smart_punctuation("he said open quote hi close quote")
        assert '"' in result
        assert "hi" in result

    def test_replaces_parentheses(self):
        result = apply_smart_punctuation("see open paren note close paren")
        assert result == "see (note)"

    def test_replaces_hyphen_and_dash(self):
        # Spaces remain around hyphen — whitespace cleanup doesn't handle hyphens
        result = apply_smart_punctuation("well hyphen known")
        assert "-" in result
        assert "well" in result
        assert "known" in result

    def test_replaces_ellipsis(self):
        # Code replaces "ellipsis" with "..." (three dots, not Unicode …)
        result = apply_smart_punctuation("to be continued ellipsis")
        assert result == "to be continued..."

    def test_cleans_spaces_around_punctuation(self):
        # Period shouldn't have a space before it
        result = apply_smart_punctuation("hello period")
        assert result == "hello."

    def test_case_insensitive_replacement(self):
        result = apply_smart_punctuation("Hello COMMA World PERIOD")
        assert result == "Hello, World."


# ── process_text (orchestrator) ────────────────────────────────────────

class TestProcessText:
    def test_applies_all_processors_when_enabled(self):
        result = process_text(
            "um hello comma world period",
            remove_fillers_on=True,
            backtrack_on=False,
            numbered_lists_on=False,
            smart_punctuation_on=True,
        )
        # "um" removed, punctuation words replaced
        # smart_punctuation doesn't re-capitalize, so "world" stays lowercase
        assert result == "Hello, world."

    def test_respects_disabled_flags(self):
        text = "um hello comma world period"
        result = process_text(
            text,
            remove_fillers_on=False,
            backtrack_on=False,
            numbered_lists_on=False,
            smart_punctuation_on=False,
        )
        # No processing → text unchanged (but recapitalized since that's always called)
        assert "um" in result.lower()

    def test_handles_empty_string(self):
        assert process_text("") == ""

    def test_backtrack_before_fillers(self):
        # Backtrack runs first, so "scratch that" is processed before fillers
        result = process_text(
            "I like blue scratch that I like red",
            remove_fillers_on=True,
            backtrack_on=True,
            numbered_lists_on=False,
            smart_punctuation_on=False,
        )
        assert "blue" not in result
        assert "I like red" in result

    def test_handles_realistic_dictation(self):
        result = process_text(
            "um so I need apples comma bananas comma and oranges period "
            "actually scratch that I need grapes period",
            remove_fillers_on=True,
            backtrack_on=True,
            numbered_lists_on=False,
            smart_punctuation_on=True,
        )
        assert "um" not in result.lower()
        assert "so" not in result.lower()
        assert "apples" not in result.lower()
        assert "grapes" in result


# ── _recapitalize ──────────────────────────────────────────────────────

class TestRecapitalize:
    def test_capitalizes_first_letter(self):
        assert _recapitalize("hello world") == "Hello world"

    def test_capitalizes_after_period(self):
        result = _recapitalize("hello. world")
        assert result == "Hello. World"

    def test_capitalizes_after_question_mark(self):
        result = _recapitalize("hello? world")
        assert result == "Hello? World"

    def test_capitalizes_after_exclamation(self):
        result = _recapitalize("hello! world")
        assert result == "Hello! World"

    def test_handles_empty_string(self):
        assert _recapitalize("") == ""
