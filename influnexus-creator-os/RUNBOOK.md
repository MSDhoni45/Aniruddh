# Daily runbook: research → viral topic → recording package

Run by the scheduled task "Influnexus daily brief" at 08:41 Asia/Kolkata so the package is ready by 09:30 IST.
`DATE` is today's date in IST. This project stops at a recording-ready script. It does not edit, render or publish video.

## 0. Setup (the container may be fresh)
```
cd influnexus-creator-os && git pull --ff-only && pip install -q -e .
```

## 1. Research (aim to finish by 09:10 IST)
- Search the last 24 hours across all six categories in `README.md`; include 24-72 hour stories only when interest is growing (label them EMERGING).
- Send searches in parallel. Use social platforms to find discussion and authoritative sources to verify it.
- Record the original announcement date, not the date of a repost.
- Look for 15 credible candidates. Do not pad: weak items go in with `evidence_confidence: "LOW"`; claims that fail verification go in with `rejected`. If fewer than 15 reach MEDIUM or HIGH, say why in `candidate_shortfall_reason`.
- Every field in `creatoros.research.candidates.REQUIRED`. Unobserved metrics are `"UNKNOWN"`; traction above 5 needs `traction_evidence`.
- Check repeats: `creatoros content-search "<words>"`. A covered topic only returns with `material_update_of` naming the new development.
- Stories whose key facts will change before recording (e.g. an IPO not yet priced) get `hold_reason`.

## 2. Verify the leading story
- List every material claim with a status: CONFIRMED, COMPANY CLAIM, THIRD-PARTY CLAIM, DISPUTED, UNVERIFIED, SPECULATION.
- Security: advisory, CVE, versions, patch, prerequisites, exploitation, reproduction, severity disputes. AI products: real availability, regions, pricing, limits. Science: paper, peer review, replication.
- Attributed claims in the script must carry their attribution in the spoken words; record those exact words as `script_attribution`.
- If a key claim cannot be verified or attributed, take the next candidate.
- Name every source you could not open.

## 3. Write
- Read `research/creator_style_guide.md` and `research/hook_patterns.md`.
- At least 10 hooks across at least 5 mechanisms, each scored 0-10 on accuracy, clarity, curiosity, natural delivery, relevance and immediate comprehension. Accuracy under 7 disqualifies. Open the script with the top hook.
- One script, natural Hinglish, 75-90 words, 30-40 seconds (40 is a hard limit).
- Score the ten quality checks honestly; below 90, or any check below 7, means rewrite. Duration is measured by the tool.

## 4. Build
Write `daily/DATE/package.json` (same shape as `daily/2026-11-18/package.json`), then:
```
creatoros package --date DATE
```
It refuses to render if any rule fails and logs the topic to `research/content_db.jsonl` when it passes. Fix problems; never bypass the validator.

## 5. Deliver
- Commit `daily/DATE/` and `research/content_db.jsonl`; push to the working branch.
- Send one push notification with the topic and `daily/DATE/package.md`. Report delivery only as the tool reports it.
- Reply with the package so it can be recorded from the message.
- Do not publish anything anywhere.

## 6. Learning (when the creator supplies numbers)
- `creatoros metrics-add ...` at 24 h, 72 h and 7 days; `creatoros content-update --date D --slug S status=published platforms=instagram,x`.
- Never invent numbers. One video is an anecdote.

## Weekly (Mondays)
- `creatoros weekly --end DATE`, then add a short "Recommendations" section to `reports/weekly/DATE.md`, citing the data above it.
- Refresh `research/creator_benchmarks.md` and `research/creator_video_samples.csv` (competitor database). Keep MEASURED, THIRD-PARTY and HYPOTHESIS labels; don't claim to have watched videos you could not open.
