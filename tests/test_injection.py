"""Unit tests for context injection modes, truncation, and language suffix.

These are protocol invariants — the experiment runner and the MCP server
both depend on identical behaviour, so regressions here break either the
service or the paper's injection-mode experiment.
"""

from ploidy.injection import (
    append_language,
    build_deep_prompt,
    format_context,
    get_system_prompt_for_mode,
    truncate_context,
)


class TestFormatContext:
    def test_raw_mode_prefixes_header(self):
        out = format_context("some context", "raw")
        assert "Context about this code/system" in out
        assert "some context" in out

    def test_memory_mode_numbers_observations(self):
        out = format_context("line one\nline two\nline three", "memory")
        assert "Observation #1" in out
        assert "Observation #2" in out
        assert "Observation #3" in out
        assert "line one" in out
        assert "Project Memory" in out

    def test_memory_mode_skips_blank_lines_with_contiguous_indices(self):
        # Blank lines are filtered before enumeration so observation
        # numbers stay contiguous regardless of input formatting.
        out = format_context("line one\n\n\nline two", "memory")
        assert out.count("**Observation #") == 2
        assert "Observation #1" in out
        assert "Observation #2" in out
        assert "Observation #3" not in out
        assert "line one" in out
        assert "line two" in out

    def test_skills_mode_prefixes_each_line_with_rule(self):
        out = format_context("line1\nline2", "skills")
        assert "RULE: line1" in out
        assert "RULE: line2" in out

    def test_claude_md_mode_wraps_in_project_instructions(self):
        out = format_context("ctx", "claude_md")
        assert "<project-instructions>" in out
        assert "</project-instructions>" in out
        assert "# CLAUDE.md" in out

    def test_unknown_mode_falls_back_to_raw(self):
        # Paper §4 injection-mode sweep depends on this fallback so a
        # typoed mode string doesn't silently produce wrong experimental
        # conditions.
        out = format_context("ctx", "not_a_real_mode")
        assert "Context about this code/system" in out


class TestSystemPromptForMode:
    def test_system_prompt_mode_returns_formatted_text(self):
        out = get_system_prompt_for_mode("project context", "system_prompt")
        assert out is not None
        assert "senior engineer" in out
        assert "project context" in out

    def test_other_modes_return_none(self):
        assert get_system_prompt_for_mode("ctx", "raw") is None
        assert get_system_prompt_for_mode("ctx", "memory") is None
        assert get_system_prompt_for_mode("ctx", "skills") is None
        assert get_system_prompt_for_mode("ctx", "claude_md") is None


class TestBuildDeepPrompt:
    def test_raw_mode_prepends_context_to_user_prompt(self):
        user, system = build_deep_prompt("ctx", "task", mode="raw")
        assert "task" in user
        assert "ctx" in user
        assert system is None

    def test_system_prompt_mode_splits_context_into_system(self):
        user, system = build_deep_prompt("ctx", "task", mode="system_prompt")
        assert user == "task"
        assert system is not None
        assert "ctx" in system

    def test_empty_context_returns_prompt_with_no_system(self):
        user, system = build_deep_prompt("", "task")
        assert user == "task"
        assert system is None

    def test_context_pct_is_applied_before_formatting(self):
        long_ctx = "First sentence here. Second sentence here. Third here."
        user, _ = build_deep_prompt(long_ctx, "task", mode="raw", context_pct=40)
        # 40% of the long string keeps the head only; "Third" must be gone.
        assert "Third" not in user


class TestTruncateContext:
    def test_pct_100_returns_full_context(self):
        assert truncate_context("a.b.c.", 100) == "a.b.c."

    def test_pct_0_returns_empty(self):
        assert truncate_context("a.b.c.", 0) == ""

    def test_snaps_to_sentence_boundary_when_period_is_near_end(self):
        # target_len lands past the period and satisfies the 0.7 threshold.
        out = truncate_context("First sentence here. Second sentence.", 70)
        assert out == "First sentence here."

    def test_hard_cut_when_no_period_in_range(self):
        out = truncate_context("abcdefghijklmnop", 50)
        # No period to snap to — hard character cut.
        assert out == "abcdefgh"


class TestAppendLanguage:
    def test_english_is_noop(self):
        assert append_language("prompt", "en") == "prompt"

    def test_korean_appends_instruction(self):
        out = append_language("prompt", "ko")
        assert out.startswith("prompt")
        assert "한국어" in out

    def test_japanese_appends_instruction(self):
        out = append_language("prompt", "ja")
        assert "日本語" in out

    def test_chinese_appends_instruction(self):
        out = append_language("prompt", "zh")
        assert "中文" in out

    def test_unknown_language_is_noop(self):
        # Mirrors format_context's defensive fallback: unknown code → no
        # suffix rather than a KeyError in the experiment runner.
        assert append_language("prompt", "xx") == "prompt"
