"""Builds daily/2026-11-28/package.json (V7/V8/V9/V10) from the 24 Nov accepted package as a template.
Run: python3 daily/2026-11-28/build_package.py daily/2026-11-28/package.json"""
import json, sys, copy

BASE = "/home/user/Aniruddh/influnexus-creator-os/"
TPL = json.load(open(BASE + "daily/2026-11-24/package.json"))
W = {"start_utc": "2026-11-27T09:57:58+00:00", "end_utc": "2026-11-28T09:57:58+00:00",
     "start_ist": "2026-11-27T15:27:58+05:30", "end_ist": "2026-11-28T15:27:58+05:30", "hours": 24}
RET = "2026-11-28T10:02:00+00:00"
KEYS = ("broad_relevance", "surprise", "usefulness", "social_momentum", "visual", "consequence", "discussion", "timeliness")
VS = {"CONFIRMED": "VERIFIED", "INDEPENDENTLY REPORTED": "PARTLY VERIFIED", "COMPANY-CLAIMED": "PARTLY VERIFIED",
      "PRELIMINARY": "UNVERIFIED", "DISPUTED": "REJECTED", "SPECULATIVE": "UNVERIFIED"}

ECB = "https://www.ecb.europa.eu/press/blog/date/2026/html/ecb.blog20261127~81118f8ec0.en.html"
ECB_RSS = "https://www.ecb.europa.eu/rss/blog.html"
TM = "https://www.techmeme.com/feed.xml"
BB = "https://www.bloomberg.com/news/articles/2026-11-27/european-workers-ai-use-on-par-with-that-of-us-peers-ecb-says"
WA = "https://blog.whatsapp.com/stay-connected-on-whatsapp-when-you-travel"
NOTRUN = "not verified to RUNBOOK step 2 in this run (ranked below the verified leader; only headlines/feeds read)"

