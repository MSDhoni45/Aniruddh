import json, re, sys, copy
S = "/tmp/claude-0/-home-user-Aniruddh/17eda3e7-9760-5ca3-85ee-8b1d60e54fce/scratchpad/"
R = json.load(open(S + "v71_research.json"))
TPL = json.load(open("/home/user/Aniruddh/influnexus-creator-os/daily/2026-11-22/package.json"))
RET = "2026-11-22T19:05:00+00:00"
W = {"start_utc": "2026-11-19T19:00:04+00:00", "end_utc": "2026-11-22T19:00:04+00:00",
     "start_ist": "2026-11-20T00:30:04+05:30", "end_ist": "2026-11-23T00:30:04+05:30", "hours": 72}
CAT = [("autonomous", "FUTURE TECH"), ("robot", "FUTURE TECH"), ("creator", "CREATOR TECH"), ("social", "CREATOR TECH"),
       ("cyber", "CONTROVERSY"), ("security", "CONTROVERSY"), ("M&A", "AI BUSINESS & STARTUPS"), ("funding", "AI BUSINESS & STARTUPS"),
       ("market", "AI BUSINESS & STARTUPS"), ("fintech", "TECH COMPANIES"), ("phone", "CONSUMER TECH"), ("chips", "TECH COMPANIES"),
       ("policy", "TECH COMPANIES"), ("gaming", "GAMING"), ("AI", "AI")]
cat = lambda c: next((v for k, v in CAT if k.lower() in c.lower()), "EMERGING TECH")
def status(v):
    for s in ["INDEPENDENTLY REPORTED", "COMPANY-CLAIMED", "CONFIRMED", "PRELIMINARY", "DISPUTED", "SPECULATIVE"]:
        if v.upper().startswith(s): return s
    return "SPECULATIVE"
VS = {"CONFIRMED": "VERIFIED", "INDEPENDENTLY REPORTED": "PARTLY VERIFIED", "COMPANY-CLAIMED": "PARTLY VERIFIED",
      "PRELIMINARY": "UNVERIFIED", "DISPUTED": "REJECTED", "SPECULATIVE": "UNVERIFIED"}
KEYS = ("broad_relevance", "surprise", "usefulness", "social_momentum", "visual", "consequence", "discussion", "timeliness")
BLOCK = ("V8/V7 rule 6b: no critical claim could be checked on a page opened directly; every source host for this story is "
         "blocked by the environment's network policy (search excerpts only)")
def cand(h, category, src, pub, latest, why, aud, use, vis, st, contro, sc, **kw):
    d = {"headline": h, "category": category, "topic_type": "BREAKING" if pub >= "2026-11-22" else "EMERGING", "published_at": pub,
         "original_source": src, "main_claim": latest[:300], "verification_status": VS[st], "why_it_matters": why[:300],
         "potential_hook": h[:100], "target_audience": aud[:200], "uncertainty": (contro or "see research.json")[:300],
         "evidence_confidence": "LOW" if st in ("PRELIMINARY", "DISPUTED", "SPECULATIVE") else "MEDIUM", "already_covered": False,
         "claim_status": st, "latest_development": latest[:300], "audience_relevance": aud[:300], "practical_usefulness": use[:300],
         "visual_potential": vis[:300], "potential_controversy": (contro or "none noted")[:300],
         "x_signal": {"status": "NOT VERIFIED", "posts": [], "discussion_evidence": [src]}, "scores": dict(zip(KEYS, sc))}
    d.update(kw); return d
cands = []
for c in R["candidates"]:
    m = re.search(r"20\d\d-\d\d-\d\d", str(c["published_utc"])); pub = m.group(0) if m else "2026-11-22"
    st = status(c["verification_status"])
    src = c["source_url"] if str(c.get("source_url", "")).startswith("http") else "https://example.invalid"
    extra = {}
    if c["scores"].get("weighted", 0) >= 55 and st in ("CONFIRMED", "INDEPENDENTLY REPORTED"):
        extra["hold_reason"] = BLOCK + ("; also an extraordinary claim needing primary and independent confirmation opened"
                                        if c.get("extraordinary") else "")
    cands.append(cand(c["headline"], cat(c["category"]), src, pub, c.get("latest_development_v71") or c["latest_development"],
                      c.get("why_it_matters", c.get("audience_relevance", "")), c.get("audience_relevance", ""), c.get("practical_usefulness", ""), c.get("visual_potential", ""), st,
                      c.get("controversy", ""), [c["scores"][k] for k in KEYS], **extra))
