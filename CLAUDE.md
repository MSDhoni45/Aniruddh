# Influnexus — AI & Tech Creator Intelligence OS

This repository's working project is `influnexus-creator-os/`. It researches AI and technology stories, verifies them,
ranks them and writes ONE recording-ready English short-form script a day. It does **not** edit, render, generate or publish
video, download video libraries, or touch the separate video-editing project. Never create a second scheduled task: the
daily automation already exists ("Influnexus daily brief", 08:41 IST).

Setup in a fresh container: `cd influnexus-creator-os && pip install -q -e . && git pull --ff-only`.
Dates are Asia/Kolkata (IST). `creatoros` commands run from `influnexus-creator-os/`.

## Commands the creator types

| They type | Do this |
|---|---|
| **Script for today** | If `daily/TODAY/today.md` exists and says RECORDING READY: re-check any time-sensitive claim (prices, "no confirmed attacks", "first", etc.), then return the contents of `creatoros today`. Otherwise run the full daily workflow in `RUNBOOK.md`, then return `creatoros today`. |
| **Give me 5 topics** | `creatoros topics -n 5` for today. If today has no research yet, run RUNBOOK steps 1-2 first. Show only verified (eligible) topics. |
| **Different topic** | `creatoros switch`, then take the next eligible candidate from today's research, verify it to the same standard (RUNBOOK step 2), write a new `package.json`, run `creatoros package`, return `creatoros today`. Never reuse a held or rejected topic. |
| **Make it more viral** | Rewrite the hook, pacing and storytelling only. Every factual statement must still match a HIGH claim in the claim table. Re-run `creatoros package`; the hook must still win the hook scoring. |
| **Make it 30 seconds** | Cut to about 70-75 words, keep every attribution, re-run `creatoros package` (30 s is the floor). |
| **Make it more natural** | Simpler conversational English, shorter sentences, no new claims. Re-run `creatoros package`. |
| **Prepare for recording** | Return `creatoros recording` only: script and delivery notes. |

After any change, commit `daily/DATE/` and the `research/*.jsonl` databases and push to the working branch.

## Non-negotiables
- 100% natural conversational English for a global audience; the creator keeps their natural Indian accent.
- 30-40 seconds, about 75-90 words, a hook in the first two seconds. At least 10 hooks are scored; the best accurate one wins.
- Every central claim is verified from a primary source, with source URL, title, publication date and exact supporting evidence
  in the claim table. If a central claim cannot be verified, the package is HOLD — NOT RECORDING READY and another topic is chosen.
- Never invent quotes, benchmarks, specs, prices, dates, URLs, engagement numbers, creator rankings or analytics. Unobserved = UNKNOWN.
- If a source or platform cannot be opened, say so; never claim to have watched a video or opened a blocked page.
- Viral potential scores are editorial judgements, not view predictions. Never promise growth.
