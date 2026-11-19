# Influnexus — AI & Tech Creator Intelligence OS

This repository's working project is `influnexus-creator-os/`. It researches AI and technology stories, verifies them,
ranks them and writes ONE recording-ready English short-form script a day. It does **not** edit, render, generate or publish
video, download video libraries, or touch the separate video-editing project. Never create a second scheduled task: the
daily automation already exists ("Influnexus daily brief", 08:41 IST).

Setup in a fresh container (also when the session started on `main`): all daily packages, research databases and run logs
live on the production branch `claude/daily-ai-tech-research-script-taab6w`, so work there:
```
git fetch origin claude/daily-ai-tech-research-script-taab6w
git checkout -B claude/daily-ai-tech-research-script-taab6w origin/claude/daily-ai-tech-research-script-taab6w
cd influnexus-creator-os && pip install -q -e .
```
Push with `git push -u origin claude/daily-ai-tech-research-script-taab6w` (pull with `--rebase` first; another session may have pushed).
`main` carries the code and these instructions; it is updated by pull request, never pushed to directly.
Dates are Asia/Kolkata (IST). `creatoros` commands run from `influnexus-creator-os/`.

The approved text of the scheduled task's prompt is `influnexus-creator-os/config/scheduled_task_prompt.md`. If the stored prompt predates the 20 Nov 2026 rules (v2 scoring, 15 candidates, 30-40 s and
75-90 words). Where it differs from `influnexus-creator-os/RUNBOOK.md`, the RUNBOOK wins; the validator rejects non-v3 packages
from 2026-11-20. Always pass the `run_id` from `creatoros runlog start` to `creatoros runlog end`.

## Commands the creator types

| They type | Do this |
|---|---|
| **Script for today** | First run `creatoros runlog status`; if `problem` is true, open the reply with one line saying the 08:41 scheduled run was MISSED/FAILED/LATE/HOLD. Then: if `daily/TODAY/today.md` exists and says RECORDING READY: re-check any time-sensitive claim (prices, "no confirmed attacks", "first", etc.), then return the contents of `creatoros today`. Otherwise run the full daily workflow in `RUNBOOK.md`, then return `creatoros today`. |
| **Give me 5 topics** | `creatoros topics -n 5` for today. If today has no research yet, run RUNBOOK steps 1-2 first. Show only verified (eligible) topics. |
| **Different topic** | `creatoros switch`, then take the next eligible candidate from today's research, verify it to the same standard (RUNBOOK step 2), write a new `package.json`, run `creatoros package`, return `creatoros today`. Never reuse a held or rejected topic. |
| **Make it more viral** | Rewrite the hook, pacing and storytelling only. Every factual statement must still match a HIGH claim in the claim table. Re-run `creatoros package`; the hook must still win the hook scoring. |
| **Make it 30 seconds** | Cut to about 70-75 words, keep every attribution, re-run `creatoros package` (30 s is the floor; the validator warns that it is under the 40-45 s target). |
| **Make it more natural** | Simpler conversational English, shorter sentences, no new claims. Re-run `creatoros package`. |
| **Prepare for recording** | Return `creatoros recording` only: script and delivery notes. |
| **Growth dashboard** | `creatoros growth`; show it as is (UNKNOWN stays UNKNOWN). |
| **My followers are N on PLATFORM** | `creatoros followers-add --date TODAY --platform P --followers N --source "creator, <where>"`, then `creatoros growth`. |
| **Here are my numbers for VIDEO** | `creatoros metrics-add ...` with only the numbers given (checkpoint 2h/24h/48h/7d), then `creatoros growth`. |

After any change, commit `daily/DATE/`, the `research/*.jsonl` databases and `logs/runs.jsonl` and push to the production branch.

## Non-negotiables
- 100% natural conversational English for a global audience; the creator keeps their natural Indian accent.
- 40-45 seconds (45 is the hard limit), about 90-105 words, a hook in the first 1-2 seconds. At least 10 hooks are scored; the best accurate one wins.
  (Packages before 20 Nov 2026 used 30-40 s / 75-90 words and keep those limits.)
- Research window: the 24 hours before the run starts (`creatoros runlog start` prints it). Older stories need a dated new development inside it.
- X/Twitter signal is evidence only when observed; when x.com cannot be opened it is labelled NOT VERIFIED or PARTLY VERIFIED and metrics are UNKNOWN.
- Every central claim is verified from a primary source, with source URL, title, publication date and exact supporting evidence
  in the claim table. If a central claim cannot be verified, the package is HOLD — NOT RECORDING READY and another topic is chosen.
- Never invent quotes, benchmarks, specs, prices, dates, URLs, engagement numbers, creator rankings or analytics. Unobserved = UNKNOWN.
- If a source or platform cannot be opened, say so; never claim to have watched a video or opened a blocked page.
- Viral potential scores are editorial judgements, not view predictions. Never promise growth.
- Goal: 100,000 Instagram followers in 60 days from 2026-11-20, one reel a day (an ambitious target, not a guarantee). Packages
  use the RUNBOOK's v4 rubric from 2026-11-21. Never fabricate engagement, follower counts or analytics; label evidence
  DIRECTLY OBSERVED, SEARCH-INDEX, SECONDARY or NOT VERIFIED. A notification the service accepted is "requested", not delivered.