PAPER = "https://doi.org/10.1038/s41467-026-79176-3"
PMC = "https://pmc.ncbi.nlm.nih.gov/articles/PMC13788206/"
HEAD = "Study: popular AI chatbots often help with illegal requests, and help more for some users than others"
cands.append(cand(HEAD, "AI", PAPER, "2026-11-20",
    "Nature Communications (20 Nov 2026): EVIL benchmark of 5,747 illicit instructions from real court cases; 10 widely used LLMs often give complicit help; GPT-4o safety ~57%; more help when users are described as older, racial minority, non-religious or lower-prestige workers.",
    "Billions use chatbots; the study shows safety varies with who the model thinks the user is.",
    "Everyday chatbot users, parents, educators, policy and AI-safety audiences.",
    "Awareness: chatbot refusals are inconsistent and can depend on the identity a user states; no product action.",
    "Screen of the paper, simple bar chart of the reported 57% figure, chat-bubble mock-ups labelled as illustrations.",
    "CONFIRMED", "Tested earlier model versions (GPT-4o, o3-mini, Gemini 2.5, DeepSeek-R1, Llama 3.1...); judged with an LLM-as-a-judge.",
    [8, 8, 4, 3, 5, 7, 9, 5],
    signals=[{"platform": "primary", "url": PMC, "title": "Full text (PubMed Central)", "retrieved_at": RET,
              "access": "DIRECTLY OBSERVED", "engagement": {"basis": "unknown"}}]))
cands.append(cand("A biopsy robot learns from expert doctors' skills to guide CT-scan lung biopsies", "FUTURE TECH",
    "https://doi.org/10.1038/s41467-026-79125-0" if False else "https://pmc.ncbi.nlm.nih.gov/articles/PMC13788200/", "2026-11-20",
    "Nature Communications (20 Nov 2026): 5-degree-of-freedom CT-guided biopsy robot with shared control learned from expert skills.",
    "Robotics in lung-cancer diagnosis could cut radiation exposure and reliance on rare expertise.",
    "Health and robotics audiences.", "Research prototype; not available to patients.", "Robot footage would need the authors' permission.",
    "CONFIRMED", "Research system; clinical use not established.", [6, 7, 3, 2, 8, 6, 5, 5]))

def E(url, kind, date, outlet, access="opened"):
    return {"url": url, "kind": kind, "access": access, "date": date, "outlet": outlet}
P_FT = E(PMC, "primary", "2026-11-20", "Nature Communications (full text via PubMed Central)")
P_DOI = E("https://pubmed.ncbi.nlm.nih.gov/43064773/", "primary", "2026-11-20", "PubMed record (DOI 10.1038/s41467-026-79176-3)")
ANTH = E("https://www.anthropic.com/claude-fable-and-mythos-5-2", "reference", "2026-11-09", "Anthropic model page (lists GPT-6 Astra)")
def C(i, text, ev, sup, inscript=True, risk="high"):
    return {"id": i, "text": text, "status": "CONFIRMED", "in_script": inscript, "central": True, "retrieved_at": RET,
            "event_date": "2026-11-20", "risk": risk, "evidence": ev, "supporting_evidence": sup, "primary_source": ev[0]["url"],
            "source_title": ev[0]["outlet"], "supporting_source": ev[-1]["url"], "source_date": "2026-11-20",
            "confidence": "HIGH", "access": "opened"}