# (headline, category, published_at, source, claim_status, scores, what/why, extra)
C = [
 ("ECB data: 44% of eurozone workers use AI weekly at work; for users with no productivity gain, checking and fixing AI output is the top reason",
  "AI", "2026-11-27T10:00:00+00:00", ECB, "CONFIRMED", [8, 7, 7, 3, 6, 7, 8, 9],
  "ECB blog (27 Nov) on its Consumer Expectations Survey: 44% of employed euro area consumers used AI at least weekly at work in August 2026, ~18% daily; ~56% of users say AI raises the work they complete; for users with no gain, time to check or correct AI output is the top reason.",
  "Almost everyone with a job meets AI at work; the 'checking it eats the time' finding is relatable and useful.", {}),
 ("WhatsApp announces in-app travel data eSIMs with Jio, Verizon and others, rolling out in select countries soon",
  "CONSUMER TECH", "2026-11-26", WA, "CONFIRMED", [9, 7, 8, 3, 7, 6, 7, 6],
  "WhatsApp blog (26 Nov): buy and install a travel data eSIM inside the app; partners include Jio, Smart Axiata, Smart Communications, Verizon; select countries 'soon'.",
  "Billions of WhatsApp users travel; avoids roaming charges.",
  {"hold_reason": "announced 26 Nov 2026, before the 24-hour window (starts 27 Nov 09:58 UTC) with no new dated development inside it; widening the window is not justified because a verified in-window story (ECB) exists; also not available yet (no date, no prices)"}),
 ("OpenAI countersues Apple, alleging trade-secret theft and pressure on shared suppliers; Apple responds",
  "TECH COMPANIES", "2026-11-27T13:57:00+00:00", "https://9to5mac.com/2026/11/27/openai-countersues-apple-alleging-trade-secret-theft-and-supplier-threats/",
  "INDEPENDENTLY REPORTED", [7, 7, 2, 3, 5, 6, 8, 10], "FT/9to5Mac report an OpenAI counterclaim in Apple's trade-secret case.", "Two of the biggest consumer-AI players in court.",
  {"hold_reason": "legal story: RUNBOOK needs the filing itself (case number, counterclaim) and each party's own statement opened; the court filing was not located in this run and web search found no record of the counterclaim"}),
 ("Anthropic says Claude does not silently sabotage work; some user reports reflect 'overcaution' on long tasks",
  "AI", "2026-11-27T22:35:00+00:00", "https://www.techmeme.com/", "COMPANY-CLAIMED", [6, 7, 4, 3, 3, 5, 8, 10],
  "Anthropic response to developer complaints about Claude on long tasks.", "Developers rely on AI coding agents.",
  {"hold_reason": "company's own denial (COMPANY-CLAIMED, ineligible under V7); the underlying user reports are anecdotal; conflict of interest (this assistant is built by Anthropic)"}),
 ("Embo emerges from stealth with a $110M seed led by a16z to build robot world models trained on internet video",
  "FUTURE TECH", "2026-11-28T00:50:00+00:00", "https://embo.ai/", "COMPANY-CLAIMED", [4, 6, 2, 3, 6, 5, 5, 10],
  "Startup funding announcement for robotics world models.", "Robotics foundation models are a hot field.",
  {"hold_reason": "company announcement only (COMPANY-CLAIMED); funding amount is a financial claim needing HIGH; no product people can use"}),
 ("Samsung is reportedly giving its camera app an AI mode", "CONSUMER TECH", "2026-11-27T20:06:00+00:00",
  "https://www.engadget.com/2329765/samsung-is-reportedly-giving-its-camera-app-an-ai-mode/", "SPECULATIVE", [7, 5, 6, 3, 8, 4, 6, 10],
  "Report of an unannounced Samsung camera feature.", "Galaxy owners worldwide.", {"hold_reason": "a report of an unannounced feature (SPECULATIVE); no Samsung confirmation"}),
 ("LA school district blocks Google's AI search features", "AI", "2026-11-27T22:00:00+00:00",
  "https://www.engadget.com/2329851/la-school-district-blocks-google-ai-search-features/", "INDEPENDENTLY REPORTED", [6, 6, 4, 3, 5, 6, 7, 10],
  "Los Angeles Unified restricts Google AI search features on school accounts.", "Parents and students.", {"hold_reason": NOTRUN + "; local US policy story"}),
 ("Google Docs can now compare and work with Microsoft Word files without converting them", "AI", "2026-11-27T15:55:00+00:00",
  "https://9to5google.com/2026/11/27/google-docs-microsoft-word-compare-documents/", "INDEPENDENTLY REPORTED", [6, 3, 7, 2, 5, 3, 3, 10],
  "Workspace update for .docx files.", "Office workers.", {"hold_reason": NOTRUN}),
 ("Google says it fixed Gemini's RAM usage error in Chrome", "AI", "2026-11-27T14:35:00+00:00",
  "https://9to5google.com/2026/11/27/google-gemini-chrome-ram-usage-error/", "INDEPENDENTLY REPORTED", [5, 3, 4, 2, 3, 3, 4, 10],
  "Bug fix.", "Chrome users.", {"hold_reason": NOTRUN}),
 ("Android app developers will have to publicly post an address and phone number in 2027", "TECH COMPANIES", "2026-11-27T15:35:00+00:00",
  "https://9to5google.com/2026/11/27/android-app-developers-will-have-to-publicly-post-address-phone-number-in-2027/", "INDEPENDENTLY REPORTED", [4, 5, 3, 3, 3, 5, 6, 10],
  "Google Play verification policy.", "App developers.", {"hold_reason": NOTRUN + "; niche (developers)"}),
 ("MacWhisper now remembers speakers' voices across recordings", "AI", "2026-11-27T21:08:00+00:00",
  "https://9to5mac.com/2026/11/27/macwhisper-now-remembers-speakers-voices-across-recordings/", "COMPANY-CLAIMED", [4, 5, 6, 2, 5, 3, 3, 10],
  "App update.", "Mac users who transcribe.", {"hold_reason": "developer's own description (COMPANY-CLAIMED); niche"}),
 ("iOS 27.3 beta adds usage limits for advanced features, including Siri AI", "AI", "2026-11-27T14:50:00+00:00",
  "https://9to5mac.com/2026/11/27/ios-27-3-adds-limits-for-these-advanced-features-details-here/", "PRELIMINARY", [7, 6, 5, 3, 5, 5, 7, 10],
  "Beta code/feature limits.", "iPhone users.", {"hold_reason": "beta software (PRELIMINARY); limits may change before release"}),
 ("Purple Chinese electric minivan claims up to 559 miles on a charge", "FUTURE TECH", "2026-11-28T00:25:48+00:00",
  "https://www.theverge.com/transportation/1044706/this-purple-electric-chinese-minivan-can-go-up-to-559-miles-on-a-charge", "COMPANY-CLAIMED", [5, 6, 3, 2, 7, 3, 4, 10],
  "Range figure is the maker's (test cycle unknown).", "EV buyers.", {"hold_reason": "range is the maker's claim (COMPANY-CLAIMED); test cycle not stated"}),
 ("Hackers reportedly infiltrated the US Air Force's cloud systems", "CONTROVERSY", "2026-11-27T16:55:00+00:00",
  "https://www.engadget.com/2329586/hackers-reportedly-infiltrated-the-air-force-cloud-systems/", "SPECULATIVE", [4, 6, 1, 3, 3, 6, 6, 10],
  "Security report.", "General.", {"hold_reason": "a report without official confirmation; military/government security story"}),
 ("Restricted Nvidia chips were installed at a Chinese data center linked to Alice Huang", "CONTROVERSY", "2026-11-27T19:45:00+00:00",
  "https://www.engadget.com/2329748/restricted-nvidia-chips-were-installed-at-a-chinese-data-center-linked-to-alice-huang/", "SPECULATIVE", [4, 6, 1, 3, 3, 6, 7, 10],
  "Export-control report.", "General.", {"rejected": "geopolitics/export-control politics and a personal allegation (excluded by V8 positioning)"}),
 ("Apple faces a potential $80 million fine and App Store changes in Chile", "TECH COMPANIES", "2026-11-27T20:31:00+00:00",
  "https://9to5mac.com/2026/11/27/apple-faces-potential-80-million-fine-and-app-store-overhaul-in-chile/", "INDEPENDENTLY REPORTED", [4, 4, 2, 2, 3, 4, 5, 10],
  "Regulatory proposal.", "Chilean iPhone users.", {"hold_reason": NOTRUN + "; regulatory/legal, a proposed fine"}),
 ("SAP confirms a cybersecurity incident; report says hackers obtained staff tokens and touched source code on GitHub", "CONTROVERSY", "2026-11-27T11:35:00+00:00",
  "https://www.techmeme.com/", "INDEPENDENTLY REPORTED", [4, 5, 2, 3, 3, 6, 5, 10], "Enterprise security incident.", "Businesses.",
  {"hold_reason": NOTRUN + "; security claims need SAP's advisory opened"}),
 ("Verizon reportedly in talks to buy fiber broadband operator Fidium for about $6B", "TECH COMPANIES", "2026-11-27T13:50:00+00:00",
  "https://www.techmeme.com/", "SPECULATIVE", [3, 3, 2, 2, 2, 4, 3, 10], "Unconfirmed deal talks.", "US broadband users.",
  {"hold_reason": "anonymous-source deal talks (SPECULATIVE); billion-dollar figure needs HIGH"}),
 ("Trustly raises $60M from Nordic Capital and others", "AI BUSINESS & STARTUPS", "2026-11-28T01:45:00+00:00", "https://www.techmeme.com/",
  "INDEPENDENTLY REPORTED", [2, 2, 2, 2, 2, 3, 2, 10], "Fintech funding.", "Payments industry.", {"hold_reason": NOTRUN + "; low audience interest"}),
 ("Google Pixel prepares a 'Priority Notifications' feature", "CONSUMER TECH", "2026-11-27T16:30:00+00:00",
  "https://9to5google.com/2026/11/27/google-pixel-prepares-new-priority-notifications-feature-heres-what-it-will-do/", "PRELIMINARY", [5, 5, 5, 2, 4, 3, 4, 10],
  "Found in code; unreleased.", "Pixel owners.", {"hold_reason": "unreleased feature found in code (PRELIMINARY)"}),
 ("WhatsApp tests view-once text messages on iOS beta", "CONSUMER TECH", "2026-11-27T22:30:00+00:00",
  "https://9to5mac.com/2026/11/27/whatsapp-announces-travel-esims-tests-view-once-texts-and-a-cleaner-interface/", "PRELIMINARY", [7, 5, 5, 3, 6, 3, 6, 10],
  "Beta test reported by WABetaInfo.", "WhatsApp users.", {"hold_reason": "TestFlight beta test (PRELIMINARY); may not ship"}),
 ("A Product(RED) HomePod mini 2 seemingly surfaces ahead of a rumored announcement", "CONSUMER TECH", "2026-11-28T03:07:04+00:00",
  "https://9to5mac.com/2026/11/27/productred-homepod-mini-2-seemingly-surfaces-ahead-of-rumored-announcement/", "SPECULATIVE", [4, 3, 2, 2, 5, 2, 4, 10],
  "Rumour.", "Apple fans.", {"hold_reason": "rumour (SPECULATIVE)"}),
 ("Three new iPhones are expected early next year", "CONSUMER TECH", "2026-11-27T17:57:23+00:00",
  "https://9to5mac.com/2026/11/27/three-new-iphones-will-launch-early-next-year-heres-whats-coming/", "SPECULATIVE", [6, 3, 3, 3, 4, 3, 6, 10],
  "Rumour roundup.", "iPhone buyers.", {"hold_reason": "rumour (SPECULATIVE)"}),
 ("An ER doctor became a hospital's first clinical AI engineer", "AI", "2026-11-27T14:00:01+00:00", "https://spectrum.ieee.org/clinical-ai-engineer-dinesh-rai",
  "INDEPENDENTLY REPORTED", [4, 5, 3, 2, 4, 4, 4, 8], "IEEE Spectrum profile.", "Healthcare workers.", {"hold_reason": NOTRUN + "; profile feature, not a development"}),
 ("Cutting-edge prosthetics help researchers probe the human mind", "FUTURE TECH", "2026-11-27T10:00:00+00:00",
  "https://www.technologyreview.com/2026/11/27/1149946/cutting-edge-prosthetics-allow-researchers-to-probe-the-human-mind/", "INDEPENDENTLY REPORTED", [4, 7, 2, 2, 7, 4, 5, 7],
  "MIT Technology Review feature.", "Science-curious viewers.", {"hold_reason": NOTRUN + "; feature on research, no single dated development"}),
 ("Meross presence sensor splits a room into three zones for Apple Home", "CONSUMER TECH", "2026-11-27T19:30:00+00:00", "https://9to5mac.com/2026/11/27/meross-ms605/",
  "COMPANY-CLAIMED", [3, 4, 4, 2, 5, 2, 2, 9], "Smart-home product.", "HomeKit users.", {"hold_reason": "product claims (COMPANY-CLAIMED); niche"}),
 ("Allstate has suffered a multiday website and app outage since 23 November", "CONTROVERSY", "2026-11-27T18:30:00+00:00", "https://www.techmeme.com/",
  "INDEPENDENTLY REPORTED", [3, 4, 2, 2, 2, 4, 4, 8], "Outage; cause not disclosed.", "Allstate customers.", {"hold_reason": NOTRUN + "; cause unknown"}),
]

