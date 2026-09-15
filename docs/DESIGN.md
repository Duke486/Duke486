# Playful profile design

A personal collection of code, games, anime and reading. Aqua and Miku green lead; peach, pink, lilac and lime provide a small rainbow across the collection.

- Interest tiles are 128 × 148 px, with 3 px outer spacing and a borderless rounded pastel surface. Character tiles are 82 × 148 for three columns on phones; portraits are 70 × 106 with meet fitting, never cropped; covers use 64 × 96 and preserve the whole artwork; game logos are contained, not cropped.
- Each tile holds its image and caption together. Do not remove all surfaces and leave tiny images floating in wide whitespace. Do not return to giant portrait cards.
- The header is 800 × 210, with the original Miku/Tamako artwork and a clipped rainbow wave. Section labels use small topic-specific line icons.
- Preserve the alternating Chinese/English typewriter SVG. It uses native SVG discrete animation for type, hold, erase and language switch, with a moving blinking cursor. The original wording is retained.
- Keep the profile terse. No duplicate text navigation, source-method explanations, update-date boilerplate or public-profile disclaimers on the main page. Details belong in maintenance documentation.
- Steam displays four verified games. When the current source offers fewer than four, retain previously verified entries, preserving per-game observed_at. Never invent a game or playtime.
- Trakt currently exposes a private profile. Two tested public widgets returned empty content. Use a designed profile-link card; do not display empty widgets or claim access to private history.
- Fixed height is only for small tiles. Wide images use automatic height so GitHub mobile padding does not produce letterboxing.

## Visual acceptance

Inspect the full composition, not just individual SVG bounds. Confirm the actual viewport before measuring. Check real GitHub at 360 × 800 and 390 × 844: other interest tiles stay 128 × 148 and two columns; character tiles stay 82 × 148 and three columns, not fill half the viewport. Check desktop, light/dark, complete captions, preserved image ratios and the typewriter at different points in its cycle.

This supersedes the overly austere previous version. Removing generic decoration does not mean removing color, grouping, personality or the original animation.