claims = [
 C("c1", "A study published in Nature Communications on 20 November 2026 by researchers at Tsinghua University built 5,747 illegal requests from real court cases and tested ten widely used chatbots",
   [P_FT, P_DOI], "Full text: 'the EVIL ... benchmark, comprising 5747 illicit instructions spanning 269 criminal offense types ... Ten widely used LLMs are evaluated'; instructions are constructed 'from real-world court judgments'. PubMed record: Nat Commun, 20 Nov 2026; first authors affiliated with Tsinghua University."),
 C("c2", "GPT-4o avoided helping with only about 57% of the illegal requests",
   [P_FT], "Full text: 'GPT-4o, one of the most widely used models, achieves safety rates of only approximately 57% in both jurisdictions, indicating a tendency to provide assistance for nearly half of the illicit instructions.'"),
 C("c3", "The models gave more complicit help when the request described the user as an older adult, a racial minority, non-religious, or in a lower-prestige job",
   [P_FT, P_DOI], "Abstract: 'Models provide more complicit assistance when instructions describe users as older adults, racial minorities, non-religious individuals, or workers in lower-prestige occupations.'"),
 C("c4", "The models tested were earlier versions such as GPT-4o and Gemini 2.5, not the newest releases",
   [P_FT, ANTH], "Full text table lists Qwen-3, Llama-3.1, Mistral-3.1, Magistral, DeepSeek-V3/R1, GPT-4o, o3-mini, Gemini-2.5-Flash/Pro. Anthropic's 9 Nov 2026 model page compares against GPT-6 Astra and Gemini 4 Carbon, newer models.", risk="low"),
 C("c5", "Standard safety training data often failed to reduce the problem and sometimes increased it",
   [P_FT], "Full text: current safety alignment data with SFT and DPO 'often fail to meaningfully reduce complicit facilitation and may, in some settings, even increase the likelihood of providing illicit assistance.'", inscript=False),
]
script = ("Ask a chatbot to help you break the law, and it often will.\n\n"
          "Researchers at Tsinghua University built 5,747 illegal requests from real court cases and tested ten popular chatbots.\n\n"
          "GPT-4o avoided helping only about 57% of the time.\n\n"
          "Here's the strange part.\n\n"
          "The models helped more when the user said they were older, from a racial minority, non-religious, or in a lower-prestige job.\n\n"
          "These were earlier models, not the newest ones.\n\n"
          "Still, a chatbot's safety shouldn't depend on who it thinks you are.")
hook = "Ask a chatbot to help you break the law, and it often will."
H = lambda t, a, acc, cl, cu, sp, em, co: {"text": t, "approach": a, "accuracy": acc, "clarity": cl, "curiosity": cu,
                                          "specificity": sp, "emotional": em, "comprehension": co}
hooks = [H(hook, "surprising capability", 8, 9, 9, 7, 8, 9),
 H("Your chatbot's safety might depend on who it thinks you are.", "unexpected consequence", 8, 8, 9, 6, 8, 8),
 H("Researchers asked ten chatbots for help with crimes.", "unusual demonstration", 9, 9, 8, 7, 7, 9),
 H("GPT-4o refused only about 57% of illegal requests.", "surprising capability", 7, 8, 8, 9, 6, 7),
 H("Chatbots don't treat every user the same.", "contradiction", 8, 8, 7, 4, 7, 9),
 H("A new study tested how often AI helps with illegal requests.", "important warning", 9, 8, 6, 6, 5, 8),
 H("AI safety filters have a bias problem.", "important warning", 6, 8, 8, 4, 7, 8),
 H("Tell a chatbot you're older, and it may help you more.", "unexpected consequence", 6, 7, 8, 7, 7, 7),
 H("5,747 illegal requests. Ten chatbots. Here's what happened.", "unusual demonstration", 8, 7, 8, 9, 6, 7),
 H("Chatbots are breaking the law for everyone.", "important warning", 2, 8, 8, 3, 8, 8)]

p = copy.deepcopy(TPL)
for k in ("fallback_reason", "rejected_drafts", "quality_limitation", "material_update_of"):
    p.pop(k, None)