cands = []
for h, cat, pub, src, st, sc, what, why, extra in C:
    d = {"headline": h, "category": cat, "topic_type": "BREAKING", "published_at": pub, "original_source": src, "main_claim": what[:300],
         "verification_status": VS[st], "why_it_matters": why, "potential_hook": h[:100], "target_audience": why,
         "uncertainty": extra.get("hold_reason") or extra.get("rejected") or "see research_pool.json",
         "evidence_confidence": "HIGH" if st == "CONFIRMED" else "LOW" if st in ("PRELIMINARY", "DISPUTED", "SPECULATIVE") else "MEDIUM",
         "already_covered": False, "claim_status": st, "latest_development": what[:300], "audience_relevance": why,
         "practical_usefulness": what[:300], "visual_potential": "headline/screenshot graphics", "potential_controversy": "none noted",
         "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": [src]},
         "scores": dict(zip(KEYS, sc))}
    d.update(extra)
    cands.append(d)
w = cands[0]
w.update({"visual_potential": "ECB chart screenshots (credited), creator to camera, simple bar graphics of 44% / 18% / 56%",
          "potential_controversy": "Europe-only data; CES and US (Gallup) surveys are not harmonised, so cross-country comparisons are indicative only",
          "uncertainty": "Self-reported survey answers; figures are perceptions, not measured productivity",
          "signals": [{"platform": "primary", "url": ECB, "title": "ECB Blog: AI, jobs and prices: what euro area consumers expect", "retrieved_at": RET,
                       "access": "DIRECTLY OBSERVED", "engagement": {"basis": "unknown"}},
                      {"platform": "news", "url": TM, "title": "Techmeme headline (27 Nov 2026 13:15 EST) linking Bloomberg's report of the ECB survey", "retrieved_at": RET,
                       "access": "DIRECTLY OBSERVED", "engagement": {"basis": "unknown"}}],
          "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": [TM]}})

