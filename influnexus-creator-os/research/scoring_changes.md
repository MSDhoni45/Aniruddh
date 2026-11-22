# Scoring changes

Every change to the editorial scoring weights, with the reason and the evidence. Weights change only when several reels'
real numbers support it; one reel is an anecdote.

| Date | Scheme | Change | Reason | Evidence |
|---|---|---|---|---|
| 2026-11-19 | v2 | curiosity 20, storytelling 20, shareability 15, global relevance 15, freshness 10, visual 10, originality 10 | Initial editorial rubric | None (no published reels) |
| 2026-11-19 | v3 (from 2026-11-20) | public discussion 20, surprise 15, significance 15, usefulness 15, visual 10, broad appeal 10, discussion 5, longevity 5, verification confidence 5 | Creator's specification | None (no published reels) |
| 2026-11-19 | v4 (from 2026-11-21) | social traction 20, novelty 15, consequence 15, broad appeal 15, visual 10, discussion 10, verified significance 10, freshness 5. Creative rubric: hook 20, clarity 15, human delivery 15, relevance 15, information 15, retention 10, discussion 10 | Creator's Instagram growth specification | None (no published reels). Social traction is provisional until engagement is observed. |
| 2026-11-19 | v5 (from 2026-11-21) | Story rubric back to the v3 weights (public discussion 20, surprise 15, significance 15, usefulness 15, visual 10, broad appeal 10, conversation 5, longevity 5, verification 5). Quality score: hook 20, clarity 15, storytelling 20, retention 15, shareability 15, factual confidence 15 (weights assumed by the system: the creator listed the criteria without weights). Language: Hinglish. | Creator's Master Prompt V5 | None (no published reels) |
| 2026-11-19 | verification policy (from 2026-11-21) | Tiered, risk-based evidence levels (HIGH, MEDIUM-HIGH, MEDIUM, LOW, UNVERIFIED) computed from each claim's sources; high-risk claims need MEDIUM-HIGH plus a report within 7 days, low-risk claims MEDIUM; automatic HOLD-and-fallback | Creator's permanent verification policy | GTA VI launch package held on 19 Nov (search excerpts only for time-sensitive facts) |

## 2026-11-22: v6 (creator-led editorial quality; required from 2026-11-23)
Why: the creator judged the daily scripts technically valid but news-like, not creator-led content that earns shares, saves,
comments and follows. Goal changed to 150,000 Instagram followers in four months (from 22 Nov 2026; a target, not a guarantee).
- Candidate rubric v6 (0-10 each, weights): curiosity 12, surprise 12, broad relevance 12, shareability 12, save potential 10,
  comment potential 10, visual storytelling 10, practical usefulness 8, long-term relevance 6, factual confidence 8.
  Editorial estimates, not predictions. Claim status per story; only CONFIRMED or REPORTED stories are selectable; factual
  confidence 8+ needs CONFIRMED, under 6 is ineligible. Claim tables gain CLAIMED (attribution required).
- 15-25 candidates (fewer only with a reason); five finalists = top five eligible; five hooks each, one per approach (surprising
  fact, unexpected consequence, direct relevance, contrarian question, visual demonstration), at most 14 words, generic openings
  banned; the chosen hook is the winner's top accurate hook.
- Three variants (A curiosity, B practical, C consequences), one selected word for word; visual plan (no invented demos);
  nine-question creative gate; duration estimated at 140 wpm plus 0.35 s per sentence break (no cramming: about 85-95 words);
  sentences at most 22 words; caption at most 60 words.
- Delivery trimmed to eight items; finalists, hooks, variants and the gate go to creative.md and research.json.
- `creatoros learn`: account-median comparisons by hook type, topic, pillar and format, three reels minimum per group;
  reports that Instagram analytics are not connected. No data yet, so the rubric weights are unchanged by data.
