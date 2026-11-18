# Daily runbook (for the scheduled Claude session)

Runs every day at about 09:09 Asia/Kolkata so the brief is ready by 09:30. `DATE` is today's date in IST.

## 0. Setup (the container may be new)
```
cd influnexus-creator-os && pip install -q -e . && git pull --ff-only
```
Speech models are only needed for editing: `tools/setup_models.sh`.

## 1. Research the last 24 hours
- Search for public X conversations and news on the monitored list in `README.md`. Send searches in parallel.
- Aim for at least 10 candidates when reliable material exists. Fewer is acceptable; say so.
- For each candidate fill every field in `creatoros.research.candidates.REQUIRED`. Anything not observed is `"UNKNOWN"`.
  Never infer likes, reposts or views from snippets. Reposts of one claim are one source, not several.
- Run `creatoros story-check "<headline>" --keys <ids> --date DATE` and set `already_covered` accordingly.
- Stories first published before the 24-hour window get `"outside_window": true` unless there is a material new development.

## 2. Fact-check the leading story
- List every material claim in `factcheck.claims` with a status from `creatoros.factcheck.claims.STATUSES`.
- Cybersecurity: vendor advisory, CVE, affected versions, patch, prerequisites, exploitation, reproduction, severity disputes.
- AI products: official release, real availability, regions, pricing, limits. Science: paper, peer review, replication.
- If a major claim cannot be verified or attributed, drop the story and take the next candidate.
- Say which sources could not be opened from this environment.

## 3. Write the script
- Natural Hinglish, 75-90 words, 32-38 seconds, 40 hard maximum. Structure: hook, development, evidence, why care, takeaway.
- Draft three hooks, score them (`hooks` in the brief data), use the winner. Read `research/creator_style_guide.md` and `research/hook_patterns.md`.
- Attributed claims need the attribution in the spoken words; record the exact phrase as `script_attribution`.

## 4. Build and validate
Write `daily/DATE/brief.json` (same shape as `daily/2026-11-18/brief.json`) and `scripts/DATE_edit_plan.json`, then:
```
creatoros brief --date DATE          # refuses to render if anything fails validation
creatoros story-add "<headline>" --keys <ids> --date DATE --slug <slug>
```
Fix every reported problem; never bypass the validator.

## 5. Deliver
- Commit `daily/DATE`, `scripts/DATE_*` and `research/story_log.jsonl`; push to the working branch.
- Send a push notification with the story headline and the brief path. Report delivery only if the send call confirms it.
- Reply in the session with the brief, concise enough to record from.

## 6. Analytics (when videos have been published)
- `creatoros metrics-add ...` for each checkpoint that is due (24h, 72h, 7d). Only enter numbers the creator or an API supplied.
- After every 10 videos with 7-day data: `creatoros metrics-review`, then update the style guide from the evidence.

## Weekly (Mondays)
Refresh `research/creator_benchmarks.md` and `research/creator_video_samples.csv`. Keep MEASURED, THIRD-PARTY and HYPOTHESIS labels.