def E(url, date, outlet, kind="primary"):
    return {"url": url, "kind": kind, "access": "opened", "date": date, "outlet": outlet}
EV_B = E(ECB, "2026-11-27", "ECB Blog: AI, jobs and prices: what euro area consumers expect (Georgarakos, Kenny, Meyer)")
EV_R = E(ECB_RSS, "2026-11-27", "ECB Blog RSS (pubDate Fri 27 Nov 2026 11:00 CET)")
def CL(i, text, sup, ev, risk="high", sattr=None):
    c = {"id": i, "text": text, "status": "CONFIRMED", "in_script": True, "central": True, "retrieved_at": RET, "event_date": "2026-11-27",
         "risk": risk, "evidence": ev, "supporting_evidence": sup, "primary_source": ECB, "source_title": EV_B["outlet"],
         "supporting_source": ev[-1]["url"], "source_date": "2026-11-27", "confidence": "HIGH", "access": "opened",
         "quote": False, "wording_verified": True}
    if sattr:
        c["attribution"], c["script_attribution"] = "ECB economists' blog on the ECB Consumer Expectations Survey", sattr
    return c
claims = [
 CL("c1", "On Friday 27 November 2026 the European Central Bank published new data from its Consumer Expectations Survey on AI use at work (ECB Blog)",
    "ECB Blog 'AI, jobs and prices: what euro area consumers expect', RSS pubDate Fri, 27 Nov 2026 11:00 CET; 'New evidence from the ECB's Consumer Expectations Survey sheds light on consumers' views on jobs, prices and AI regulation.'",
    [EV_B, EV_R], sattr="new data from the European Central Bank"),
 CL("c2", "In August 2026, 44% of employed euro area consumers reported using AI at least weekly at work, and around 18% used it daily",
    "'In August 2026, 44% of employed euro area consumers reported using AI at least weekly at work, and around 18% used it daily.'",
    [EV_B, {"url": BB, "kind": "news", "access": "secondary", "date": "2026-11-27", "outlet": "Bloomberg (headline via Techmeme; page 403)"}], sattr="said they used"),
 CL("c3", "Around 56% of workplace AI users say AI increases the amount of work they complete",
    "'Around 56% say that AI increases the amount of work they complete, while 47% report producing higher-quality output.'",
    [EV_B], sattr="said"),
 CL("c4", "Among AI users who reported no increase in output, the most commonly cited reason was the time needed to check or correct AI-generated results",
    "'Among users who reported no increase in output, the most commonly cited reason is the time needed to check or correct AI-generated results (Chart 2, panel b).'",
    [EV_B], sattr="the most common reason"),
]

script = ("Nearly half of workers in the eurozone now use AI every week. But not all of them are getting more done.\n\n"
          "That's new data from the European Central Bank, released Friday.\n\n"
          "In August, 44 percent of working people there said they used AI at work weekly. "
          "About 18 percent used it daily.\n\n"
          "Around 56 percent of users said it helps them get more done.\n\n"
          "But for those who saw no gain, the top reason was the time spent checking and fixing the AI's work.\n\n"
          "The real skill isn't using AI. It's knowing when to trust it.")
hook = "Nearly half of workers in the eurozone now use AI every week."
H = lambda t, a, acc, cl, cu, sp, em, co: {"text": t, "approach": a, "accuracy": acc, "clarity": cl, "curiosity": cu, "specificity": sp,
                                          "emotional": em, "comprehension": co}
