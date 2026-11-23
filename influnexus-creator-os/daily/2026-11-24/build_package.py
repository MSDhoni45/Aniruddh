import json, re, sys, copy
S = "/tmp/claude-0/-home-user-Aniruddh/17eda3e7-9760-5ca3-85ee-8b1d60e54fce/scratchpad/"
R = json.load(open(S + "r24_research.json"))
TPL = json.load(open("/home/user/Aniruddh/influnexus-creator-os/daily/2026-11-23/package.json"))
RUN = json.load(open(S + "run24.json")); W = RUN["research_window"]
RET = "2026-11-23T20:05:00+00:00"
KEYS = ("broad_relevance", "surprise", "usefulness", "social_momentum", "visual", "consequence", "discussion", "timeliness")
CAT = [("autonom", "FUTURE TECH"), ("robot", "FUTURE TECH"), ("creator", "CREATOR TECH"), ("game", "GAMING"), ("security", "CONTROVERSY"),
       ("cyber", "CONTROVERSY"), ("retail", "CONSUMER TECH"), ("commerce", "CONSUMER TECH"), ("phone", "CONSUMER TECH"),
       ("deal", "AI BUSINESS & STARTUPS"), ("funding", "AI BUSINESS & STARTUPS"), ("space", "FUTURE TECH"), ("AI", "AI")]
cat = lambda c: next((v for k, v in CAT if k.lower() in str(c).lower()), "TECH COMPANIES")
def status(v):
    for s in ["INDEPENDENTLY REPORTED", "COMPANY-CLAIMED", "CONFIRMED", "PRELIMINARY", "DISPUTED", "SPECULATIVE"]:
        if str(v).upper().startswith(s): return s
    return "SPECULATIVE"
VS = {"CONFIRMED": "VERIFIED", "INDEPENDENTLY REPORTED": "PARTLY VERIFIED", "COMPANY-CLAIMED": "PARTLY VERIFIED",
      "PRELIMINARY": "UNVERIFIED", "DISPUTED": "REJECTED", "SPECULATIVE": "UNVERIFIED"}
BLOCK = ("V7/V8 rule 6b: no critical claim could be checked on a page opened directly; its primary and news hosts are blocked "
         "by the environment's network policy (search excerpts only)")
HOLDS = {"walmart-muse": BLOCK + "; no Walmart or Meta primary found; outlets disagree on scope and on live vs beta",
         "nvidia-huang": BLOCK + "; Nvidia release and SEC 8-K not opened; the 33% stock move needs HIGH; tied to politics and a personal scandal",
         "wang-superintelligence": BLOCK + "; superintelligence claim is extraordinary (primary and independent confirmation must be opened); x.com blocked",
         "waymo-storm-pause": BLOCK + "; the Sunday announcement could not be found again and is easily confused with the 18 Nov pause"}
REJECT = {"korea-exam-ai-cheating": "politics (ministerial resignation) excluded by V8 positioning"}
cands = []
for c in R["candidates"]:
    pub = re.search(r"20\d\d-\d\d-\d\d", str(c.get("published_utc"))); st = status(c.get("verification_status"))
    sc = c.get("scores", {})
    d = {"headline": c["headline"], "category": cat(c.get("category")), "topic_type": "BREAKING",
         "published_at": pub.group(0) if pub else "2026-11-23", "original_source": c["source_url"] if str(c.get("source_url", "")).startswith("http") else "https://example.invalid",
         "main_claim": str(c.get("what_happened", ""))[:300], "verification_status": VS[st], "why_it_matters": str(c.get("why_it_matters", ""))[:300],
         "potential_hook": c["headline"][:100], "target_audience": str(c.get("who_can_use", ""))[:200], "uncertainty": str(c.get("notes", ""))[:300] or "see research.json",
         "evidence_confidence": "LOW" if st in ("PRELIMINARY", "DISPUTED", "SPECULATIVE") else "MEDIUM", "already_covered": False,
         "claim_status": st, "latest_development": str(c.get("what_happened", ""))[:300], "audience_relevance": str(c.get("who_can_use", ""))[:300],
         "practical_usefulness": str(c.get("what_it_does", ""))[:300], "visual_potential": str(c.get("what_can_be_shown", ""))[:300],
         "potential_controversy": str(c.get("notes", ""))[:300] or "none noted",
         "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": [c["source_url"]] if str(c.get("source_url", "")).startswith("http") else []},
         "scores": {k: min(sc.get(k, 0), 3) if k == "social_momentum" else sc.get(k, 0) for k in KEYS}}
    if not pub or "UNKNOWN" in str(c.get("published_utc")):
        d["rejected"] = "announcement date unknown"
    if c["id"] in HOLDS: d["hold_reason"] = HOLDS[c["id"]]
    if c["id"] in REJECT: d["rejected"] = REJECT[c["id"]]
    cands.append(d)
