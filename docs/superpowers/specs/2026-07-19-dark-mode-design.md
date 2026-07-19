# Dark Mode — Always-On Design

**Date:** 2026-07-19  
**Status:** Approved  

## Goal

Change the WhisperTool tkinter UI from the default system light theme to an always-on dark mode, consistent with the floating overlay window's existing dark teal aesthetic.

## Approach

Configure `ttk.Style` and classic `tk` widget colors programmatically — no new dependencies. Use the `clam` ttk theme on all platforms for maximum customizability (replacing `vista`/`aqua`).

## Color Palette

| Role         | Hex       | Used for                             |
|--------------|-----------|--------------------------------------|
| Background   | `#121212` | Root + main window background        |
| Surface      | `#1e1e2e` | LabelFrame/Frame interiors           |
| Primary text | `#e0e0e0` | Labels, buttons, entry fields        |
| Secondary    | `#888888` | Subtle labels, placeholder text      |
| Accent       | `#22d3ee` | Active elements, highlights          |
| Success      | `#22c55e` | Ready status dot                     |
| Danger       | `#ef4444` | Recording status dot                 |
| Processing   | `#f59e0b` | Transcribing status dot              |
| Polish       | `#8b5cf6` | AI polishing status dot              |
| Border       | `#333333` | Frame outlines, separators           |
| Selection    | `#0e7490` | Listbox item selection bg            |

## Scope

### main.py
- New method `_apply_dark_theme()` called at the start of `_build_ui()`
- Configures `ttk.Style` for all ttk widgets: TFrame, TLabelFrame, TLabel, TButton, TCheckbutton, TCombobox, TEntry, TScrollbar, TSeparator
- Sets direct colors on classic tk widgets: `tk.Listbox`, `tk.Text`, `tk.Canvas` (status dot)
- Sets root window `bg="#121212"`

### FloatingOverlay
- Already uses dark colors (`#0f172a`, `#1e293b`, `#22d3ee`, `#06b6d4`, `#0e7490`) — no changes needed

### text_processor.py
- No changes (no UI code)

## What Does NOT Change

- Hotkey capture behavior
- Model loading flow
- Audio recording / transcription pipeline
- AI rewriting logic
- Config file schema
- All functional behavior — purely visual

## Implementation Notes

- `ttk.Style.theme_use("clam")` is the key enabler — `vista`/`aqua` resist custom coloring
- Classic `tk` widgets (`Listbox`, `Text`) need explicit `bg`/`fg`/`selectbackground`/`selectforeground` properties
- `ttk` widget colors are configured via `style.configure("TWidget", fieldbackground=..., foreground=..., background=...)` and `style.map()` for state-specific colors