hooks = [H(hook, "surprising capability", 9, 9, 8, 8, 7, 9),
 H("The biggest thing slowing down AI at work? Checking its answers.", "contradiction", 8, 9, 9, 7, 7, 9),
 H("Almost half of European workers use AI weekly. Many still aren't faster.", "unexpected consequence", 8, 8, 8, 8, 6, 8),
 H("If AI isn't saving you time, you're not alone.", "practical discovery", 7, 9, 8, 5, 8, 9),
 H("Europe's central bank just asked workers how AI is going.", "major product reveal", 9, 8, 7, 6, 5, 8),
 H("More people in the eurozone use AI daily than in the US.", "contradiction", 6, 8, 8, 7, 6, 8),
 H("Here's why AI isn't making everyone more productive.", "important warning", 7, 8, 8, 4, 6, 9),
 H("Using AI at work? Watch how much time you spend fixing it.", "important warning", 8, 9, 7, 6, 7, 9),
 H("One in five eurozone workers now uses AI every single day.", "surprising capability", 7, 9, 7, 8, 6, 9),
 H("AI was supposed to save time. For many workers, checking it costs time.", "unexpected consequence", 8, 8, 8, 6, 7, 8),
 H("AI is replacing hard work for half of Europe.", "unexpected consequence", 3, 8, 8, 4, 8, 8)]

p = copy.deepcopy(TPL)
for k in ("fallback_reason", "rejected_drafts", "quality_limitation", "material_update_of", "scrutiny", "creator_request", "verification_report"):
    p.pop(k, None)
