# HANDOFF — Key Signature Trainer

Repo: artificialfear/key-sig-trainer — live at https://artificialfear.github.io/key-sig-trainer/

Student-facing practice tool for Raven Band (Mat Graham, STEM Academy @ Bartlett). Practice only — no score tracking beyond per-device streaks.

## Files
- `index.html` — whole app (HTML/CSS/JS, no build step).
- `glyphs.js` — SVG path outlines for clefs, notehead, ♯ ♭ ♮, parentheses, extracted from the Bravura font (OFL, see BRAVURA-LICENSE.txt). Units: 250 = one staff space, y-up; render with `scale(k,-k)`.
- `tests/smoke.py` — Playwright smoke test (`python3 tests/smoke.py [--shots DIR]`). Includes a 4,000-line generator fuzz test.

## Design decisions (Mat, 2026-11-19)
- One tool, four modes (level ladder) rather than two tools.
- Students see their own **written** key. `INSTRUMENTS[].t` = fifths the written key sits above concert (B♭ +2, E♭ +3, F horn +1).
- Answers: letter + ♭/♮/♯ buttons, either order. No fingerings yet.
- Individual Chromebooks + viewboard ("Class display" toggle: bigger UI, Reveal, rotate instruments).
- Beginner concert keys B♭ E♭ F A♭ C.
- Practice only, no reporting.
- **Octave rule:** Mat didn't pick. The app uses the standard rule (accidental affects only that line/space until the barline), and the generator guarantees the answer never depends on it: any same-letter note in another octave after an accidental gets a printed courtesy accidental, and it's always placed after the carry note. The smoke test checks this against an "all octaves" reading.

## How it works
- Diatonic step = octave*7 + letter index (C4 = 28). Staff position = step − BASE[clef] (treble E4 = 30, bass G2 = 18).
- `evaluate(notes, km)` assigns `val` (−1/0/1) and `reason` (keysig, plain, explicit, carry, reset, courtesy) + `src` note index; feedback text comes from `reasonText`.
- Mode 1 changes key context every 4 questions; other modes every round.
- Settings in localStorage key `ksTrainer.settings` (per device).

## Dojo link
- The Band Ninja Dojo (artificialfear/raven-hub-code, dojo/src/MyProgress.js, KEYSIG_URL) links here from the Arcade panel with `?inst=<Band Ninja instrument>`; `instFromName` maps it (percussion → Mallets). Only the instrument is sent, never a name.

## Assessments (v1.3.0; v1.2.0 had only the Full Test)
- Mode cards 1–4 open openChooser(n): Practice (startMode) or Assessment (startTest(n)). TEST_PLANS: mode1 = 16 notes in 2 keys (perKey 8), mode2/3 = 2 lines, mode4 = 2 sets (16 each); 5 = Full Test (8 notes + 1 line + 1 line + 1 set = 32). Range locked to ledger1, one instrument.
- `?test=<20 hex>` from the Dojo → banner + score POSTed (text/plain JSON with kind mode1..mode4/full) to DOJO_URL (the Dojo /exec doPost, raven-hub-code dojo/src/MyProgress.js kstSave_). The id stays in the address; USED (this visit) marks kinds turned in. No id, or a kind already turned in = practice copy, nothing sent.

## Open items / ideas
- Optional strict-rule setting (no courtesy accidentals) if Mat wants to test the octave rule directly.
- Fingering answers; mic "play it" mode tie-in with Band Arcade.
- Narrow phones squeeze the 2-measure line; Chromebooks/viewboard are fine.
- Score reporting (Band Ninja / Brightspace) if he wants grading later.