PH = "https://www.producthunt.com/products/motionflare"
PHL = "https://www.producthunt.com/posts/motionflare"
HEAD = "Motionflare: an AI tool that turns a website link into a branded launch video (Product Hunt, 23 Nov)"
cands.append({"headline": HEAD, "category": "CREATOR TECH", "topic_type": "BREAKING", "published_at": "2026-11-23T08:01:00+00:00",
  "original_source": PHL, "main_claim": "Launched on Product Hunt 23 Nov; #3 of the day with 208 upvotes when checked; makers say it turns a URL into a branded video.",
  "verification_status": "VERIFIED", "why_it_matters": "Creators and small businesses need launch videos and rarely have editors.",
  "potential_hook": "Paste your website link and this AI makes the launch video.", "target_audience": "Creators, marketers, founders.",
  "uncertainty": "Features are the makers' claims; not tested; pricing beyond 'free option' unknown.", "evidence_confidence": "MEDIUM",
  "already_covered": False, "claim_status": "CONFIRMED", "latest_development": "Product Hunt launch, 23 Nov 2026.",
  "audience_relevance": "Creators, marketers, founders, small businesses.", "practical_usefulness": "Make a branded product video from a URL; free option listed.",
  "visual_potential": "The creator can record a real test on their own site.", "potential_controversy": "Unverified output quality.",
  "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": [PHL]},
  "signals": [{"platform": "primary", "url": PHL, "title": "Product Hunt launch (connector)", "retrieved_at": RET, "access": "DIRECTLY OBSERVED",
               "engagement": {"basis": "observed", "points": 208}}],
  "scores": dict(zip(KEYS, [5, 6, 7, 4, 9, 3, 5, 10]))})
def E(url, date, outlet): return {"url": url, "kind": "primary", "access": "opened", "date": date, "outlet": outlet}
EV_L = E(PHL, "2026-11-23", "Product Hunt leaderboard (connector)")
EV_P = E(PH, "2026-11-23", "Product Hunt product profile (connector, makers' description)")
def C(i, text, st, ev, sup, attr=None, sattr=None, inscript=True, risk="high"):
    c = {"id": i, "text": text, "status": st, "in_script": inscript, "central": True, "retrieved_at": RET, "event_date": "2026-11-23", "risk": risk,
         "evidence": ev, "supporting_evidence": sup, "primary_source": ev[0]["url"], "source_title": ev[0]["outlet"], "supporting_source": ev[-1]["url"],
         "source_date": "2026-11-23", "confidence": "HIGH", "access": "opened"}
    if attr: c["attribution"], c["script_attribution"] = attr, sattr
    return c
