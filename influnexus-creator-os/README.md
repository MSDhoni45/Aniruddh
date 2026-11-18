# Influnexus Creator OS

Daily research → one viral-worthy topic → one recording-ready English script for a global audience, with English captions and platform copy.
The default language is set in `config/settings.yaml` (`language: english`).
Follower targets are stretch goals, not promises; nothing here manufactures engagement or guarantees reach.

## Scope
**In scope:** research, trend detection, verification, topic scoring, hooks, scripts, platform captions, content memory, analytics review.
**Out of scope:** editing, rendering, footage processing and publishing. The modules under `src/creatoros/{editing,audio,graphics,rendering,subtitles,qc,publishing}`
and `tools/make_test_footage.py` were built earlier and are not part of the daily workflow. They can be moved to their own repository.

## Daily loop
Type **"Script for today"** in a Claude Code session on this repository (the repository's `CLAUDE.md` defines it and the other
commands: "Give me 5 topics", "Different topic", "Make it more viral", "Make it 30 seconds", "Make it more natural", "Prepare for recording").

1. **08:41 IST** the scheduled Claude session follows `RUNBOOK.md`. The deliverable lands in `daily/DATE/today.md` by 09:30
   (full research in `package.md`, script-only view in `recording.md`, caption text in `captions.txt`).
2. Read section C once, record in your natural voice. `captions.txt` has the on-screen caption text.
3. When numbers exist, log them (`creatoros metrics-add`, `creatoros content-update`). Mondays: `creatoros weekly`.

## Setup
```
pip install -e ".[dev]"
python -m pytest tests/test_units.py tests/test_research.py   # 45 fast tests; no models needed
```
The research workflow needs only Python. The out-of-scope editing tests additionally need FFmpeg and `tools/setup_models.sh`.

## Commands
| Command | Does |
|---|---|
| `creatoros package --date DATE` | validates `daily/DATE/package.json`, renders `package.md`, `today.md`, `recording.md`, `captions.txt`, logs topics and claims |
| `creatoros today` / `recording` | today's deliverable / script and delivery notes only |
| `creatoros topics -n 5` | strongest eligible topics, verified first, with verification status |
| `creatoros switch` | archive today's package before writing a different topic |
| `creatoros runlog start\|end` | append to `logs/runs.jsonl`, the proof that a run executed |
| `creatoros script-check FILE` | word count, estimated duration, banned openings, generic phrases |
| `creatoros factcheck FILE --script FILE` | rejects unverified or unattributed claims |
| `creatoros score FILE` | viral potential score and eligibility for candidate topics |
| `creatoros content-search [QUERY] [--status S] [--category C]` | search the content database |
| `creatoros content-update --date D --slug S key=value ...` | status, platforms, audience response, lessons |
| `creatoros weekly --end DATE` | weekly review data in `reports/weekly/` |
| `creatoros calibrate --date DATE` | (needs an edit) measured speaking pace |
| `creatoros metrics-add k=v ...` / `metrics-report` / `metrics-review` | analytics |

## Rules the validator enforces
- Script and all platform copy must be English (Devanagari or Hindi words in Latin script fail), with no forced slang, corporate jargon
  or clickbait phrasing; the X post must fit 280 characters.
- Every package carries a claim verification table (exact claim, primary source, supporting source, status, source date, confidence, access).
- RECORDING READY only when every central script claim is HIGH with a primary source, no quote has unverified wording and nothing is unresolved;
  otherwise HOLD — NOT RECORDING READY. Secondary repetition alone is never HIGH.
- Scoring v2 (from 19 Nov 2026): curiosity 20, storytelling 20, shareability 15, global relevance 15, freshness or evergreen 10,
  visual 10, originality 10. Editorial scores, not view predictions. Older packages keep the v1 weights.
- v2 packages need visual suggestions for the editor, and every script claim needs its source title and the exact supporting evidence.
- Hooks may not repeat a hook already used for another topic.
- Topic must be the highest-scoring eligible candidate. LOW-confidence, low-credibility, on-hold, rejected or already-covered stories cannot win.
- 15 credible candidates, or a written reason for fewer. Unknown metrics score zero; traction above 5 needs observed evidence.
- At least 10 hooks over 5+ mechanisms; accuracy under 7 disqualifies; the script must open with the top hook.
- Script: 30-40 s (40 hard), no banned openings or generic phrases, every attributed claim attributed in the spoken words, no UNVERIFIED or SPECULATION claims.
- Script quality 90/100 or more, no check under 7; duration is measured, not self-scored.
- Research summary 100-150 words; 3-5 Instagram hashtags; every source has a URL.
- A topic already in `research/content_db.jsonl` needs `material_update_of`.

## Verified state (19 November 2026, 01:30 IST)
| Component | State | Evidence |
|---|---|---|
| Current-information retrieval | WORKING | web search returned items dated 16-18 Nov 2026 across all categories |
| Social discovery | PARTIALLY WORKING | X posts are found through search results only; X, Instagram, YouTube, Reddit and LinkedIn cannot be opened; engagement is UNKNOWN |
| Source verification | PARTIALLY WORKING | primary sites cannot be opened from the cloud environment; their own indexed text is read through domain-restricted search and labelled `search-index`. 18 Nov California story held because its case number, exact allegation wording and OpenAI statement could not be verified |
| Topic ranking | WORKING | 21 candidates scored on the v2 criteria in `daily/2026-11-19/package.md`; tests cover eligibility rules |
| Script generation and QA | WORKING | 19 Nov: 89-word English script on a Nature Medicine brain-implant study, RECORDING READY; 69 fast tests |
| Duplicate prevention and memory | WORKING | content database blocks repeated topics and hooks; `research/topics_db.jsonl` and `claims_db.jsonl` keep every researched topic (incl. rejected) and claim |
| Daily scheduling | CONFIGURED, NOT YET PROVEN | one task, "Influnexus daily brief", 08:41 IST; no run on record yet. Each run writes `logs/runs.jsonl`; a 09:40 IST check on 19 Nov will verify the first run |
| Notification | PARTIALLY WORKING | push notification is requested at the end of each run; phone delivery cannot be confirmed from here |
| Competitor intelligence | PARTIALLY WORKING | `research/creators_db.csv` (58 verified creators, 3 partial; every account URL seen in search results) and `research/creator_benchmarks.md`; no creator video can be watched from here, so delivery and editing analysis is NOT OBSERVED |
| Performance learning | WORKING, no data yet | analytics store (now incl. viewed-vs-swiped rate and audience geography), ratios and weekly review are tested; nothing published |
| Speaking pace | ASSUMED | 150 words per minute until a recording is measured |

## Layout
`config/` settings · `research/` benchmarks, style guide, hook patterns, content database · `daily/DATE/` package, script, fact-check, sources · `reports/weekly/` · `analytics/` · `src/creatoros/` code · `tests/`. Editing-related folders (`footage/`, `assets/`, `final/`, `renders/`, `subtitles/`) are out of scope.