HEAD = C[0][0]
p.update({
 "date": "2026-11-28", "slug": "ecb-ai-at-work-checking-time", "keys": ["ecb-ai-at-work-survey", "ai-productivity-checking-output"], "topic": HEAD,
 "category": "AI", "topic_type": "BREAKING", "announced_at": "27 November 2026, 11:00 CET (ECB Blog)", "event_date": "2026-11-27",
 "story_id": "2026-11-28-ecb-ai-at-work-checking-time", "company": "European Central Bank (ECB)", "generated_at": RET,
 "research_window": W, "window_expansion_reason": None, "content_format": "I",
 "why_selected": "The strongest verified in-window story: new official survey data on AI at work that almost every viewer with a job can relate to, read directly on the ECB's own site.",
 "why_short": "Half of eurozone workers use AI weekly; checking its output is why some see no gain.",
 "why_beats_alternatives": ("WhatsApp's travel eSIM (68.0) scores slightly higher but was announced on 26 Nov, outside the 24-hour window, and is not available yet. "
   "OpenAI's countersuit against Apple (56.0) needs the court filing, which was not found. Samsung's camera AI mode and iOS 27.3 Siri limits are reports or betas. "
   "The ECB data (67.0) is in the window, official, opened directly and useful to anyone who uses AI at work."),
 "why_this_story": ("Most viewers use AI at work or will soon. New ECB data says 44% of eurozone workers use it weekly, and the top reason some see no gain "
   "is the time spent checking and fixing its output, a useful, relatable takeaway. Social signal: X metrics not verified; a Techmeme headline was the only "
   "discussion observed. It beat WhatsApp's eSIM news, which fell outside the window."),
 "evidence_confidence": "HIGH", "confidence": "HIGH",
 "verified_development": ("On 27 Nov 2026 an ECB Blog post by ECB economists, based on the ECB Consumer Expectations Survey, reported that in August 2026 44% of "
   "employed euro area consumers used AI at least weekly at work and around 18% daily; around 56% of workplace AI users said AI increases the work they complete; "
   "and among users with no increase in output the most cited reason was the time needed to check or correct AI-generated results."),
 "disclosure": "Disclosure: written by Claude, an Anthropic model. The story is about AI tools in general; no specific company's product is named. Not sponsored.",
 "research_summary": ("A sweep of the 24-hour window (27-28 Nov) read RSS feeds and pages from TechCrunch, The Verge, Ars Technica, Engadget, 9to5Google, 9to5Mac, "
   "Wired, MIT Technology Review, IEEE Spectrum, Techmeme, Google, OpenAI and the ECB, and found 27 candidates; Black Friday deals dominated. "
   "The leader, an ECB Blog post of 27 Nov on its Consumer Expectations Survey, was opened directly: 44% of employed euro area consumers used AI at least "
   "weekly at work in August 2026, about 18% daily; around 56% of users say it raises the work they complete; for users with no gain, checking or correcting "
   "AI output is the most cited reason. WhatsApp's travel eSIM was announced on 26 Nov, outside the window, and held."),
 "primary_sources": [{"label": "ECB Blog: AI, jobs and prices: what euro area consumers expect (27 Nov 2026)", "url": ECB},
                     {"label": "ECB Blog RSS feed (publication time)", "url": ECB_RSS}],
 "supporting_sources": [{"label": "Bloomberg (Alexander Weber), 27 Nov 2026: European workers' AI use on par with US peers, ECB says (paywalled, HTTP 403 here; headline seen via Techmeme)", "url": BB},
                        {"label": "Techmeme feed item linking the Bloomberg report (27 Nov 2026)", "url": TM}],
 "key_facts": ["Published 27 Nov 2026 on the ECB Blog (authors: Georgarakos, Kenny, Meyer), based on the ECB Consumer Expectations Survey.",
               "August 2026: 44% of employed euro area consumers used AI at least weekly at work; around 18% daily.",
               "About 56% of workplace AI users say AI increases the amount of work they complete; 47% say quality improved.",
               "Among users with no output gain, the most cited reason is time needed to check or correct AI-generated results."],
 "uncertainties": ["Survey answers are self-reported perceptions, not measured productivity.",
                   "The 56% figure comes from the June 2026 survey wave; weekly/daily use from August 2026.",
                   "ECB blog views are the authors', not necessarily the ECB's.",
                   "Eurozone and US figures come from different surveys (CES vs Gallup), so the comparison is left out."],
 "excluded_claims": ["Euro area daily AI use is higher than in the US (surveys not harmonised; the blog itself says comparisons are indicative).",
                     "Investment gap figures (40% vs 12%) and job-loss expectations (not needed for the one idea).",
                     "Any claim that AI makes workers slower overall (not what the data says)."],
 "context": "The ECB's Consumer Expectations Survey asks about 20,000 people in 11 euro area countries each month (background; not in the script).",
 "script": script, "hook": hook, "hooks": hooks, "revisions": 3,
 "practical_takeaway": {"who_can_use": "Anyone who uses AI tools at work", "what_it_does": "Shows how often eurozone workers use AI and why some see no productivity gain",
   "availability": "not applicable (survey data)", "price": "not applicable",
   "difference": "Official, large survey data rather than a vendor's claim",
   "limitations": "Self-reported, euro area only; perceived gains, not measured output",
   "why_it_matters": "Checking and fixing AI output is the hidden cost that decides whether AI actually saves you time"},
 "audience_check": {"why_care_today": "The data was published on Friday and most viewers use AI at work.",
   "affects_life_or_work": "It is about how AI changes everyday work for ordinary employees.",
   "can_they_use_it": "Yes, they can audit how much time they spend checking AI output.",
   "surprising": "The top reason for no gain is the time spent fixing AI's work.",
   "demonstrable": "Simple charts from the ECB post and the creator's own example can show it.",
   "clear_consequence": "Saving time with AI depends on how much checking a task needs.",
   "would_share": "People will send it to colleagues who complain about fixing AI output.",
   "right_audience": "Working professionals and students who use AI tools daily."},
 "script_checks": {k: {"pass": True, "why": v} for k, v in {
   "hook_clarity": "One clear stat-led line a viewer understands instantly.",
   "factual_accuracy": "Every number maps to c1-c4, read directly on the ECB Blog.",
   "natural_delivery": "Short spoken sentences; numbers said as words a person would say.",
   "narrative_coherence": "One idea: lots of AI use, and checking is the hidden cost.",
   "audience_relevance": "Anyone with a job meets AI at work.",
   "practical_takeaway": "Know when to trust AI output and when it costs you time.",
   "ending_quality": "Ends on a memorable takeaway, not a forced question.",
   "no_redundancy": "Each sentence adds a new fact or the turn.",
   "no_jargon": "No technical terms; 'eurozone' is explained by context.",
   "no_unsupported_implications": "Does not claim AI slows workers overall; only the reason given by those with no gain."}.items()},
 "recording_guidance": {"hook_emphasis": "Lean on 'nearly half' and 'every week'.", "important_pause": "A beat after 'the most common reason was simple.'",
   "final_tone": "Calm and knowing; a practical tip, not a warning."},
 "learning_applied": "No Instagram performance data is connected or recorded yet, so today's choice uses the documented V7/V8 model unchanged.",
 "recording": {"tone": "Curious, conversational, practical.", "opening_expression": "Slight nod on 'every week', then a knowing look on 'not all of them'.",
   "emphasis": ["nearly half", "44 percent", "every day", "checking and fixing", "when to trust it"],
   "pauses": ["after 'getting more done.'", "after 'was simple.'"],
   "pronunciation": ["eurozone: YOOR-oh-zone", "European Central Bank: say it in full, no acronym"]},
 "visuals": ["ECB Blog headline and Chart 2 (credited)", "Simple bar graphic: 44% weekly, 18% daily, 56% more work"],
 "visual_suggestions": ["Screenshot of the ECB Blog post headline 'AI, jobs and prices: what euro area consumers expect' dated 27 Nov 2026 (credit ECB)",
   "Own animated bar graphic: 44% weekly, 18% daily (August 2026, ECB survey)",
   "Screenshot of ECB Chart 2 panel b (reasons for no gain) with 'check or correct' highlighted (credit ECB)",
   "Creator-recorded screen: you re-reading and correcting an AI draft on your own laptop (clearly your own example)"],
 "pillar": "ai_breakthroughs", "format": "E", "backups": [],
 "backup_shortfall_reason": "No other in-window candidate was verified to the same standard; WhatsApp's eSIM is outside the window.",
 "editing": {"opening_visual": "Creator to camera, '44%' graphic pops in", "key_moments": ["44% weekly / 18% daily", "checking and fixing"],
   "broll": ["ECB Blog screenshots", "creator's own screen correcting an AI draft"], "on_screen_text": ["44% USE AI WEEKLY", "18% DAILY", "TOP REASON: CHECKING & FIXING"],
   "demonstrations": ["creator-recorded own example only"], "stats": ["44%", "18%", "56%"], "rhythm": "One fact per shot, pause on the turn",
   "caption_emphasis": ["nearly half", "checking and fixing", "trust"], "sound": "Light curious bed"},
 "audience": {"stop_scroll": "'Nearly half of workers' plus a twist makes people stop.", "watch_to_end": "Viewers want to hear why AI isn't helping some people.",
   "share": "People will send it to coworkers who fix AI drafts all day.", "save": "The trust-versus-check tip is worth keeping.",
   "comment": "People will share whether AI actually saves them time.", "follow": "Clear, sourced takes on AI in everyday work."},
 "limitations": ["Source audit: all source groups reachable today; x.com opens but post metrics were not read, so the X signal is NOT VERIFIED.",
                 "Only the leader was verified to RUNBOOK step 2; other candidates are from feed headlines.",
                 "Bloomberg's report (27 Nov) returned HTTP 403 (paywall); its headline was read via Techmeme's feed and several AI-news aggregators repeat the figures (search excerpts only)."],
 "instagram": {"cover_headline": "Why AI isn't saving everyone time",
   "caption": "Nearly half of workers in the eurozone now use AI every week, says new data from the European Central Bank. About 18% use it daily. But for people who saw no gain, the top reason was the time spent checking and fixing AI output. Does AI actually save you time?",
   "hashtags": ["#AI", "#FutureOfWork", "#Productivity", "#AItools"]},
 "linkedin": {"caption": "ECB data (27 Nov): 44% of employed euro area consumers used AI at least weekly at work in August 2026, about 18% daily. For users with no output gain, the most cited reason was time spent checking or correcting AI output.",
   "business_relevance": "Productivity gains depend on how much verification a task needs.", "discussion_prompt": "Where does checking AI output eat your time?"},
 "x": {"post": "New ECB data: 44% of eurozone workers used AI at least weekly at work in August, ~18% daily. For those who saw no gain, the top reason was time spent checking and fixing AI output."},
 "youtube": {"title": "Why AI Isn't Saving Everyone Time", "description": "Source: ECB Blog, 27 Nov 2026, based on the ECB Consumer Expectations Survey.",
   "keywords": ["AI at work", "productivity", "ECB survey"]},
 "growth": {"watch": "A stat then a twist.", "share": "Relatable to anyone using AI at work.", "follow": "Sourced AI-at-work takes.",
   "segment": "Working professionals, students.", "underperform": "Survey stories can feel dry without a personal example."},
 "x_signals": [], "candidates": cands,
 "candidate_shortfall_reason": "27 candidates found in the 24-hour window; Black Friday deal posts were excluded as non-news, and most others are reports, betas or rumours.",
 "factcheck": {"story": HEAD, "date": "2026-11-28", "claims": claims},
 "access_limits": ["ECB Blog and RSS opened directly; x.com metrics not read."], "verification": "tiered",
 "quality_v8": {"hook": 9, "clarity": 9, "storytelling": 8, "audience_relevance": 9, "information_value": 9, "natural_delivery": 9, "shareability": 9, "ending": 8},
 "rejected_drafts": ["Draft 1 said 'workers in Europe' (the data covers the euro area only) and was corrected to 'eurozone'.",
                     "Draft 2 claimed eurozone workers use AI daily more than Americans; cut because the surveys are not harmonised.",
                     "Draft 3 ended 'Does AI save you time?' (generic); replaced with the trust takeaway."],
})

