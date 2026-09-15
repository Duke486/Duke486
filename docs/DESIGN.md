# Profile design constraints

This is a personal developer profile and a small collection of interests, not a product landing page.

- Keep the requested aqua and Miku green. Use the gradient only as a quiet header accent. Use flat backgrounds, 6 px corners on information cards, no shadows or decorative bubbles.
- Use plain section names. Avoid numbered editorial sections, generic welcome slogans, redundant captions and inspirational footer copy.
- The header is 640 × 150. Preserve the personal cat greeting in actual README text, not tiny text inside the illustration.
- Every interest item (Steam game, favorite title, reading entry, character) has a **128 × 108** SVG footprint. README declares both width and height. Interest images form an unboxed gallery, so each image does not need a border and background.
- Character portraits are 60 × 64 within that footprint. Covers and game images use `meet` to preserve the whole artwork. Titles stay at 12 px and remain linked to their full source title. Progress and playtime use a quieter 10 px caption.
- Steam has up to four real source records. No invented games or playtimes to fill empty slots.
- Project and statistics cards remain wider for legibility; these contain substantially more text than an interest thumbnail.

## Required visual checks

Read actual `innerWidth` / `innerHeight` after setting the browser viewport. A successful resize API call alone is not evidence of phone testing. At 360 × 800 and 390 × 844, measure rendered image rectangles and inspect screenshots. Interest cards must be 128 × 108, fit two columns, remain under 14% of viewport height, and produce no horizontal page overflow. Inspect both themes. Check the published GitHub page as well as the local preview; GitHub sanitizes markup and may apply different CSS.

## Research used

- [NN/g: Cards: UI-Component Definition](https://www.nngroup.com/articles/cards-component/) — cards consume space; homogeneous image collections can use a gallery without an enclosing box for each image.
- [The Crit: Does Your AI-Built App Look Vibe-Coded?](https://thecrit.co/resources/does-your-ai-built-app-look-vibe-coded) — diagnose excessive card styling, generic decoration and weak hierarchy; direct visual choices toward the content.

These principles guide this revision, not a claim that a particular color or radius can objectively prove whether a design was AI-generated.
