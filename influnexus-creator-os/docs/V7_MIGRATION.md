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

## Blockers and the exact action each needs (checked 22 Nov 2026, 19:50 IST)
| Blocker | Evidence | Action only the creator can take |
|---|---|---|
| Primary and independent sources cannot be opened | curl through the agent proxy: only www.anthropic.com (200) and github.com answer; x.com, tesla.com, electrek.co, reuters.com, apnews.com, techcrunch.com, theverge.com, openai.com, blog.google, apple.com, microsoft, nvidia, huggingface.co, arxiv.org, sec.gov, nhtsa.gov and the rest fail (DNS refused by the network policy); WebFetch fails the same way | In the cloud environment's settings (session title bar, environment menu, Edit, Network access): choose a broader access level, or add the domains below under Allowed domains, keeping "Allow package managers" ticked. Docs: https://code.claude.com/docs/en/cloud-environments#network-access |
| Scheduled task still has the pre-v3 prompt | `get_trigger`: prompt is the 18 Nov v2 text; `update_trigger` from this session was refused by the auto-mode permission check ("Undermining Oversight") | Open the "Daily AI/tech research and script" session (the one the task fires into) and ask it to set the prompt to `config/scheduled_task_prompt.md`, or edit the task in claude.ai, or allow `mcp__claude-code-remote__update_trigger` in permissions. The run already follows CLAUDE.md and the RUNBOOK, which take precedence. |
| X engagement data | No X connector in the org or registry; api.x.com blocked; no API credentials | An X developer account with API read access (a paid plan; needs your approval), its bearer token stored as an environment secret, and api.x.com allowed in the network settings |
| Instagram followers and insights | No Instagram/Meta connector in the org or registry search; graph.instagram.com / graph.facebook.com blocked | A professional (Business or Creator) Instagram account linked to a Facebook Page, a Meta app with Instagram insights permissions and its access token as an environment secret, plus graph.facebook.com allowed; or tell me the numbers ("My followers are N on Instagram") |
| Notification receipt | PushNotification returns "Mobile push requested" only | Confirm on your phone that it arrived; I record it with `creatoros runlog delivery --delivery received --receipt "creator confirmed ..."` |

Suggested Allowed domains (research quality): x.com, api.x.com, tesla.com, openai.com, blog.google, deepmind.google, ai.meta.com,
about.fb.com, blogs.microsoft.com, news.microsoft.com, nvidianews.nvidia.com, blogs.nvidia.com, apple.com, aboutamazon.com,
aws.amazon.com, x.ai, mistral.ai, huggingface.co, arxiv.org, nature.com, science.org, sec.gov, nhtsa.gov, reuters.com,
apnews.com, bbc.com, cnbc.com, theverge.com, techcrunch.com, arstechnica.com, wired.com, engadget.com, electrek.co,
9to5mac.com, 9to5google.com, androidauthority.com, macrumors.com, theregister.com, bleepingcomputer.com, securityweek.com,
thehackernews.com, technologyreview.com, spectrum.ieee.org, openrouter.ai.
