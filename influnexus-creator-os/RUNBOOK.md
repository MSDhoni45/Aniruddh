# Daily runbook: research → viral topic → recording package (English)

Run by the scheduled task "Influnexus daily brief" at 08:41 Asia/Kolkata so the package is ready by 09:30 IST, and whenever the
creator types "Script for today" (see the command table in the repository's `CLAUDE.md`).
`DATE` is today's date in IST. This project stops at a recording-ready script. It does not edit, render or publish video.

Every run is stateless: it needs nothing from an earlier conversation. All state is in this repository (packages, `research/*.jsonl`,
`logs/runs.jsonl`, `daily/DATE/run_report.json`). Read only today's files and the databases; do not load old packages.

## 0. Setup (the container may be fresh). Retry each network step at most 3 times with 5/15/45 s backoff.
```
git fetch origin claude/daily-ai-tech-research-script-taab6w
git checkout -B claude/daily-ai-tech-research-script-taab6w origin/claude/daily-ai-tech-research-script-taab6w
cd influnexus-creator-os && pip install -q -e .
```
If setup fails after the retries, write what failed to `logs/runs.jsonl` (`creatoros runlog end --status NONE --error "..."`) if the
CLI works, and say so in the reply. Never continue on a stale or wrong branch.

## 0.5 Log the run and check for an existing package
- `creatoros runlog start --trigger scheduled` (or `--trigger manual`). It prints the `run_id`, the 24-hour `research_window`
  (UTC and IST), the git commit, the cloud environment and the phase `budgets`. Keep the `run_id`.
  - Exit code **5 = ALREADY_DONE**: today's scheduled run already finished READY. Do not research or commit again; reply with
    `creatoros today` and say it was already delivered. Exit code **6 = IN_PROGRESS**: another run started under an hour ago; stop.
  - A scheduled start with no end after 60 minutes is closed as INTERRUPTED and a new run proceeds.
- At the end: `creatoros runlog end --run-id RUN_ID --status READY|HOLD|NONE --delivery requested|failed|not attempted --channel push
  [--error "..."] [--warning "..."]`. It writes `daily/DATE/run_report.json` (run ID, start/end, environment, commit, window,
  candidates, selected story, source access, fact-check, words, duration, quality gate, package status, delivery, errors, warnings).
  `logs/runs.jsonl` and `run_report.json` are committed; they are the evidence that a run happened.
- Never re-render a past date's package: historical packages stay as delivered.
- `creatoros runlog status --date DATE` reports whether the 08:41 scheduled run started, ended and was READY by 09:30
  (PENDING / RUNNING / OK / LATE / HOLD / NONE / FAILED / MISSED; exit code 4 = problem). Report any problem verdict to the creator.
- Network: this cloud environment cannot open nature.com, biorxiv.org, health.ucdavis.edu, x.com or most news sites (DNS refused by
  the environment's network policy). Reach primary sites through domain-restricted search and record `access: search-index`.
  Never record `opened` for a page that was not fetched. Widening the environment's Allowed domains would let pages be opened.
- If `daily/DATE/today.md` already says RECORDING READY, do not research again: re-check time-sensitive claims, re-run
  `creatoros package --date DATE`, deliver it, and log the run as `--status READY --note reused`.

## Time budget (scheduled run, 08:41 start)
research 09:03 · verification 09:13 · ranking and writing 09:20 · quality and package 09:23 · delivered by 09:25 · hard deadline 09:30.
If a phase overruns, cut scope (fewer candidates, the strongest verified one) rather than miss the deadline. Never spend more than two
attempts on one blocked domain. If nothing passes the gate by 09:22, deliver no script and say what blocked each candidate.

## 1. Research (scoring "v3" from 20 Nov 2026)
- Cover everything in AI and technology, not only model launches: AI models, agents, generative AI, research, tools, AI coding;
  NVIDIA, Microsoft, Google, OpenAI, Anthropic, Apple, Meta, Tesla, xAI, Amazon and emerging companies; founders and CEOs
  (statements, interviews, podcasts, keynotes, predictions, decisions, demos); startups (launches, funding, unusual models, failures);
  robotics, humanoids, space, semiconductors, autonomous and electric vehicles, quantum, biotech, AR/VR, transport, energy;
  consumer tech (phones, computers, wearables, AI gadgets, useful apps, inventions).
- **Window:** the 24 hours in `research_window` from `runlog start`. A story published earlier qualifies only with a
  `new_development` (`what`, `at`) dated inside the window; the validator enforces this. Do not pick an old story because it was reposted.
- **Discovery:** public X/Twitter discussion is a major source: OpenAI/ChatGPT/Sam Altman; Elon Musk, Tesla, SpaceX, xAI/Grok, X;
  NVIDIA/Jensen Huang; Google/DeepMind/Gemini; Apple, Microsoft, Amazon, Meta, Anthropic, Mistral; robotics, humanoids, autonomous
  vehicles, cybersecurity, chips, consumer electronics, startups and VC, science, space, open-source AI, developer tools, AI video,
  hardware. Smaller researchers and builders count as much as famous accounts. Social posts are leads, never facts.
- **X signal (`x_signal`):** `status` VERIFIED / PARTLY VERIFIED / NOT VERIFIED, `posts` (each: `url`, `account`, `posted_at`,
  `retrieved_at`, `access`, `metrics` with likes, reposts, replies, quotes, views as observed numbers or `"UNKNOWN"`), and
  `discussion_evidence` (other public signals: outlets covering it, forum threads, with links). x.com cannot be opened from this
  environment, so X metrics are UNKNOWN and posts found through search are `access: search-index`. VERIFIED needs a post opened
  directly with observed metrics. Never write "trending" without that evidence.
- Each candidate (scoring "v3") records: `headline`, `category`, `topic_type`, `published_at` (ISO with timezone), `original_source`,
  `main_claim`, `verification_status` (VERIFIED / PARTLY VERIFIED / UNVERIFIED / REJECTED), `why_it_matters`, `potential_hook`,
  `target_audience`, `uncertainty`, `evidence_confidence`, `already_covered`, `x_signal`, and editorial scores 0-10:
  public discussion (20), surprise and curiosity (15), real-world significance (15), audience usefulness (15), visual storytelling (10),
  broad appeal (10), discussion potential (5), longevity (5), verification confidence (5)
  (`public_discussion, surprise, significance, usefulness, visual, broad_appeal, discussion_potential, longevity, verification_confidence`).
  Public discussion above 3 needs X posts or `discussion_evidence`; above 7 needs a VERIFIED x_signal. Editorial, never view predictions.
  Do not favour OpenAI by default: the strongest verified story wins, whatever the company or field.
- Check `research/topics_db.jsonl` and `creatoros content-search` for repeats before scoring.
- Search the last 24 hours across all categories above.
- Send searches in parallel. Use social platforms to find discussion and authoritative sources to verify it.
- Record the original announcement date, not the date of a repost.
- Shortlist 5-10 credible candidates (the validator needs 5 at MEDIUM or HIGH). Do not pad: weak items go in with
  `evidence_confidence: "LOW"`; claims that fail verification go in with `rejected`. If fewer than 5, say why in `candidate_shortfall_reason`.
- Every field in `creatoros.research.candidates.REQUIRED_V3`. Unobserved metrics are `"UNKNOWN"`.
- Check repeats: `creatoros content-search "<words>"`. A covered topic only returns with `material_update_of` naming the new development.
- Stories whose key facts will change before recording (e.g. an IPO not yet priced) get `hold_reason`.

## 2. Verify the leading story (permanent rule: claim verification table)
- Every factual claim goes in `factcheck.claims` with: `text` (exact claim), `primary_source` (URL or null), `source_title`,
  `supporting_evidence` (the exact sentence from the source that supports it), `supporting_source`
  (an independent URL or null), `status`, `source_date`, `confidence` (HIGH/MEDIUM/LOW), `access`, `in_script`, and (v3)
  `retrieved_at` (ISO time the source text was read). The rendered fact-check states how many claims were verified from
  search-index excerpts rather than opened pages.
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
- Read `research/creator_style_guide.md` (v0.2, global English) and `research/hook_patterns.md`.
- At least 10 hooks across at least 5 mechanisms, each scored 0-10 on accuracy, clarity, curiosity, natural delivery, relevance and immediate comprehension. Accuracy under 7 disqualifies. Open the script with the top hook.
- One script in 100% natural conversational English for a global audience (`"language": "english"` in the package): 90-105 words,
  40-45 seconds (45 is a hard limit; fewer words if needed to stay under it). Hook in the first 1-2 seconds, then context, why it
  matters, a useful takeaway, and a memorable ending or a natural question. Short sentences, plain international English, explain any
  essential jargon once. No corporate language, fake excitement, clickbait or forced American slang; the validator rejects them.
- The creator records in their natural Indian accent. Never coach an accent; delivery notes cover tone, emphasis, pauses and names only.
- Learn storytelling principles from Cleo Abram, MKBHD, Bilawal Sidhu, Rowan Cheung and Mrwhosetheboss (see `research/creator_style_guide.md`).
  Never copy their lines, formats or catchphrases.
- Use only claims that are HIGH in the claim table. Leave out true-but-old facts presented as new.
- Accuracy: never generalise one trial participant to all patients; a prototype is not a product you can buy; valuation is not
  revenue; a speculative capability is not a demonstrated one; preliminary research says so.
- Recording direction covers delivery only (tone, emphasis, pauses, pronunciation of difficult names). Visual suggestions for the
  separate editor go in `visuals`; nothing else about editing.
- Score the ten quality checks honestly; below 90, or any check below 7, means rewrite. Duration is measured by the tool.

## 4. Build
Write `daily/DATE/package.json` with `"scoring": "v3"` (the shape of `daily/2026-11-19/package.json` plus `research_window`
copied from `runlog start`, `generated_at`, v3 candidates and `retrieved_at` on claims), including `visuals`
(B-roll and graphic suggestions for the creator's separate editor; never footage you can't license, never fake footage). Then:
```
creatoros package --date DATE
```
All platform copy (Instagram caption and cover, LinkedIn, X within 280 characters, YouTube Shorts title, description and keywords)
is in English; the validator checks it. `captions.txt` (on-screen caption text in 2-5 word lines, exact script words) is written
automatically. It refuses to render if any rule fails, prints `RECORDING READY` or `HOLD — NOT RECORDING READY`, and logs the topic to
`research/content_db.jsonl` (held stories as `held`). Fix problems; never bypass the validator. Only a RECORDING READY package is delivered.

## 5. Deliver
- Send one push notification with the topic (the only configured delivery channel besides the run's own reply). The tool reports
  "requested", not a receipt: record `--delivery requested --channel push`; if it errors, `--delivery failed`. Never claim it reached the phone.
- `creatoros runlog end ...` (above), then commit `daily/DATE/`, `research/*.jsonl` and `logs/runs.jsonl` in ONE commit and push
  (pull `--rebase` first; retry the push up to 4 times with backoff). If the push fails, say PACKAGE READY — DELIVERY FAILED.
- If no candidate passes the gate by 09:22 IST, deliver no script: say so plainly, list what blocked each top candidate.
- Reply with the contents of `creatoros today` (DATE, SELECTED TOPIC, WHY, VIRAL POTENTIAL, BEST HOOK, FINAL SCRIPT, DURATION,
  RECORDING DIRECTIONS, VISUAL SUGGESTIONS, FACT-CHECK, ENGLISH CAPTIONS, PLATFORM CONTENT), concise enough to record from.
- Do not publish anything anywhere.

## 6. Learning (when the creator supplies numbers)
- `creatoros metrics-add ...` at 24 h, 72 h and 7 days; `creatoros content-update --date D --slug S status=published platforms=instagram,x`.
- Never invent numbers. One video is an anecdote.

## Creator intelligence
- `research/creators_db.csv` holds the verified creator database (target 100-200; started at 50+). Record metrics only when observed,
  with source and date; anything not watched is NOT OBSERVED. Learn principles; never copy scripts or distinctive expression.

## Weekly (Mondays)
- `creatoros weekly --end DATE`, then add a short "Recommendations" section to `reports/weekly/DATE.md`, citing the data above it.
- Refresh `research/creator_benchmarks.md` and `research/creator_video_samples.csv` (competitor database). Keep MEASURED, THIRD-PARTY and HYPOTHESIS labels; don't claim to have watched videos you could not open.
