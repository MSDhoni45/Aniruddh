# V7 migration (22 Nov 2026)

## Audit of v6 (what exists and works)
- **Scheduling:** one cloud scheduled task, "Influnexus daily brief", 08:41 IST, fires into a persistent session. It ran
  READY on 20, 21 and 22 Nov (start 08:41, end 08:46-08:48). Its stored prompt is older than v5; the run reads `CLAUDE.md`
  and `RUNBOOK.md`, which take precedence. Only the authorized session can edit the stored prompt (attempts from this session
  were refused). The approved text is `config/scheduled_task_prompt.md`.
- **Run flow:** `creatoros runlog start` (duplicate guard, source audit, 24 h window in UTC/IST, budgets) → ONE fresh subagent
  researches, verifies and writes `daily/DATE/package.json` → `creatoros package` (validator; renders today.md) →
  `creatoros growth` → push notification → `creatoros runlog end` (run_report.json) → one commit and push.
- **Research tools:** WebSearch (extended mode works for recent dates) and WebFetch. The source audit finds x.com, Reddit,
  YouTube, Instagram, Google Trends and most news sites BLOCKED; anthropic.com and github.com reachable. No X/Reddit/YouTube/
  Instagram API credentials. X signal is therefore PARTLY VERIFIED or NOT VERIFIED with UNKNOWN metrics.
- **Verification:** tiered, risk-based levels computed from evidence lists; extraordinary financial claims need the primary
  document opened; automatic HOLD and fallback (`creatoros hold`).
- **Story history:** `research/content_db.jsonl` (repeat detection, `material_update_of`), `research/topics_db.jsonl`,
  memory records.
- **Delivery:** push notification (recorded as "requested"; no receipt available) plus the run's reply; stages via
  `creatoros runlog stages`.
- **Analytics:** none connected. `analytics/performance.csv` and `analytics/followers.csv` hold only creator-entered numbers
  (both empty so far).
- **Known failures:** 20 Nov hook relied on search excerpts for an IPO price (held, replaced); 19 Nov GTA VI script rejected
  by the creator; v6 trial picked an obscure (if verified-looking) mathematics story with snippet-only endorsement.

## What V7 changes (built on top; nothing removed)
| Area | V7 change | Where |
|---|---|---|
| Scoring | V7 virality model; verification as an eligibility gate | `research/candidates.py` (WEIGHTS_V7, validate_v7) |
| Claims | COMPANY-CLAIMED, INDEPENDENTLY REPORTED, PRELIMINARY | `factcheck/claims.py` |
| Extraordinary claims | auto-detected; primary + independent confirmation opened; scrutiny record | `factcheck/evidence.py`, `scripts/package.py` |
| Script | 30-40 s, 70-90 words, natural pace; 5+ hooks on six criteria; ten script checks | `scripts/lint.py`, `config/settings.yaml` |
| Brief | seven sections, no editing plan | `scripts/package.py` (render_today_v7) |
| History | story_id, company, event_date, selected date | `scripts/package.py` → `content_db` |
| Growth | 100K in 60 days from 22 Nov; weekly checkpoints | `analytics/growth.py`, settings |
| Learning | script-length bands and posting hour | `analytics/learning.py` |
| Dates | V7 accepted 22 Nov, required 23 Nov; older packages keep their rules | `scripts/package.py` |

## Not possible from this environment (blockers)
- Observed X metrics (x.com blocked; no API key). Instagram analytics (no authorized connection).
- Editing the scheduled task's stored prompt (only the authorized session may).
- Push-notification receipts (the tool returns "requested" only).