# ---- V9/V10 production fields (storyboard timings from the tool's own pace estimate, scaled to the full estimate) ----
sys.path.insert(0, BASE + "src")
from creatoros.scripts import lint
from creatoros.editing.align import script_sentences
sents = script_sentences(script)
durs = [lint.estimate_seconds(x, "v9")["seconds"] for x in sents]
total = lint.estimate_seconds(script, "v9")["seconds"]
k = total / sum(durs)
ROWS = [
 ("talking-head", "Creator to camera, chest-up, confident", "NEARLY HALF USE AI EVERY WEEK", "'44%' counter pops beside the creator", "Cut", "Soft pop", "Creator footage (own)"),
 ("talking-head", "Creator to camera, small head tilt", "BUT NOT ALL ARE GETTING MORE DONE", "Text strike-through on 'more done'", "Punch-in 106%", "Record-scratch light", "Creator footage (own)"),
 ("screen", "Screenshot of the ECB Blog post headline 'AI, jobs and prices: what euro area consumers expect' with the 27 Nov 2026 date", "EUROPEAN CENTRAL BANK · 27 NOV", "Slow push-in; highlight the date", "Slide left", "Paper/click", "ECB website screenshot, credit 'Source: ECB Blog' on screen (confirm ECB reuse terms)"),
 ("graphic", "Own animated bar: 44% weekly (August 2026, ECB Consumer Expectations Survey)", "44% USE AI AT WORK WEEKLY", "Bar grows to 44%", "Cut", "Tick", "Own graphics (data: ECB)"),
 ("graphic", "Same graphic, second bar: about 18% daily", "~18% EVERY DAY", "Second bar grows to 18%", "Cut", "Tick", "Own graphics (data: ECB)"),
 ("split", "Left: creator; right: own graphic '56% get more done'", "56% SAY: MORE WORK DONE", "Check-mark animation", "Cross-dissolve", "Soft chime", "Creator footage (own) + own graphics (data: ECB)"),
 ("b-roll", "Creator-recorded screen: your own laptop, re-reading and correcting an AI-written draft (your own example, labelled as such); then ECB Chart 2 panel b with 'check or correct' highlighted", "TOP REASON: CHECKING & FIXING AI'S WORK", "Highlight box on the chart bar", "Zoom-through", "Typing + delete sounds", "Own screen recording; ECB chart screenshot, credit ECB"),
 ("talking-head", "Creator to camera, slower, lean in", "THE REAL SKILL ISN'T USING AI", "Music dips", "Cut", "None (let it breathe)", "Creator footage (own)"),
 ("talking-head", "Creator to camera, small smile", "IT'S KNOWING WHEN TO TRUST IT", "Title card hold 1 s", "Cut to end card", "Soft resolve", "Creator footage (own)"),
]
assert len(ROWS) == len(sents), (len(ROWS), len(sents))
sb, t = [], 0.0
for (tr, foot, ost, mg, trans, sfx, lic), sent, d in zip(ROWS, sents, durs):
    e = round(t + d * k, 1)
    sb.append({"line": sent, "start_s": round(t, 1), "end_s": e, "treatment": tr, "footage": foot, "on_screen_text": ost, "motion_graphics": mg,
               "transition": trans, "sfx": sfx, "source_licensing": lic})
    t = e
