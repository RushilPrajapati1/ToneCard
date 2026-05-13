# Product

## Register

product

## Users

Music nerds seeking discovery. Someone who already knows roughly how they feel, but wants to find tracks they haven't heard before. They open Tonecard to explore — click around the mood plane, see what surfaces, follow something interesting. Low friction on arrival; depth is the reward for staying.

## Product Purpose

Tonecard is a public mood-discovery tool built on the Spotify Web API and ReccoBeats. The core surface is an interactive valence × energy plane: every point is a feeling, every click is a recommendation. No login, no library, no playlists — just the plane and the tracks it reveals. Success is a user finding something they didn't know they wanted to hear.

## Brand Personality

Warm, personal, curatorial. Like a recommendation from a friend who has exceptional taste and can explain exactly why this track fits right now. Not clinical, not algorithmic-feeling. The mood plane should feel like it was designed by someone who cares deeply about music, not a data scientist.

Three words: **attuned, confident, unhurried**.

References: Pitch (editorial music intelligence, strong typographic voice) and Letterboxd (taste as identity, personal discovery at the center, community curation without noise).

## Anti-references

Tonecard should not look or feel like a data dashboard — no chart-heavy layouts, no obsessive metric labels, no analytics-tool energy. The valence and energy numbers are means to an end (finding the right track), not the product. Avoid anything that makes the mood plane feel like a scatter plot.

## Design Principles

1. **Taste over metrics.** Show tracks with editorial confidence. The mood plane surfaces recommendations, not a spreadsheet. Numbers (valence, energy) serve orientation, not decoration.
2. **The plane is the product.** The interactive SVG plane is the primary affordance. It should feel inviting and spatial, not technical — something you want to explore, not operate.
3. **Feel-forward.** Every interface decision should reinforce the emotional register — mood, vibe, feel. Abstract features belong in the background; the listening experience belongs in front.
4. **Earned restraint.** Spare because the music is the content, not because minimalism is safe. No decoration that competes with the tracks themselves.
5. **Warm, not cute.** Warmth through typography quality and curation confidence, not rounded corners and pastel fills.

## Accessibility & Inclusion

WCAG AAA. Full keyboard navigation, high-contrast ratios at all text sizes, no motion-only affordances (the mood plane must be operable without pointer precision), screen reader support for track list and controls. Reduced-motion preference respected — plane interactions and any transitions should degrade gracefully under `prefers-reduced-motion`.
