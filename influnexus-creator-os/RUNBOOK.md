# Daily runbook: research → viral topic → recording package (English; V7 from 23 Nov 2026)

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
  `logs/runs.jsonl` and `run_report.json` are committed; they are the evidence that a run happened. `runlog end` (and
  `runlog delivery`) also refresh `today.md`, so its RUN STATUS line shows this run's final status and delivery.
- Never re-render a past date's package: historical packages stay as delivered.
- `creatoros runlog start` now runs the source audit itself, BEFORE research, and saves `daily/DATE/source_access.json`
  (tiered packages are refused without it). `creatoros sources-audit --date DATE` re-runs it by hand: it probes every source group (X, Reddit, YouTube, Instagram, LinkedIn,
  Google Trends, primary sites, news) from this environment and saves `daily/DATE/source_access.json`. A group it reports BLOCKED
  can only be researched through web-search excerpts (SEARCH-INDEX) or secondary reporting, and the validator refuses any claim
  that it was DIRECTLY OBSERVED. Do not retry blocked hosts.
- `creatoros runlog status --date DATE` reports whether the 08:41 scheduled run started, ended and was READY by 09:30
  (PENDING / RUNNING / OK / LATE / HOLD / NONE / FAILED / MISSED; exit code 4 = problem). Report any problem verdict to the creator.