claims_all = [
 C("c1", "Motionflare launched on Product Hunt on Monday 23 November 2026 and was among the day's top three launches (ranked #3 with 208 upvotes when checked)", "CONFIRMED",
   [EV_L], "Leaderboard 2026-11-23: Motionflare, launched 2026-11-23T00:01 PT, points 208, daily_rank 3."),
 C("c2", "Motionflare's makers say you paste a website URL and it uses your real product screenshots, logo, colors and copy to create branded motion graphics with music and optional narration", "COMPANY-CLAIMED",
   [EV_P], "Profile: 'Paste a URL and it uses your real product screenshots, logo, colors, and copy to create branded motion graphics with music and optional narration.'",
   attr="Motionflare's makers (Product Hunt listing)", sattr="Its makers say"),
 C("c3", "The makers say a Film mode generates a live-action commercial, results can be refined by chat, and videos export in up to 4K", "COMPANY-CLAIMED",
   [EV_P], "Profile: 'Or switch to Film mode to generate a live-action commercial. Refine the result by chat and export in up to 4K.'",
   attr="Motionflare's makers (Product Hunt listing)", sattr="Its makers say"),
 C("c4", "Motionflare's Product Hunt listing shows a free option (pricing: free options)", "COMPANY-CLAIMED",
   [EV_P], "Profile pricing_type: free_options.", attr="Product Hunt listing", sattr="its listing shows"),
]
claims = claims_all
claims[2]["text"] = "The makers say results can be refined by chat and videos export in up to 4K (they also describe a Film mode for live-action commercials)"
claims[2]["supporting_evidence"] = "Profile: 'Or switch to Film mode to generate a live-action commercial. Refine the result by chat and export in up to 4K.'"
claims[3]["script_attribution"] = "its listing even shows"
script = ("Paste your website link, and this AI makes the launch video for you.\n\n"
          "It's called Motionflare, one of Product Hunt's top three launches on Monday.\n\n"
          "Its makers say it pulls your real screenshots, logo, colors and copy from your site.\n\n"
          "Then it adds motion graphics, music and optional narration.\n\n"
          "You edit it by chatting, and export in up to 4K.\n\n"
          "Its listing even shows a free option.\n\n"
          "So before you pay an editor, try it on your own site.")
hook = "Paste your website link, and this AI makes the launch video for you."
H = lambda t, a, acc, cl, cu, sp, em, co: {"text": t, "approach": a, "accuracy": acc, "clarity": cl, "curiosity": cu, "specificity": sp, "emotional": em, "comprehension": co}
hooks = [H(hook, "practical discovery", 8, 9, 9, 8, 7, 9),
 H("This AI turns any website into a launch video.", "surprising capability", 7, 9, 8, 7, 7, 9),
 H("Need a product video but no editor?", "practical discovery", 8, 9, 7, 6, 7, 9),
 H("Your website already has everything for a video ad.", "contradiction", 7, 7, 8, 6, 6, 8),
 H("One link in, one branded video out.", "unusual demonstration", 7, 8, 8, 7, 6, 8),
 H("Monday's number-three launch on Product Hunt makes videos from links.", "major product reveal", 9, 7, 6, 8, 4, 7),
 H("Small brands might not need a video editor for launches anymore.", "unexpected consequence", 5, 8, 8, 5, 7, 8),
 H("I found an AI that reads your website and directs your ad.", "surprising capability", 6, 7, 8, 6, 7, 8),
 H("Before you hire an editor, try this.", "important warning", 7, 8, 7, 3, 6, 9),
 H("This AI replaces video editors.", "unexpected consequence", 2, 9, 8, 3, 8, 9)]
