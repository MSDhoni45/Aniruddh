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

## 2. Verify the leading story (permanent rule: claim verification table)
- Every factual claim goes in `factcheck.claims` with: `text` (exact claim), `primary_source` (URL or null), `supporting_source`
  (an independent URL or null), `status`, `source_date`, `confidence` (HIGH/MEDIUM/LOW), `access`, `in_script`.
  - `access`: `opened` (page read), `search-index` (the primary site's own indexed text, read through search, page not opened),
    `secondary-only`, or `not found`. Say which, honestly.
  - HIGH needs a primary source reached as `opened` or `search-index` plus an independent supporting source.
    Several secondary outlets repeating one claim is MEDIUM at most.
  - Quotations need `quote: true`; they stay below HIGH until `wording_verified: true` against the primary source.
  - Background details that do not carry the story may be marked `central: false`.
- Statuses: CONFIRMED, COMPANY CLAIM, THIRD-PARTY CLAIM, DISPUTED, UNVERIFIED, SPECULATION. Attributed claims carry their attribution
  in the spoken words; record those words as `script_attribution`.
- Legal stories: lawsuit existence from the filer's own release, case number, complaint, each party's own statement, the origin of every
  number. Security: advisory, CVE, versions, patch, exploitation, severity disputes. AI products: the company's own release and docs.
  Science: paper, peer review, replication.
- Search with `allowed_domains` set to the primary site (e.g. `oag.ca.gov`, `openai.com`, `nasa.gov`) to reach its own text when the
  site cannot be opened. Never invent URLs, case numbers, quotes or dates; if one cannot be found, write it into `unresolved`.
- **Readiness gate:** if any central script claim is below HIGH, lacks a primary source, quotes unverified wording, or anything is in
  `unresolved`, the package renders as **HOLD — NOT RECORDING READY**. A held package is never delivered as the day's script.
  Save it under `daily/DATE/held_<slug>/package.json` (`creatoros package --date DATE --file ...`) and take the next eligible candidate,
  giving the held story a `hold_reason` in the new package's candidate list.

## 3. Write
- Read `research/creator_style_guide.md` and `research/hook_patterns.md`.
- At least 10 hooks across at least 5 mechanisms, each scored 0-10 on accuracy, clarity, curiosity, natural delivery, relevance and immediate comprehension. Accuracy under 7 disqualifies. Open the script with the top hook.
- One script, natural Hinglish, 75-90 words, 30-40 seconds (40 is a hard limit). The first two seconds must hook.
- Use only claims that are HIGH in the claim table. Leave out true-but-old facts presented as new.
- Recording direction covers delivery only (tone, emphasis, pauses, pronunciation). No video editing instructions.
- Score the ten quality checks honestly; below 90, or any check below 7, means rewrite. Duration is measured by the tool.

## 4. Build
Write `daily/DATE/package.json` (same shape as `daily/2026-11-18/package.json`), then:
```
creatoros package --date DATE
```
It refuses to render if any rule fails, prints `RECORDING READY` or `HOLD — NOT RECORDING READY`, and logs the topic to
`research/content_db.jsonl` (held stories as `held`). Fix problems; never bypass the validator. Only a RECORDING READY package is delivered.

## 5. Deliver
- Commit `daily/DATE/` and `research/content_db.jsonl`; push to the working branch.
- Send one push notification with the topic and `daily/DATE/package.md`. Report delivery only as the tool reports it.
- If no candidate passes the gate by 09:20 IST, deliver no script: say so plainly, list what blocked each top candidate.
- Reply with the package so it can be recorded from the message.
- Do not publish anything anywhere.

## 6. Learning (when the creator supplies numbers)
- `creatoros metrics-add ...` at 24 h, 72 h and 7 days; `creatoros content-update --date D --slug S status=published platforms=instagram,x`.
- Never invent numbers. One video is an anecdote.

## Weekly (Mondays)
- `creatoros weekly --end DATE`, then add a short "Recommendations" section to `reports/weekly/DATE.md`, citing the data above it.
- Refresh `research/creator_benchmarks.md` and `research/creator_video_samples.csv` (competitor database). Keep MEASURED, THIRD-PARTY and HYPOTHESIS labels; don't claim to have watched videos you could not open.