- Network: this cloud environment cannot open nature.com, biorxiv.org, health.ucdavis.edu, x.com or most news sites (DNS refused by
  the environment's network policy). Reach primary sites through domain-restricted search and record `access: search-index`.
  Never record `opened` for a page that was not fetched. Widening the environment's Allowed domains would let pages be opened.
- If `daily/DATE/today.md` already says RECORDING READY, do not research again: re-check time-sensitive claims, re-run
  `creatoros package --date DATE`, deliver it, and log the run as `--status READY --note reused`.

## Cost control (from 21 Nov 2026)
The 20 Nov run cost about $11, almost all of it the main session re-reading its long conversation history (~730K tokens) on
each of 28 requests; the research itself (12 searches) cost about $0.14. So the scheduled session stays thin:
1. Main session: setup, `creatoros runlog start --trigger scheduled` (audits sources first), then hand steps 1-4 (research,
   verification, writing, `creatoros package`) to ONE subagent (Agent tool, fresh context) with a short brief: the run_id,
   research window, budgets, and "follow influnexus-creator-os/RUNBOOK.md (V7, Verification policy) and write
   daily/DATE/package.json; return the package status and topic". The subagent does all searches and file work.
2. Main session again: `creatoros growth`, the push notification, `creatoros runlog end`, one commit and push, the reply.
   Aim for at most about 8 main-session requests, batch independent tool calls, and never paste large files into the main session.
Research depth, verification thresholds and the deadline do not change. A fresh session per run would cut the cost further,
but that needs a new scheduled task, which only the creator can approve.

## Delivery stages (never claim more than the evidence shows)
`creatoros runlog stages --date DATE` reports separately: package generated, package saved, pushed (commit on the production
branch), notification requested, notification accepted by the provider, notification received by the creator. The push tool's
reply is "requested". Record `--delivery accepted` only with the provider's response as `--receipt`, and `received` only with
the creator's confirmation; the CLI refuses either without a receipt.

## Verification policy (permanent from 2026-11-21; tiered, risk-based)
Each script claim's risk is classified from its temporal meaning (`classify_risk` in `factcheck/evidence.py`): present or future
context ("today", "out now", "next month", "will", "aaj"), a future date or a date within 90 days makes it `high` (time-sensitive);
an explicit past date over a year old or "years ago", "back in", "originally" makes it `low` (historical); with no time cue,
prices, launches, availability, security and finance default to `high`, other stable descriptions to `low`. An optional
`event_date` sharpens it. A declared `risk` can raise the classification, never lower it. Each claim also has an `evidence` list of sources
(`url`, `kind` primary/news/reference/blog/forum/user-edited, `access` opened/search-index/secondary, `date`, optional `outlet`,
`syndicated_from`) plus `conflicts` when sources disagree. The level is computed (`creatoros/factcheck/evidence.py`), never declared:
- **HIGH:** a primary source opened directly (or authenticated primary material).
- **MEDIUM-HIGH:** official text read through a search index, plus at least two genuinely independent reputable sources.
- **MEDIUM:** at least two independent reputable reports, consistent, each dated and attributed.
- **LOW:** a single source, unclear attribution, syndicated copies of one report, or incomplete evidence.
- **UNVERIFIED:** rumour, conflicting sources, or nothing traceable.
Copies of one report count once; blogs, forums and user-edited wikis (fandom, TV Tropes, Reddit) never count as reputable;
search excerpts agreeing never make a claim HIGH. Gate: high-risk claims need MEDIUM-HIGH or better and a corroborating report
dated within 7 days; low-risk claims need MEDIUM or better. **Extraordinary financial claims** (share prices and moves, IPO
pricing and proceeds, valuations, market caps, amounts in the billions; detected automatically, or set `financial: true`) that are
time-sensitive need **HIGH**: the primary document itself opened directly (e.g. the company's release on its own site). Search
excerpts of a primary page plus press coverage are not enough for them.
**Automatic fallback:** if the selected story fails, `creatoros hold --date DATE --reason "..."` archives it under
`daily/DATE/held_<slug>/`, logs it in `holds.json` and names the next-ranked story; give the held candidate its `hold_reason`
(the validator insists) and verify the next one. Repeat until one passes. Never fill an evidence gap. If none passes, deliver no
script and say why. A creator-requested topic (`creator_request`, REEL SCRIPT: [TOPIC]) is exempt from the window and the top-score rule,
not from verification.

## V7: Viral AI & Technology Creator Engine (accepted from 2026-11-22, required from 2026-11-23)
The creator's V7 brief. Where it differs from v6, v5, v4 or v3 below, this section wins. Unchanged and still required:
"Verification policy", HOLD/fallback, time budget, cost control (ONE fresh subagent), delivery stages, the duplicate guard.
`"scoring": "v7"`, `"language": "english"`. Goal: 100,000 followers within 60 days from 2026-11-22 (a stretch goal, never promised).
Optimise for qualified growth: shares, saves, watch time, completion, replays, comments, profile visits, follows per 1,000 views.
1. **Discovery window:** the previous 24 hours from the run's own start (UTC and IST are printed by `runlog start`). An older
   event qualifies only with a genuinely new, dated development; record the original event date (`event_date`) separately
   from the publication date (`announced_at`). Widening to 48-72 h stays allowed with `window_expansion_reason` when the 24 h
   pool is too thin. Never fabricate recency.
2. **Sweep broadly:** AI labs (OpenAI, Anthropic, Google DeepMind, Meta, xAI, Mistral, DeepSeek, NVIDIA, Microsoft, Amazon,
   Apple, new labs); AI products and tools (agents, video, image, coding, browsers, assistants, automation); creator tech
   (Instagram/YouTube features, editing, AI filmmaking, avatars, voice, monetization, algorithms); business and marketing tech;
   robotics and hardware; science and health; fintech and cybersecurity; industry (acquisitions, launches, policy,
   controversies, demos). Sources: X, official blogs, papers, GitHub releases, launch pages, credible publications, developer
   communities, YouTube and LinkedIn announcements. Original sources first. X metrics only when observed (x.com is blocked
   here: say the social signal is unverified).
3. **Pool of 20-30 credible developments** when the news supports it (fewer only with `candidate_shortfall_reason`, never
   filler). Remove duplicates, recycled news, rumours, misleading demos, unverifiable claims, pure promotion. Each candidate:
   every v3 field plus `claim_status`, `latest_development`, `audience_relevance`, `practical_usefulness`,
   `visual_potential`, `potential_controversy`.
4. **Virality model (each 0-10, weights):** broad_relevance 20, surprise 15, usefulness 15, social_momentum 15, visual 10,
   consequence 10, discussion 10, timeliness 5. social_momentum above 3 needs observed discussion, above 6 observed numbers.
   **Verification is a gate:** only CONFIRMED or INDEPENDENTLY REPORTED stories are eligible (COMPANY-CLAIMED, PRELIMINARY,
   SPECULATIVE, DISPUTED are not). Editorial judgements, not view predictions.
5. **Stories people can use:** a tool millions can use, or a striking robotics demo, beats an obscure breakthrough. Answer
   `audience_check` (one sentence each): why_care_today, affects_life_or_work, can_they_use_it, surprising, demonstrable,
   clear_consequence, would_share, right_audience. Never choose a story only because it is technically impressive; if the top
   story is too technical, compare it with accessible alternatives and say why it still wins (`why_beats_alternatives`).
6. **Fact-checking:** source priority primary docs > official announcements > original research > direct statements >
   credible independent reporting > commentary. Claim labels add COMPANY-CLAIMED, INDEPENDENTLY REPORTED and PRELIMINARY (all
   said with attribution) to CONFIRMED, SPECULATIVE and DISPUTED. A GitHub repository is not proof of correctness, a company
   benchmark is not independent validation, a demo is not general capability, a press release is not commercial success, a
   proof checker does not validate every assumption. Do not rely on snippets for critical claims; say when a source could not
   be opened.
7. **Extraordinary claims** (famous problems solved, AGI, major medical breakthroughs, autonomous discoveries, historic firsts,
   billion-dollar events, security breaches, radical robotics) are detected automatically (`evidence.is_extraordinary`, or
   `extraordinary: true`). In the script they need the primary source OPENED and independent confirmation OPENED (credible
   reporting or a named expert's own statement, kind `expert`; never GitHub, never a snippet), plus `scrutiny`: who_claimed,
   what_demonstrated, independent_confirmation, uncertainty, reproduced, preliminary. If uncertainty is substantial, make it
   central to the story. Never imply universal acceptance from a limited endorsement.
8. **One story, one idea:** one central idea, one reason to care, one visual angle, one takeaway. No roundups. If nothing
   credible meets the bar, say so and deliver no script.
9. **Script:** 30-40 seconds (40 hard), about 70-90 words, estimated at 140 wpm plus a 0.35 s pause per sentence (about 75-85
   words fits). Hook 0-2 s, context 2-10, development 10-25, takeaway 25-34, ending 34-40 (flexible). Conversational, global,
   confident and curious; not a news anchor, spokesperson, AI explainer or clickbait account. Short sentences, one narrative,
   no headline repetition, no unnecessary statistics, no sentence over 22 words.
10. **Hooks:** at least 5, each scored 0-10 on accuracy, clarity, curiosity, specificity, emotional, comprehension, with an
    approach (surprising capability, unexpected consequence, major product reveal, practical discovery, contradiction,
    unusual demonstration, important warning; at least 3 different). Accuracy under 7 disqualifies; the top accurate hook
    opens the script. Banned: "You won't believe this", "This changes everything", "AI is getting crazy", "The future is
    here", "Nobody is talking about this" and other generic openings.
11. **Practical takeaway** (`practical_takeaway`): who_can_use, what_it_does, availability, price, difference, limitations,
    why_it_matters. Write UNKNOWN or "not applicable" rather than inventing availability or price. For research, the real
    significance without invented applications.
12. **Script checks** (`script_checks`, each `{pass, why}`): hook_clarity, factual_accuracy, natural_delivery,
    narrative_coherence, audience_relevance, practical_takeaway, ending_quality, no_redundancy, no_jargon,
    no_unsupported_implications. Any false: revise (max 3 `revisions`). factual_accuracy cannot pass unless the claim table is
    RECORDING READY.
13. **Story history:** `story_id`, `company`, `event_date` (plus the date selected) go into `research/content_db.jsonl` with
    the script and sources. Repeats need `material_update_of` explaining what changed.
14. **Performance:** `creatoros learn` compares topics, hooks, categories, script lengths (length bands) and posting times
    with the account median (3 reels minimum per group); it reports that Instagram analytics are not connected. Copy its line
    into `learning_applied`. `creatoros growth` shows weekly checkpoints toward 100,000 (UNKNOWN until the creator gives a
    starting follower count).
15. **Delivery (`today.md`), seven sections only:** 1 story (headline, date, category, confidence); 2 why this story
    (`why_this_story`, 100 words or fewer, including the observable X signal and why it beat alternatives); 3 the script;
    4 caption (strong opening, key fact, natural question; 60 words or fewer) with 3-5 hashtags; 5 sources (with dates and
    whether each was opened); 6 fact-check notes (confirmed, uncertainties, excluded claims: `excluded_claims`); 7 recording
    guidance (`recording_guidance`: hook_emphasis, important_pause, final_tone). No editing plan. v6 fields (finalists,
    variants, visual plan, creative gate) are not required in V7; `thumbnail_text`, `pinned_comment` and `edit_beats` are optional.

## v6: creator-led editorial quality (accepted 2026-11-22 only; superseded by V7 before it became mandatory; the creator's "Fix daily script quality" brief, 22 Nov 2026)
Goal: content a broad audience shares, saves, comments on and follows for (150,000 Instagram followers in four months from
22 Nov 2026: an ambitious target, not a guaranteed outcome). Not a news summary; do not optimise for merely finishing a script.
Where this section differs from the v5, v4 and v3 text below, this section wins. Everything in "Verification policy",
HOLD/fallback, the time budget, cost control and delivery stages still applies. `"scoring": "v6"`, `"language": "english"`.
1. **Research 15-25 stories** from the 24-hour window. Widen to 48 h (then 72 h) with `window_expansion_reason` when no strong
   verified story exists OR fewer than five candidates are eligible (weekends: the 22 Nov trial found only two in 24 h, while
   70-point stories from the day before were excluded); a widened story still needs a dated development inside the wider window: OpenAI, Google, DeepMind,
   Anthropic, Meta, Apple, Microsoft, Amazon, NVIDIA, Tesla, SpaceX, xAI, robotics, startups, cybersecurity, consumer tech,
   science, AI applications, emerging tech. Look for surprising developments, useful discoveries, controversies, major launches,
   unexpected demos, important debates and tech that affects everyday life. Do not force an AI-model story when another
   technology story is stronger. Public X discussion first where evidence is reachable; x.com is blocked here, so say so and keep
   X metrics UNKNOWN. Fewer than 15 credible candidates only with `candidate_shortfall_reason` (never pad).
2. **Verify before writing.** Each candidate has `claim_status`: CONFIRMED, REPORTED (credible reporting, said with attribution),
   CLAIMED (a company's or person's assertion, said as "X says"), SPECULATIVE, UNVERIFIED. Only CONFIRMED or REPORTED stories
   can be selected. Claim-table statuses add CLAIMED (needs `attribution` and `script_attribution`). Never turn a rumour into a
   fact or invent a financial number.
3. **v6 rubric** (each 0-10; editorial estimates, never view predictions): curiosity 12, surprise 12, broad_relevance 12,
   shareability 12, save_potential 10, comment_potential 10, visual_storytelling 10, practical_usefulness 8,
   long_term_relevance 6, factual_confidence 8. factual_confidence 8+ needs claim_status CONFIRMED; under 6 is ineligible.
   Each candidate also needs `why_share` and `visual_note` (plus every v3 field).
4. **Five finalists** = the five highest-scoring eligible candidates (`finalists`, or fewer with `finalist_shortfall_reason`).
   The winner is the top eligible story (or the creator's own topic). Every losing finalist has `why_not`; the package's
   `why_beats_alternatives` explains why the winner beats them.
5. **25 hooks:** five per finalist, one per approach: surprising fact, unexpected consequence, direct relevance, contrarian
   question, visual demonstration. Each at most 14 words (it must land in 1-2 seconds) and scored 0-10 on accuracy, curiosity,
   clarity, credibility, emotional, natural. Accuracy under 7 disqualifies. Banned: "Big news in AI today", "Something crazy just
   happened", "You won't believe this", "Breaking news", "Stop scrolling" and other generic or misleading clickbait. The chosen
   `hook` is the winner's top-scoring accurate hook: the strongest truthful curiosity.
6. **Three variants** for the winner in `variants`: `A` high-curiosity storytelling, `B` practical usefulness, `C` surprising
   consequences, each `{"angle": ..., "script": ...}`: 85-105 words, 35-45 s at a natural pace, conversational English-first,
   no news-anchor or press-release voice, no hype, no unnecessary jargon. Pick one (`selected_variant`, `variant_rationale`);
   `script` is that variant word for word. Rejected drafts may go in `rejected_drafts` (internal).
7. **Structure (adapt, never mechanical):** 0-2 s hook; 2-8 s why viewers should care; 8-25 s the most interesting facts;
   25-35 s a useful takeaway or surprising implication; 35-45 s a memorable ending or a specific question.
8. **Visual plan** (`visual_plan`): `opening_visual`, `broll`, `screen_recordings`, `demonstrations`, `motion_graphics`,
   `on_screen_text`, `transitions`. Opening visual, on-screen text and transitions are required, plus at least two of broll,
   screen recordings, demonstrations, motion graphics. Each demonstration or screen recording is `{"what": ..., "source": URL of
   real footage | "creator-recorded"}`; never describe a demo that does not exist. Prefer stories that can be shown.
9. **Natural pacing:** the validator estimates duration at 140 words per minute plus a 0.35 s pause after each sentence
   (until the creator's voice is calibrated), so about 85-95 words fits; 105 words usually does not. No sentence over 22 words.
10. **Creative quality gate** (`creative_gate`): each of `nontechnical_viewer_cares`, `hook_compelling`, `delivers_on_hook`,
    `takeaway`, `natural_language`, `visualizable`, `claims_verified`, `memorable_ending`, `sounds_like_creator` is
    `{"pass": true|false, "why": "a concrete reason"}`. Any false means rewrite (max 3 `revisions`) or choose another story.
    `claims_verified` cannot pass unless the claim table is RECORDING READY. Keep `quality_v5` (six-part score); do not inflate it.
11. **Performance learning:** run `creatoros learn` first. It reads only recorded numbers (analytics/performance.csv), compares
    hooks, topics, pillars and formats with the account's own median, and says plainly when Instagram analytics are not
    connected. Put its `learning_applied` line (or what the data changed today) in the package. Never invent performance data.
12. **Delivery (`today.md`)** has only: 1 story, 2 why selected, 3 verified facts and sources, 4 the recording-ready script,
    5 estimated duration, 6 opening visual, 7 a concise caption (60 words or fewer), 8 three to five hashtags. Finalists, the 25
    hooks, the variants, the full visual plan and the gate go to `creative.md` and `research.json` (internal).
13. **Production-equivalent test:** `creatoros package --file DIR/package.json --trial` validates and renders beside the file
    without touching the content or memory databases.
`thumbnail_text`, `pinned_comment` and `edit_beats` are optional in v6. `hooks` may be omitted (the winner's five are used).

## v5: Master Prompt V5 (required 2026-11-21 to 2026-11-22; superseded by v6; v3, v4 or v5 accepted on 2026-11-20)
Where this section differs from the v4 and v3 text below, this section wins. `"scoring": "v5"`, `"language": "english"`
(creator's instruction, 21 Nov 2026: natural conversational English for a global audience; Hinglish only on request).
- **Language:** natural conversational English for a global audience: short sentences, simple international words, technical
  terms explained once; no corporate jargon, forced slang or robotic narration. Hinglish only when the creator asks for it.
- **Research:** last 24 hours; widen to 48-72 hours only when no strong verified story exists (`research_window.hours` 48 or 72
  plus `window_expansion_reason`). Search internationally, with attention to stories Indian audiences care about. Separate the
  announcement date from the date of any older event being discussed. Never call an unverified story confirmed.
- **Story scores:** the v3 rubric (public discussion 20, surprise 15, significance 15, usefulness 15, visual 10, broad appeal 10,
  conversation 5, longevity 5, verification 5). Missing engagement is UNKNOWN and lowers confidence; the top number does not win
  automatically when its evidence is weak. Shortlist at least 5 credible candidates. Write `why_beats_alternatives`.
- **Gaming:** set `category: "GAMING"` and `release_type` (original release, re-release, remaster, remake, fan-made modification,
  rumor, official announcement, launch). Never say a game launched unless the release is independently verified. For nostalgic
  games: childhood memories, recognisable gameplay, iconic music or places, surprising history, modern relevance.
- **Hooks:** at least 5 scored internally on accuracy, curiosity, clarity, credibility, emotional impact and natural delivery
  (accuracy under 7 disqualifies); no "Hey guys", "Today we're talking about", "Did you know", "In today's video", "Breaking news".
- **Script:** 85-105 words, 35-45 s (45 hard): hook (0-3 s), what happened (3-10), most interesting details (10-25), why it
  matters (25-37), satisfying ending or a specific question (37-45). Natural over formulaic; every sentence earns its place.
- **Quality score** (`quality_v5`, 0-10 each): hook 20, clarity 15, storytelling 20, retention 15, shareability 15, factual
  confidence 15. Below 90: revise (`revisions`, max 3), then state `quality_limitation`. Factual confidence under 8 always fails.
- **Package fields:** `verified_development`, `confidence`, `thumbnail_text` (six words or fewer), `pinned_comment`,
  `edit_beats` (`0-3`, `3-10`, `10-25`, `25-45`: visuals, screenshots, graphics, licensed B-roll; never assume footage is licensed).
- **Delivery (`today.md`):** A selected topic, B final script (near the top, no timestamps or stage directions inside it),
  C recording directions, D editing directions, E posting package (Instagram caption, Shorts title, 3-5 hashtags, thumbnail text,
  pinned comment), F fact-check, G internal quality score. One script only.
- **Creator study:** `research/creators_db.csv` grows toward 300 creators over time; never claim more than it holds. Learn
  principles (hooks, structure, pacing, retention); never copy scripts or distinctive expressions.

## v4: the Instagram growth rubric (superseded by v5 from 2026-11-21)
Where this section differs from the v3 text below, this section wins. `"scoring": "v4"`.
- **Goal:** 100,000 Instagram followers in 60 days (day 1 = 2026-11-20); one reel a day. A target, never a promise.
- **Candidates:** collect at least 15 genuinely distinct stories when verified material exists (`candidate_shortfall_reason`
  otherwise; never pad). Topics include AI breakthroughs, agents, robotics, consumer tech, cybersecurity, space, science,
  AI filmmaking and video generation, creative tools, AI coding, controversies, launches, tech in everyday life. Do not default to
  OpenAI or to any big company; pick what people genuinely care about.
- **Scores (0-10 each, weighted):** social traction 20, novelty and surprise 15, real-world consequence 15, broad appeal 15,
  visual 10, discussion 10, verified significance 10, freshness 5 (`social_traction, novelty, consequence, broad_appeal, visual,
  discussion, verified_significance, freshness`). Social traction above 3 needs signals; above 6 needs engagement actually observed.
  Without observed engagement the total is shown as PROVISIONAL: popularity measured is kept separate from predicted potential.
- **Per candidate:** `published_at` (original announcement), `latest_development_at`, `original_source`, independent source in
  `signals`, `confirmed_facts`, `company_claims`, `unverified_claims`, `x_signal`/`signals` (engagement evidence or UNKNOWN),
  `why_it_matters` (why people care), `why_share`, `visual_note`, `evidence_confidence`.
- **Selection:** prefer a surprising opening, relevance to ordinary people, consequences, visuals, verification, curiosity,
  discussion and a useful takeaway. Avoid generic model announcements, minor updates, rumours, old news, over-technical stories,
  sensational or recycled claims. Write `why_beats_alternatives`.
- **Hooks:** at least 10 scored on accuracy, clarity, curiosity, surprise, relevance, natural (spoken delivery) and retention;
  only the winner is delivered.
- **Script:** 90-105 words, 40-45 s (45 hard): hook (0-2 s), what happened (2-10), surprising details (10-25), why it matters
  (25-35), takeaway or question (35-45); natural rhythm wins over timestamps. No unsupported numbers.
- **Creative score** (`creative_scores`, 0-10 each): hook 20, clarity 15, human delivery 15, relevance 15, information 15,
  retention 10, discussion 10. Target 90. Below 90: revise and re-score (`revisions`, max 3); after the third, state
  `quality_limitation` honestly. Facts are a separate hard gate: a material factual error fails the package whatever the score.
  Score against these criteria; never nudge numbers to reach 90.
- **Also in the package:** `posting_window` (`window_ist`, `rationale`, `basis` hypothesis until the account's own data shows a
  better time, then observed with `evidence`) and `audience_hypothesis` (the expected response, to be checked against numbers).
- **Morning deliverable** (`today.md`): winning story, why, top five ranked candidates (provisional where traction was not
  measured), strongest verified social signal, fact-check, script, Instagram caption, 3-5 hashtags, posting window, audience
  hypothesis, sources, confidence and limitations. Detailed research is in `package.md` and `research.json`.
- **Budget:** existing tools only (web search, no paid APIs). Aim for at most about 40 searches per run; two attempts per
  blocked domain; no retries beyond the RUNBOOK time budget.
- **Learning:** after publishing, record reel numbers at 2h, 24h, 48h and 7d with `creatoros metrics-add` (no Instagram analytics
  connection exists yet). Rates are per account reached: share rate, save rate, follower conversion, follows per 1k reach; each
  reel is compared with the account's own median. Weights change only with evidence, logged in `research/scoring_changes.md`.

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
- **Source groups:** X (leaders such as Musk, Altman, Huang, Hassabis, Pichai, Nadella, Zuckerberg, Amodei, Karpathy, LeCun,
  Ng, Fei-Fei Li, plus founders, researchers, engineers, investors, journalists and smaller accounts); Reddit (r/artificial,
  r/technology, r/singularity, r/MachineLearning, r/LocalLLaMA, r/OpenAI, r/ChatGPT, r/ClaudeAI, r/Futurology, r/robotics,
  r/programming, r/startups, r/Entrepreneur); YouTube (tech creators and Shorts: study patterns, never copy); Instagram reels;
  LinkedIn; Google Trends; primary sources; credible reporting (Reuters, AP, Bloomberg, The Verge, TechCrunch, Ars Technica,
  Wired, MIT Technology Review, IEEE Spectrum, FT). Reporting helps discovery; it never replaces available primary evidence.
- **Cross-platform signals (`signals` on each candidate; required for the selected story):** one entry per observation:
  `platform` (x, reddit, youtube, instagram, linkedin, google_trends, primary, news), `url`, `title`, `retrieved_at`,
  `access` (DIRECTLY OBSERVED / SEARCH-INDEX / SECONDARY / NOT VERIFIED) and `engagement` with `basis`
  observed / reported / estimated / unknown (+ `source` for reported numbers). "observed" needs the page directly observed.
  A story seen across several independent platforms is a stronger signal; an estimate is never shown as a measurement.
- **Search tactics (learned in the 19 Nov manual test):** generic "AI news today" queries return mostly older pages. What works:
  the date in quotes ("November 18, 2026") plus a topic, dated daily digests (e.g. AI news-of-the-day pages) as leads, then
  domain-restricted searches on the primary site (`allowed_domains`: nasa.gov, blog.google, blogs.microsoft.com, nvidianews.nvidia.com,
  openai.com...) to verify, and a search with the primary domain blocked to find independent reporting.
- **Dates:** when a source gives a date but no time, record `published_at` as `YYYY-MM-DD`; it counts if that day overlaps the
  window. Never invent a time.
- **Early stories:** prefer important developments before they saturate creator platforms (new tools, robotics demos,
  unexpected capabilities, research results, failures, security discoveries, consumer changes, startup surprises).
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
- Discover at least 10 candidates when credible material exists; shortlist 5-10 (the validator needs 5 at MEDIUM or HIGH). Do not pad: weak items go in with
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
- Claim labels: CONFIRMED, REPORTED (said with attribution), UNVERIFIED, SPECULATIVE (plus the finer existing labels).
  Never confuse a prototype with a product, a demo with general capability, a benchmark with real-world performance,
  valuation with revenue, a research claim with consensus, or a rumour with confirmation.
- Hooks (v3): score at least 10 internally on accuracy, clarity, curiosity, surprise, specificity, natural delivery and
  relevance (/70; accuracy under 7 disqualifies). Only the winner is delivered; the rest go to `research.json`. Do not reuse an
  opening from the last 14 days (the validator checks the first three words).
- Accuracy: never generalise one trial participant to all patients; a prototype is not a product you can buy; valuation is not
  revenue; a speculative capability is not a demonstrated one; preliminary research says so.
- Recording direction covers delivery only (tone, emphasis, pauses, pronunciation of difficult names). Visual suggestions for the
  separate editor go in `visuals`; nothing else about editing.
- Score the ten quality checks honestly; below 90, or any check below 7, means rewrite. Duration is measured by the tool.

## 4. Build
Write `daily/DATE/package.json` with `"scoring": "v3"` (the shape of `daily/2026-11-19/package.json` plus `research_window`
copied from `runlog start`, `generated_at`, v3 candidates and `retrieved_at` on claims), plus:
- `pillar`: ai_breakthroughs (30%), future_tech_robotics (20%), useful_ai_tools (15%), big_tech_leaders (15%), consumer_hardware (10%),
  startups_science (10%). Starting shares are hypotheses; never force a pillar over a clearly stronger story.
- `format`: A "Something important just happened", B "This technology is actually useful", C "The future is already here",
  D "Everyone is talking about this, but...", E "Here's what most people missed", F "This changes how we use technology",
  G "Watch what this technology can do", H "The real story behind this announcement".
- `backups`: two other eligible candidates (recovery only), or `backup_shortfall_reason`.
- `audience`: stop_scroll, watch_to_end, share, save, comment, follow (one honest sentence each; no outrage or fear bait).
- `editing`: opening_visual, key_moments, broll, on_screen_text, demonstrations, stats, rhythm, caption_emphasis, sound
  (authentic, licensable visuals only; label illustrations as illustrations).
- `limitations`: what could not be reached today (from the source audit) and any other research limits.
Including `visuals`
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
- `creatoros growth --date DATE` refreshes `reports/growth/DATE.md` (100K/60-day target from 22 Nov, weekly checkpoints, trajectory, observed conversion, content mix;
  UNKNOWN where no numbers exist).
- `creatoros runlog end ...` (above), then commit `daily/DATE/`, `research/*.jsonl`, `reports/growth/` and `logs/` in ONE commit and push
  (pull `--rebase` first; retry the push up to 4 times with backoff). If the push fails, say PACKAGE READY — DELIVERY FAILED.
- If no candidate passes the gate by 09:22 IST, deliver no script: say so plainly, list what blocked each top candidate.
- Reply with the contents of `creatoros today` (DATE, SELECTED TOPIC, WHY, VIRAL POTENTIAL, BEST HOOK, FINAL SCRIPT, DURATION,
  RECORDING DIRECTIONS, VISUAL SUGGESTIONS, FACT-CHECK, ENGLISH CAPTIONS, PLATFORM CONTENT), concise enough to record from.
- Do not publish anything anywhere.

## 6. Learning (when the creator supplies numbers)
- `creatoros learn` turns recorded numbers into lessons (best hooks, topics, follower conversion, weakest categories) against
  the account's own median; with no data it says so. Run it before scoring each day (V7 step 14).
- No analytics connector (Instagram, YouTube, X, LinkedIn) is connected, so numbers come from the creator.
- `creatoros metrics-add date=D video_id=D_SLUG platform=P checkpoint=24h|72h|7d views=.. reach=.. avg_view_duration_s=..
  completion_rate=.. shares=.. saves=.. comments=.. profile_visits=.. new_followers=.. pillar=.. format=.. hook_type=.. source=..`
  at 24 h, 72 h and 7 days; `creatoros content-update --date D --slug S status=published platforms=instagram,x`.
- `creatoros followers-add --date D --platform instagram|youtube|x|linkedin --followers N --source "where it was read"`.
- Never invent numbers. One video is an anecdote; groups under three videos are not evidence. Correlation is not causation.

## Creator intelligence
- `research/creators_db.csv` holds the verified creator database (target 100-200; started at 50+). Record metrics only when observed,
  with source and date; anything not watched is NOT OBSERVED. Learn principles; never copy scripts or distinctive expression.

## Weekly (Mondays)
- `creatoros weekly --end DATE` (topics, 60-day target, pillar and format mix, 7-day performance by pillar/format/hook type),
  then add a short "Recommendations" section to `reports/weekly/DATE.md` citing the data above it: top and weak topics, best hooks
  and lengths, follower conversion, repeated audience questions. Change one variable at a time.
- Refresh `research/creator_benchmarks.md` and `research/creator_video_samples.csv` (competitor database). Keep MEASURED, THIRD-PARTY and HYPOTHESIS labels; don't claim to have watched videos you could not open.