p["storyboard"] = sb
p["recording_v9"] = {"opening_expression": "Open with a slight nod and raised eyebrows on 'every week', then a knowing half-smile on 'not all of them'.",
  "emphasis": ["nearly half", "every week", "44 percent", "daily", "checking and fixing", "when to trust it"],
  "pauses": ["after 'getting more done.'", "before 'But for those who saw no gain'", "before the last line"],
  "pronunciation": ["eurozone: YOOR-oh-zone", "European Central Bank: say it in full", "44 percent: forty-four percent"],
  "framing": "Vertical 9:16, chest-up medium close-up, eyes on the upper third; leave headroom for on-screen numbers; plain background.",
  "pace": "Natural and clear (about 140 words per minute); slow slightly on the 'checking and fixing' line.",
  "gestures": "Open palm on 'nearly half'; small shrug on 'not all of them'; tap the desk or mime typing on 'checking and fixing'; point to camera on 'when to trust it'."}
p["music"] = {"style": "Light, curious lo-fi/electronic bed, about 95-105 BPM, no lyrics",
  "track_suggestion": "Search your licensed library for 'curious minimal tech lo-fi' (for example YouTube Audio Library, free; or Epidemic Sound / Artlist if you hold a subscription). No specific track is claimed as licensed.",
  "licensing": "Use only a track your account is licensed to use on Instagram; keep the licence record",
  "opening_cue": "Bed starts under the first word, low", "beat_changes": ["Small lift on the numbers (44%, 18%, 56%)", "Dip before 'But for those who saw no gain'", "Near-silence on 'The real skill'"],
  "sfx": ["Soft pop on the hook number", "Ticks as bars grow", "Typing/delete on the checking line", "Soft resolve at the end"],
  "dialogue_music_balance": "Dialogue normalised to about -14 LUFS; music bed around -27 dB under speech, up to about -20 dB in gaps",
  "ending_cue": "Clean resolve on 'trust it', 1 s tail"}
p["distribution"] = {"cover_headline": "Why AI isn't saving everyone time",
  "thumbnail_concept": "Creator looking at a laptop with a raised eyebrow; bold '44% USE AI WEEKLY' and small 'but...'",
  "posting_angle": "A relatable, sourced take on AI at work: lots of people use it, and checking its output is the hidden cost",
  "engagement_question": "Does AI actually save you time, or do you spend it fixing the output?"}
p["production_handoff"] = {"pipeline": ["GitHub editing tools", "saved references", "creative analysis", "transcript-based storyboard", "editing", "audio restoration", "music", "color grading", "4K rendering", "QC"],
  "output_resolution": "2160x3840",
  "audio": "Denoise and de-reverb dialogue, gentle compression, normalise to -14 LUFS with -1.5 dB true peak; tighten pauses over 0.45 s without clipping words",
  "captions": "Word-level burned-in captions from captions.txt, 2-5 words per line; highlight the numbers and 'checking and fixing'; keep clear of the bottom UI area",
  "broll_list": ["ECB Blog post headline and date (screenshot, credit ECB)", "ECB Chart 2 panel b: reasons for no gain (screenshot, credit ECB)",
                 "Own graphics: 44% weekly, 18% daily, 56% more work bars (data: ECB)", "Creator's own screen recording correcting an AI draft (own example)"],
  "notes": "Do not use unrelated stock footage or invent product demos; credit the ECB on screen for screenshots and data."}
p["editing"]["key_moments"] = ["44% weekly / 18% daily", "checking and fixing"]
p.pop("hooks_note", None)
json.dump(p, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print("ok", len(cands))
