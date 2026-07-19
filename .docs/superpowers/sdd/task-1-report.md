# Task 1 Report: Dark Mode Theme

## Status: DONE

## Commits
- `2939f39` feat: apply always-on dark mode theme

## Test Summary
Manual code review of all changes applied:

1. **Theme setup replaced** (line 404): Old `style.theme_use("vista"/"aqua")` block replaced with single call to `self._apply_dark_theme()`.

2. **New `_apply_dark_theme()` method added** (lines 432-528): Configures `clam` ttk theme with full dark palette:
   - Root window background: `#121212`
   - Frame/label surfaces: `#1e1e2e`
   - Text foreground: `#e0e0e0`
   - Accent (teal): `#22d3ee`
   - All ttk widget classes styled (TFrame, TLabelFrame, TLabel, TButton, TCheckbutton, TCombobox, TEntry, TScrollbar, TSeparator)
   - Classic tk defaults set via `option_add` for Listbox and Text
   - Combobox listbox dropdown themed to match

3. **Three per-widget overrides in `_build_ui()` updated:**
   - Status dot canvas: `bg="#1e1e2e"` added
   - Hint label "e.g. ...": `foreground="#888888"` (was `"gray"`)
   - Footer label "Double-click ...": `foreground="#888888"` (was `"gray"`)

## Concerns
- No runtime test was performed (no microphone/Whisper model available in this environment). The app imports `sounddevice`, `faster_whisper`, `pynput`, etc., which require hardware or system-level access not available in a headless/CI environment.
- The `clam` theme is used for cross-platform dark styling. On Windows, it will look different from the original `vista` theme -- this is intentional.
- The `FloatingOverlay` class's existing dark colors were left untouched as specified.
- On macOS, `ttk.Style().theme_use("clam")` may or may not be available; the `try/except` handles the fallback silently.