p = copy.deepcopy(TPL)
for k in ("fallback_reason", "rejected_drafts", "quality_limitation", "material_update_of", "scrutiny"): p.pop(k, None)
p.update({
 "date": "2026-11-24", "slug": "motionflare-website-to-launch-video", "keys": ["motionflare", "ai-launch-video"], "topic": HEAD,
 "category": "CREATOR TECH", "topic_type": "BREAKING", "announced_at": "23 November 2026 (Product Hunt launch, 00:01 PT)", "event_date": "2026-11-23",
 "story_id": "2026-11-24-motionflare-website-to-launch-video", "company": "Motionflare (small bootstrapped team)", "generated_at": RET,
 "research_window": W, "window_expansion_reason": None, "content_format": "B",
 "why_selected": "The strongest story whose central claims could be checked on directly opened data, useful to creators and marketers.",
 "why_short": "Paste a link, get a launch video.",
 "why_beats_alternatives": "Walmart's AI-agent checkout with Meta's Muse (70.5), Nvidia's CEO reinstatement (64.5) and Alexandr Wang's superintelligence essay (57.0) rank higher on discovery but none could be checked on an opened page (and Nvidia's story is tied to politics). Motionflare's launch data and the makers' description were read directly through the Product Hunt connector.",
 "why_this_story": "A practical tool for creators and small brands: paste a site link and its makers say it builds a branded launch video. It was one of Product Hunt's top three launches on Monday (208 upvotes observed directly, the only social signal I could measure; X is blocked). It is a FALLBACK: Walmart's AI checkout story is stronger but none of its sources could be opened.",
 "fallback_reason": "Walmart's Agent Gateway with Meta's Muse (70.5) is the best story discovered, but corporate.walmart.com, Meta and every news outlet (The Verge, Unite.AI, mlq.ai, TechBuzz) are blocked by this environment's network policy, so none of its claims could be checked on an opened page; outlets also disagree on scope. Allowing those domains, or a Walmart/Meta post on a reachable host, would unblock it.",
 "evidence_confidence": "MEDIUM", "confidence": "MEDIUM",
 "verified_development": "On 23 Nov 2026 Motionflare launched on Product Hunt and ranked #3 with 208 upvotes when checked. Its makers describe a tool that turns a website URL into branded motion graphics with music and optional narration, a Film mode for live-action commercials, chat edits and 4K export, with a free option.",
 "disclosure": "Disclosure: written by Claude, an Anthropic model. Motionflare is unrelated to Anthropic. Not sponsored.",
 "research_summary": ("A research pass covered 22 candidates from 23 Nov across AI, commerce, robotics, chips, gaming and creator tools. News, company and social sites are blocked in this environment, so the strongest stories (Walmart's AI-agent checkout with Meta's Muse, Nvidia's CEO reinstatement, Alexandr Wang's essay, a Waymo storm pause) could not be checked on opened pages and were held; a Korean exam story was excluded as political. "
   "The Product Hunt connector showed Monday's launches directly: Motionflare ranked #3 with 208 upvotes. Its makers say it turns a website URL into a branded video using the site's own screenshots, logo, colors and copy, with music, optional narration, a Film mode, chat edits and 4K export, and a free option. These are the makers' claims; the tool was not tested."),
 "primary_sources": [{"label": "Product Hunt launch (23 Nov 2026)", "url": PHL}, {"label": "Product Hunt product profile", "url": PH}],
 "supporting_sources": [],
 "key_facts": ["Launched 23 Nov 2026; #3 with 208 upvotes when checked.", "Makers' description: URL to branded video with screenshots, logo, colors, copy, music, narration.",
               "Film mode, chat edits, 4K export (makers' claims).", "Free option listed."],
 "uncertainties": ["Output quality is untested; every feature is the makers' own description.", "Upvotes were still changing on launch day.",
                   "Paid pricing and limits of the free option are not stated in the listing.", "No independent review or coverage could be opened."],
 "excluded_claims": ["Team size and funding details.", "Any comparison with other video tools."],
 "context": "Product Hunt is a daily launch site where tech users upvote new products; a top-three finish is a signal of early interest, not proof of quality.",
 "script": script, "hook": hook, "hooks": hooks,
 "practical_takeaway": {"who_can_use": "Creators, marketers, founders, small businesses with a website",
   "what_it_does": "Turns a website URL into a branded video (makers' description)", "availability": "Live on its website since the 23 Nov launch",
   "price": "Free option listed; paid pricing UNKNOWN", "difference": "Uses the site's own screenshots, logo, colors and copy instead of templates (makers' claim)",
   "limitations": "Untested quality; claims are the makers'", "why_it_matters": "A launch video without an editor could save small brands time and money"},
 "audience_check": {"why_care_today": "It launched on Monday and is free to try.", "affects_life_or_work": "Anyone selling online needs videos.",
   "can_they_use_it": "Yes, there's a free option on its website.", "surprising": "It builds the video from your own site's content.",
   "demonstrable": "You can record a real test on your own site.", "clear_consequence": "Fewer barriers to making launch videos.",
   "would_share": "Creators will send it to friends launching products.", "right_audience": "Creators, marketers and founders we want to reach."},
 "script_checks": {k: {"pass": True, "why": w} for k, w in {
   "hook_clarity": "Thirteen words that state exactly what the tool does.", "factual_accuracy": "Every claim maps to c1-c4 read directly from Product Hunt, attributed to the makers.",
   "natural_delivery": "Short spoken sentences, read aloud at a normal pace.", "narrative_coherence": "One idea: link in, video out.",
   "audience_relevance": "Creators and small brands need launch videos.", "practical_takeaway": "Try it on your own site before paying an editor.",
   "ending_quality": "Ends on a useful action, not a forced question.", "no_redundancy": "Each line adds a feature or a fact.",
   "no_jargon": "No technical terms beyond 4K.", "no_unsupported_implications": "Features are attributed to the makers; no claim it beats editors."}.items()},
 "recording_guidance": {"hook_emphasis": "Lean on 'website link' and 'launch video'.", "important_pause": "A beat after 'top three launches.'",
   "final_tone": "Practical and friendly; a tip, not an ad."},
 "learning_applied": "No Instagram performance data is connected or recorded yet, so today's choice uses the documented V7/V8 model unchanged.",
 "recording": {"tone": "Practical, curious.", "opening_expression": "Hold up your phone showing your website.", "emphasis": ["website link", "your real screenshots", "free option"],
               "pauses": ["after 'top three launches'"], "pronunciation": ["Motionflare: MO-shun-flair"]},
 "visuals": ["Screen recording of your own Motionflare test", "Product Hunt leaderboard screenshot"],
 "visual_suggestions": ["Your own screen recording: paste your website URL into Motionflare and show the video it makes (creator-recorded; test before posting)",
   "Screenshot of Monday's Product Hunt leaderboard with Motionflare at #3 (credit Product Hunt)",
   "Side-by-side: your website on the left, the generated video on the right",
   "Text card: 'Makers' claims: music, narration, Film mode, 4K'"],
 "pillar": "useful_ai_tools", "format": "B", "backups": [], "backup_shortfall_reason": "Stronger stories are blocked from verification; Gauth's study agent (#2) has fewer verifiable details.",
 "editing": dict(TPL["editing"], opening_visual="Your website, then the generated video", demonstrations=["creator-recorded test only"]),
 "audience": {"stop_scroll": "A link turning into a video is instantly clear.", "watch_to_end": "Viewers wait to hear if it's free.",
   "share": "Creators share tools with friends launching products.", "save": "Useful tool, likely saved.", "comment": "People will ask for results.",
   "follow": "Practical AI tools for creators."},
 "limitations": ["News, company and social sites blocked; Product Hunt read through its connector; anthropic.com and github.com reachable.", "Tool not tested by me."],
 "instagram": {"cover_headline": "Website link to launch video",
   "caption": "Paste a website link, get a launch video. Motionflare was one of Product Hunt's top three launches on Monday. Its makers say it uses your site's real screenshots, logo, colors and copy, adds music and optional narration, and exports in up to 4K. There's a free option. Would you use it?",
   "hashtags": ["#AItools", "#ContentCreation", "#Marketing", "#ProductHunt"]},
 "linkedin": {"caption": "Motionflare (Product Hunt #3 on 23 Nov) says it turns a website URL into a branded launch video using the site's own assets.",
   "business_relevance": "Launch videos without an editor for small teams.", "discussion_prompt": "Would you ship a launch video made this way?"},
 "x": {"post": "Motionflare was one of Product Hunt's top three launches on Monday: paste a website URL and, its makers say, it builds a branded launch video from your site's own screenshots, logo and copy. Free option listed."},
 "youtube": {"title": "This AI Turns Your Website Into a Launch Video", "description": "Motionflare, Product Hunt #3 on 23 Nov 2026. Features are the makers' claims.", "keywords": ["AI video", "Motionflare", "marketing"]},
 "growth": {"watch": "Clear before/after.", "share": "Useful tool.", "follow": "Practical AI tools.", "segment": "Creators, marketers.", "underperform": "Tool stories can feel like ads."},
 "x_signals": [], "candidates": cands, "candidate_shortfall_reason": "22 credible candidates found in the 24-hour window; several have unknown dates and are rejected rather than counted.",
 "factcheck": {"story": HEAD, "date": "2026-11-24", "claims": claims},
 "access_limits": ["Product Hunt read through its connector; news and social sites blocked."], "verification": "tiered",
 "revisions": 3, "quality_limitation": "Three drafts tightened length and attribution, but a single-tool launch with only the makers' claims caps storytelling and broad relevance; it is a fallback because the stronger Walmart story could not be verified.",
 "rejected_drafts": ["Draft 1 (91 words, about 41 s): included the Film mode line; over the 40-second limit.", "Draft 2: ended 'Would you use it?' (a generic question, replaced with a practical action)."],
 "quality_v8": {"hook": 9, "clarity": 9, "storytelling": 7, "audience_relevance": 7, "information_value": 8, "natural_delivery": 9, "shareability": 8, "ending": 8},
})
p.pop("hooks_note", None)
json.dump(p, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print("ok", len(cands))
