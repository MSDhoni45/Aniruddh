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
| **TODAY'S REEL SCRIPT** | Same as "Script for today" below, delivered in the v6 format (`today.md`: story, why selected, verified facts and sources, script, duration, opening visual, caption, hashtags). Do not ask the creator to pick a topic. |
| **REEL SCRIPT: [TOPIC]** | Research that exact topic (why now, what happened, what people discuss, what is surprising, what viewers may misunderstand, why share), verify it to RUNBOOK step 2, `creatoros switch` if today already has a package, write a v6 package (from 2026-11-23; v5 before), `creatoros package`, return `creatoros today`. Gaming: label the release type (original release, re-release, remaster, remake, mod, rumour, official announcement, launch). |
| **IMPROVE THIS SCRIPT: [SCRIPT]** | Critique and rewrite the opening, pacing, clarity, storytelling, retention and ending; keep every fact; return one improved script with the six-part quality score. If it is today's package, re-run `creatoros package`. |
| **Script for today** | First run `creatoros runlog status`; if `problem` is true, open the reply with one line saying the 08:41 scheduled run was MISSED/FAILED/LATE/HOLD. Then: if `daily/TODAY/today.md` exists and says RECORDING READY: re-check any time-sensitive claim (prices, "no confirmed attacks", "first", etc.), then return the contents of `creatoros today`. Otherwise run the full daily workflow in `RUNBOOK.md`, then return `creatoros today`. |
| **Give me 5 topics** | `creatoros topics -n 5` for today. If today has no research yet, run RUNBOOK steps 1-2 first. Show only verified (eligible) topics. |
| **Different topic / DIFFERENT TOPIC** | `creatoros switch`, then take the next eligible candidate from today's research, verify it to the same standard (RUNBOOK step 2), write a new `package.json`, run `creatoros package`, return `creatoros today`. Never reuse a held or rejected topic. |
| **Make it more viral** | Rewrite the hook, pacing and storytelling only. Every factual statement must still match a HIGH claim in the claim table. Re-run `creatoros package`; the hook must still win the hook scoring. |
| **Make it 30 seconds** | Cut to about 70-75 words, keep every attribution, re-run `creatoros package` (30 s is the floor; the validator warns that it is under the 40-45 s target). |
| **Make it more natural** | Simpler conversational English, shorter sentences, no new claims. Re-run `creatoros package`. |
| **Prepare for recording** | Return `creatoros recording` only: script and delivery notes. |
| **Growth dashboard** | `creatoros growth`; show it as is (UNKNOWN stays UNKNOWN). |
| **My followers are N on PLATFORM** | `creatoros followers-add --date TODAY --platform P --followers N --source "creator, <where>"`, then `creatoros growth`. |
| **Here are my numbers for VIDEO** | `creatoros metrics-add ...` with only the numbers given (checkpoint 2h/24h/48h/7d), then `creatoros growth`. |

After any change, commit `daily/DATE/`, the `research/*.jsonl` databases and `logs/runs.jsonl` and push to the production branch.

## Non-negotiables
- LANGUAGE (creator's instruction, repeated 21 Nov 2026): every script and all platform copy are in 100% natural conversational
  English for a global audience (`config/settings.yaml` `language: english`). Hinglish only when the creator asks for it for a
  specific script. The creator keeps their natural Indian accent. The v6 rules below otherwise apply.
- v6 (from 2026-11-23; RUNBOOK "v6"): creator-led technology content, not a news summary. 15-25 candidates scored on the
  ten-part v6 rubric with a claim status (CONFIRMED, REPORTED, CLAIMED, SPECULATIVE, UNVERIFIED; only CONFIRMED or REPORTED
  stories win); five finalists with five hooks each (one per approach, no generic openings); three script variants
  (curiosity, practical, consequences), one chosen; a visual plan with no invented demos; duration estimated at a natural
  pace (140 wpm plus pauses); a nine-question creative quality gate; `creatoros learn` applied. `today.md` carries only the
  eight delivery items; hooks, variants and the gate stay in `creative.md`. Trial runs: `creatoros package --file ... --trial`.
- v5: 35-45 seconds (45 is the hard limit), about 85-105 words, a hook in the first 3 seconds. At least 5 hooks are scored
  internally; the best accurate one wins and only it is delivered. (v3/v4: 40-45 s, 90-105 words; before 20 Nov: 30-40 s, 75-90.)
- Research window: the 24 hours before the run starts (`creatoros runlog start` prints it); v5/v6 may widen to 48-72 hours only
  when no strong verified story exists in 24 hours (`window_expansion_reason`). Older stories need a dated new development.
- X/Twitter signal is evidence only when observed; when x.com cannot be opened it is labelled NOT VERIFIED or PARTLY VERIFIED and metrics are UNKNOWN.
- Verification (from 2026-11-21, tiered and risk-based; RUNBOOK "Verification policy"): each script claim has a risk and an
  evidence list; its risk is classified from the claim's temporal meaning (a declared risk can only raise it) and its level
  (HIGH, MEDIUM-HIGH, MEDIUM, LOW, UNVERIFIED) is computed from the sources. Time-sensitive claims
  (launches, prices, availability, security, finance, breaking news) need MEDIUM-HIGH plus a current report; historical claims need
  MEDIUM; time-sensitive extraordinary financial claims (share prices and moves, IPO pricing/proceeds, valuations, billions)
  need HIGH, i.e. the primary document opened directly. Copies of one report count once; search excerpts never make HIGH. A failing story is put on HOLD (`creatoros hold`) and
  the next-ranked one is tried. Older packages keep their original rule (every central claim HIGH with a primary source).
- Never invent quotes, benchmarks, specs, prices, dates, URLs, engagement numbers, creator rankings or analytics. Unobserved = UNKNOWN.
- If a source or platform cannot be opened, say so; never claim to have watched a video or opened a blocked page.
- Viral potential scores are editorial judgements, not view predictions. Never promise growth.
- Goal (from 22 Nov 2026): 150,000 Instagram followers in four months (120 days from 2026-11-22), one reel a day; an ambitious
  target, not a guarantee (it replaced 100,000 in 60 days). Instagram analytics are not connected: performance comes only from
  numbers the creator gives (`creatoros metrics-add`), and `creatoros learn` says so. Packages use the RUNBOOK's v6 rules from 2026-11-23. Never fabricate engagement, follower counts or analytics; label evidence
  DIRECTLY OBSERVED, SEARCH-INDEX, SECONDARY or NOT VERIFIED. Delivery is reported in stages (`creatoros runlog stages`):
  generated, saved, pushed, notification requested, accepted by the provider, received by the creator; accepted and received
  need evidence. Scheduled runs keep the main session thin and hand research to one fresh subagent (RUNBOOK "Cost control").
