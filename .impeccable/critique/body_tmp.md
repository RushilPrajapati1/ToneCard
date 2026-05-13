## Tonecard / `static/index.html` — Design Critique

### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Good skeleton on results; plane loads empty with no feedback on cold open |
| 2 | Match System / Real World | 3 | Axis labels translate well; raw `valence 0.41` numbers in features row expose the model seams |
| 3 | User Control and Freedom | 2 | No way to clear a pick or undo; genre switch silently destroys current results |
| 4 | Consistency and Standards | 4 | Token system applied rigorously throughout; hover states uniform |
| 5 | Error Prevention | 2 | No warning before genre switch clears results; corner clicks yield sparse results with no guidance |
| 6 | Recognition Rather Than Recall | 3 | Presets reduce recall burden; `dance`, `acoustic` feature abbreviations require domain knowledge |
| 7 | Flexibility and Efficiency | 2 | Presets help novices; no keyboard access, no coordinate input, no power-user path |
| 8 | Aesthetic and Minimalist Design | 4 | Clean, purposeful, nothing competes with the plane |
| 9 | Error Recovery | 2 | Raw `err.message` surfaced verbatim; no retry action; error is a dead end |
| 10 | Help and Documentation | 1 | Lede is the entire onboarding; no tooltips, no axis legend, no feature label glossary |
| **Total** | | **26/40** | **Acceptable — significant improvements needed** |

### Anti-Patterns Verdict

Mostly passes the AI slop test. Color system (OKLCH warm paper tones, terracotta accent) and spatial plane interface are distinctive. No gradient text, glassmorphism, hero metric cards, or side-stripe accents.

Detector flagged Geist (overused-font, 3 instances — lines 10, 65, 147). The LLM missed this; detector is correct. Geist is a strong AI-generation signal in 2025-26.

### Priority Issues

**[P0] Keyboard/screen reader access to the mood plane is absent.**
SVG has no tabIndex, no keyboard handlers, no focus indicator. Hard WCAG 2.1.1 failure. WCAG AAA is the stated target.
Fix: tabIndex=0 + arrow key virtual cursor + aria-live coordinate announcements + Enter/Space to pick.

**[P1] Seed pool cold load has no initial feedback.**
seedLoading initializes false; plane renders empty until useEffect fires loadSeed. First impression is a blank/broken plane.
Fix: Initialize seedLoading: true.

**[P1] Error messages are raw developer strings.**
setError(err.message) surfaces HTTP 429, spotipy exceptions verbatim. No retry action. Dead end.
Fix: Map status codes to plain language + add retry button.

**[P1] Demo mode activates silently with misleading results.**
Banner ("demo data - backend unreachable") is easy to miss. Demo tracks have href="#" Open links. Users get confused.
Fix: Prominent banner, disabled Open links in demo mode, neutral demo data.

**[P2] Empty state is a passive dead end.**
"No tracks found near that point. Try clicking somewhere else, or pick a preset." — no inline affordances.
Fix: Render 2-3 preset buttons inline in the empty state.

### Persona Red Flags

**Sam (Accessibility):** SVG plane is skip-invisible to keyboard; no aria-live on results or errors. Cannot use the primary feature.

**Alex (Power User / Crate Digger):** No keyboard plane navigation. No coordinate input. No comparison between two picks. Genre list unsorted with no search.

**Riley (Stress Tester):** Genre switch silently destroys results without warning. Page refresh loses all state. Demo "Open" links go to href="#" silently.

### Minor Observations

- Brand mark CSS bars read as a bar chart (the data-dashboard anti-reference)
- Hyphen-minus used as separator in lede and coordinate display
- Inline styles in JSX break the otherwise-clean CSS class system
- Fractional font sizes (15.5px, 12.5px) suggest manual tweaking over a harmonic scale
- Footer "open mood discovery" — ambiguous
- Track album opacity: 0.5 inline instead of var(--muted)
- No OG/meta tags — blank social cards on share
- Geist swap would close the one detector flag
