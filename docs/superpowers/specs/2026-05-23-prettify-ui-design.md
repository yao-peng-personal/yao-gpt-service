# Prettify UI — Design Spec

## Scope

Polish the Gradio chat frontend with better visuals.

## Changes

### 1. Theme
- Apply `gr.themes.Soft()` to `gr.Blocks()` for modern defaults (rounded corners, typography, spacing).

### 2. Chat bubbles
- Inject CSS via `demo.launch(css=...)` to give user and assistant messages distinct background colors and spacing.
- User: light purple/blue tint, assistant: light gray.

### 3. Avatars
- Set `avatar_images` on `gr.Chatbot` — person emoji for user, robot emoji for assistant.

### 4. Layout
- Tweak sidebar scale from 2→3 and chat from 8→9 for slightly cleaner proportions.

### Files affected
- `frontend/gradio_app.py`
- `frontend/run_frontend.py` (CSS goes through `launch()`)