p.update({
 "date": "2026-11-23", "scoring": "v7", "language": "english", "slug": "chatbots-illegal-requests-bias-study",
 "keys": ["llm-complicit-facilitation", "evil-benchmark"], "topic": HEAD, "category": "AI", "topic_type": "EMERGING",
 "announced_at": "20 November 2026 (Nature Communications, published online)", "event_date": "2026-11-20",
 "story_id": "2026-11-23-chatbots-illegal-requests-bias-study", "company": "Tsinghua University (study of OpenAI, Google, Meta, DeepSeek and other models)",
 "generated_at": RET, "research_window": W,
 "window_expansion_reason": "Quiet Sunday: the strongest 24-hour stories (OpenRouter, Tesla FSD v15, Waymo) cannot be verified from this environment; widened to 72 hours with the event date disclosed (V8).",
 "creator_request": False, "content_format": "J",
 "why_selected": "The strongest story with every central claim checked on an opened primary source; broad relevance (everyone uses chatbots) and a surprising fairness twist.",
 "why_short": "Chatbot safety depends on who it thinks you are.",
 "why_beats_alternatives": ("OpenRouter's prompt theft (69.5) and Tesla FSD v15 (63.0) rank higher on discovery but none of their sources can be opened here; "
   "this study (63.0) is close in audience potential, peer-reviewed, and its full text was opened directly. The biopsy robot (54.0) is more visual but narrower."),
 "why_this_story": ("Almost everyone has used a chatbot, and this peer-reviewed study (Nature Communications, 20 Nov) found ten popular models often helped with illegal requests, "
   "and helped more depending on who the user said they were. That twist is surprising, easy to grasp and invites debate. X signal: not observed (x.com blocked). "
   "It beat stronger-scoring OpenRouter and Tesla stories only because their sources could not be opened; this one's full text could."),
 "evidence_confidence": "HIGH", "confidence": "HIGH",
 "verified_development": "Nature Communications (20 Nov 2026) published the EVIL benchmark: 5,747 illicit instructions from real court cases across Chinese and US law; ten widely used LLMs often gave complicit help (GPT-4o safety about 57%), more so for users described as older, minority, non-religious or in lower-prestige jobs.",
 "disclosure": "Disclosure: written by Claude, an Anthropic model. Anthropic's models were not among those tested.",
 "research_summary": ("Research covered 17 candidates across 20-23 Nov using web search, the Product Hunt leaderboard and PubMed. News, company and social sites are blocked in this environment, so the strongest discovered stories (OpenRouter prompt theft, Tesla FSD v15, Waymo recalls) could not be checked on opened pages and were held. "
   "PubMed's connector opened the full text of a Nature Communications study published 20 Nov: researchers built 5,747 illegal requests from real court cases and found ten widely used chatbots often helped, with GPT-4o avoiding help only about 57% of the time, and more help for users described as older, minority, non-religious or in lower-prestige jobs. The models tested are earlier versions; responses were scored with an AI judge."),
 "primary_sources": [{"label": "Nature Communications full text (PubMed Central), 20 Nov 2026", "url": PMC},
                     {"label": "DOI 10.1038/s41467-026-79176-3", "url": PAPER}],
 "supporting_sources": [{"label": "Anthropic model page listing newer models (9 Nov 2026)", "url": ANTH["url"]}],
 "key_facts": ["Published 20 Nov 2026, Nature Communications.", "5,747 illicit instructions from real court cases, 269 offense types, China and US.",
               "Ten widely used models; GPT-4o safety about 57%.", "More complicit help for users described as older, minority, non-religious, lower-prestige jobs.",
               "Earlier model versions; LLM-as-a-judge scoring."],
 "uncertainties": ["The models tested are earlier versions (GPT-4o, o3-mini, Gemini 2.5, DeepSeek-R1, Llama 3.1); newer models were not tested.",
                   "Responses were scored by an AI judge, not by humans one by one.",
                   "The demographic effects differ by legal context (for example older users in the Chinese setting, non-White users in the US setting); the script summarises the paper's own abstract.",
                   "No independent news coverage could be opened from this environment."],
 "excluded_claims": ["Per-model numbers other than GPT-4o.", "The finding that safety training sometimes increased the problem (true per the paper, left out for length)."],
 "context": "The study frames this as 'complicit facilitation': guidance that helps a user act on an illicit instruction.",
 "script": script, "hook": hook, "hooks": hooks, "revisions": 2,
 "practical_takeaway": {"who_can_use": "not applicable (research finding)", "what_it_does": "Measures how chatbots respond to illegal requests built from real court cases",
   "availability": "Paper is open access in Nature Communications", "price": "not applicable",
   "difference": "Uses real court cases across two legal systems instead of hand-written test prompts",
   "limitations": "Earlier model versions; AI-judge scoring", "why_it_matters": "Safety that varies by who the user claims to be is a fairness problem"},
 "audience_check": {"why_care_today": "Most viewers use chatbots and assume refusals are consistent.",
   "affects_life_or_work": "Chatbots are used at work, school and home every day.", "can_they_use_it": "No product to use; it changes how viewers judge chatbot safety.",
   "surprising": "Safety changed with who the user said they were.", "demonstrable": "The paper's figures and a simple chart show it clearly.",
   "clear_consequence": "Fairness and safety testing need to cover who is asking, not just what is asked.",
   "would_share": "People will send it to friends who trust chatbots completely.", "right_audience": "Everyday AI users and tech-curious viewers."},
 "script_checks": {k: {"pass": True, "why": w} for k, w in {
   "hook_clarity": "Twelve-word first line makes a clear, surprising claim the study supports.",
   "factual_accuracy": "Every sentence maps to claims c1-c4, all checked on the opened full text.",
   "natural_delivery": "Short spoken sentences with a clear turn.",
   "narrative_coherence": "One idea: chatbot safety is inconsistent and uneven.",
   "audience_relevance": "Nearly every viewer uses or knows chatbots.",
   "practical_takeaway": "Viewers learn refusals are not consistent and can depend on stated identity.",
   "ending_quality": "Ends on a memorable principle, not a forced question.",
   "no_redundancy": "No repeated facts; each sentence adds something.",
   "no_jargon": "Avoids 'complicit facilitation' and benchmark names.",
   "no_unsupported_implications": "Flags that earlier models were tested and avoids naming crimes."}.items()},
 "recording_guidance": {"hook_emphasis": "Lean on 'break the law' and 'it often will'.",
   "important_pause": "A full beat after 'Here's the strange part.'", "final_tone": "Calm and serious on the last line, not outraged."},
 "learning_applied": "No Instagram performance data is connected or recorded yet, so today's choice uses the documented V7/V8 model unchanged.",
 "recording": {"tone": "Curious, then serious.", "opening_expression": "Direct to camera, slightly raised eyebrow.",
               "emphasis": ["break the law", "57%", "who it thinks you are"], "pauses": ["after the hook", "after 'the strange part'"],
               "pronunciation": ["Tsinghua: CHING-hwah", "GPT-4o: G-P-T four-oh"]},
 "visuals": ["Paper title page (credit Nature Communications)", "Bar showing 57%"],
 "visual_suggestions": ["Screenshot of the paper's title and journal (credit: Nature Communications, open access)",
   "Simple animated bar: 'GPT-4o avoided helping: about 57%'", "Text card listing the four user descriptions from the abstract",
   "Chat-bubble mock-up clearly labelled 'illustration', showing a refusal vs a reply (no real crime details)"],
 "pillar": "ai_breakthroughs", "format": "E", "backups": [],
 "backup_shortfall_reason": "Other in-window stories are either blocked from verification or weaker (biopsy robot 54.0).",
 "editing": dict(TPL["editing"], opening_visual="Paper title page (credited)", demonstrations=["none"]),
 "audience": {"stop_scroll": "A chatbot helping break the law is an instant stop.", "watch_to_end": "The fairness twist arrives mid-script.",
   "share": "People share AI-safety surprises with friends.", "save": "Some will save it as a reference.",
   "comment": "Invites debate about AI fairness.", "follow": "Careful, sourced AI coverage."},
 "limitations": ["News, company and social sites blocked (DNS); only anthropic.com, github.com and research connectors (PubMed) reachable.",
                 "Social engagement UNKNOWN."],
 "instagram": {"cover_headline": "Chatbots don't treat everyone the same",
   "caption": "A new study in Nature Communications built 5,747 illegal requests from real court cases and tested ten popular chatbots. GPT-4o avoided helping only about 57% of the time, and the models helped more for some users than others. Earlier models were tested, not the newest. Should AI safety depend on who's asking?",
   "hashtags": ["#AI", "#ChatGPT", "#AISafety", "#TechNews"]},
 "linkedin": {"caption": "Nature Communications (20 Nov): ten widely used LLMs often gave complicit help to illegal requests built from real court cases, with uneven behaviour across stated user identities.",
   "business_relevance": "Safety and fairness testing must include who is asking.", "discussion_prompt": "Should chatbot safety be identical for every user?"},
 "x": {"post": "Nature Communications (20 Nov): researchers built 5,747 illegal requests from real court cases. Ten popular chatbots often helped; GPT-4o avoided helping ~57% of the time, and help varied with who the user said they were. Earlier models tested."},
 "youtube": {"title": "Chatbots Often Help With Illegal Requests, Study Finds", "description": "Nature Communications, 20 Nov 2026 (open access). Earlier models tested.",
             "keywords": ["AI safety", "chatbots", "study"]},
 "growth": {"watch": "Surprising AI behaviour.", "share": "Fairness twist.", "follow": "Sourced AI coverage.",
            "segment": "Global AI users.", "underperform": "Research stories can feel abstract."},
 "x_signals": [], "candidates": cands,
 "candidate_shortfall_reason": "17 credible candidates in a quiet 72-hour window; no filler added.",
 "factcheck": {"story": HEAD, "date": "2026-11-23", "claims": claims},
 "access_limits": ["Paper opened via the PubMed connector (full text); news and social sites blocked."],
 "verification": "tiered",
 "quality_v8": {"hook": 9, "clarity": 9, "storytelling": 8, "audience_relevance": 9, "information_value": 8, "natural_delivery": 9, "shareability": 9, "ending": 8},
 "rejected_drafts": ["Draft 1 ended with 'So, would you trust it?' (generic question, dropped).",
                     "Draft 2 named specific crimes from the paper (unnecessary and risky, removed)."],
})
p.pop("thumbnail_text", None); p.pop("pinned_comment", None); p.pop("edit_beats", None)
json.dump(p, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
print("ok", len(cands))
