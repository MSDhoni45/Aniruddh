# Creator Intelligence Database: AI & technology short-form

Checked 2026-11-19. Companion data file: `creators_db.csv` (61 rows, 20 columns). This is desk research from web-search results only. **No video was watched and no platform page was opened.**

## 1. Access limits (read first)

- The sandbox could not open instagram.com, youtube.com, x.com, tiktok.com, linkedin.com or most other sites. Direct fetching was not used.
- **WebSearch was the only tool.** Each account URL in the CSV appeared as a result URL in a search (most came from domain-restricted searches on youtube.com, instagram.com, tiktok.com, x.com and linkedin.com). The pages behind those URLs were not opened. Everything about an account comes from the search engine's title, snippet or summary.
- **Audience numbers are second-hand.** Each one is either (a) a figure the search summary attributed to the platform page itself ("profile listing as summarised by search; undated"), (b) a THIRD-PARTY tracker (vidIQ, Socialpruf, SponsorRadar, OutlierKit), or (c) SELF-REPORTED by the creator in a bio or post. None was read live. Most are undated. A May 2026 Meta purge of inactive accounts (reported in prior research) may make older Instagram figures too high.
- Some audience and storytelling entries come from the earlier session's research in `creator_benchmarks.md` (searched 2026-11-18). These are labelled "prior session" in the CSV. They were not searched again today.
- **Region and language** are filled in only where a source states them or the information is basic public knowledge (for example, "UK" for Mrwhosetheboss). Language is UNKNOWN for most Indian creators: no source said whether they post in English, Hindi or Hinglish.
- **What `short_form_active = yes` means:** a search result showed short-form content from that creator, such as a TikTok account or video, a YouTube Shorts URL or channel, a description of reels, or an Instagram feed run as a reels account. It does **not** confirm how often they posted in 2026. UNKNOWN means no short-form evidence was surfaced. It does not mean the creator has no short-form presence.
- Searches used this session: **75**, all in standard mode.

## 2. Counts

| Status | Count | Meaning |
|---|---|---|
| VERIFIED | **58** | A search result showed the creator's own account URL (YouTube, TikTok, Instagram, X or LinkedIn), or for Ethan Mollick, his own site. |
| PARTIAL | **3** | Tanmay Bhat: only the shared Overpowered channel was surfaced. The AntimVirat and Katha.Ai: no account URL. These rows are excluded from the 58. |

Audience field coverage across the 58 verified rows:
- 38 have a number. Some of these are stale or approximate, such as "500K+ (stale)" and "nearly 5M".
- 20 are UNKNOWN.
- 13 of the 38 numbers are SELF-REPORTED or come from claims in third-party video descriptions.

Storytelling field: 18 rows cite a source. The other 43 are NOT OBSERVED.

Notes on specific rows:
- Matt Wolfe's YouTube count is UNKNOWN this session. The prior-session figure of about 1.02M was recorded without a URL.
- Matthew Berman and Wes Roth have no dated count.
- AI Explained is verified through its X account only. The host's name is not confirmed.

## 3. Summary by focus area and region (verified rows only)

### By focus area

| Focus group | Count | Creators |
|---|---|---|
| AI news & AI explainers | 12 | Rowan Cheung, Matt Wolfe, Varun Mayya, Fireship, Two Minute Papers, AI Explained, Matthew Berman, Wes Roth, Zain Kahn, MattVidPro, Ethan Mollick, Lex Fridman |
| AI tools, tutorials & AI-for-business | 13 | Sabrina Ramonov, Vaibhav Sisinty, Ayushman Pandita, Nick Saraev, Riley Brown, Allie K. Miller, Ishan Sharma, Sanidhya Tulsinandan, Rishi Jain, Tina Huang, Jeff Su, Igor Pogany, Rachel Woods |
| AI creative / AI video | 5 | Bilawal Sidhu, Karen X. Cheng, Theoretically Media, Linus Ekenstam, Justine Moore |
| Tech reviews & tech news | 11 | MKBHD, Mrwhosetheboss, Linus Tech Tips, Technical Guruji, Tech Burner, Trakin Tech, Unbox Therapy, Dave2D, Fisayo Fosudo, Beebom, iJustine |
| Science & engineering explainers | 7 | Cleo Abram, Veritasium, Mark Rober, Kurzgesagt, Hank Green, Kyle Hill, Real Engineering |
| Robotics & space | 5 | Everyday Astronaut, Scott Manley, Marcus House, Simone Giertz, James Bruton |
| Startups, founders & creator strategy | 5 | Greg Isenberg, Ankur Warikoo, Raj Shamani, Kallaway, Dhruv Rathee |

### By region

| Region | Count | Notes |
|---|---|---|
| United States | 25 | Includes Veritasium (US/Australia) and Simone Giertz (US/Sweden) |
| India (incl. one UAE-based) | 13 | Hindi confirmed only for Technical Guruji and Trakin Tech's Hindi channel; others UNKNOWN |
| Canada / North America | 4 | Linus Tech Tips, Unbox Therapy, Dave2D, Rowan Cheung |
| UK & Ireland | 4 | Mrwhosetheboss, AI Explained, James Bruton, Real Engineering |
| Continental Europe | 3 | Kurzgesagt (Germany), Two Minute Papers (Austria-affiliated), Linus Ekenstam (Sweden) |
| Africa | 1 | Fisayo Fosudo (Nigeria) |
| UNKNOWN | 8 | Nick Saraev, Theoretically Media, Scott Manley, Zain Kahn, Jeff Su, MattVidPro, Marcus House, Igor Pogany |

Short-form evidence (all 61 rows):
- yes: 27
- no: 2 (Nick Saraev, Ethan Mollick)
- UNKNOWN: 32

## 4. Storytelling principles that recur across cited sources

These are general principles, paraphrased from the cited sources. Most sources are podcast summaries, AI-generated summary pages or third-party analyses, not the creators' full original words. Treat each one as a claim to test, not a proven rule.

1. **Start from the wrong idea the viewer already holds.** A clear explanation alone can leave misconceptions in place and make viewers more confident in them. Stating the common mistake and then correcting it produced more learning. Creator: Veritasium (Derek Muller's PhD research). Sources: https://thejournal.com/articles/2015/05/05/watching-videos-does-not-necessarily-lead-to-learning.aspx, https://rosetta.to/u/veritasium/khan-academy-and-the-effectiveness-of-science-videos

2. **Find the picture before writing the words.** Pick the one visual that makes the idea click, then build the script around it. Creator: Cleo Abram. Sources: https://videoconsortium.org/mag/episode-8-cleo-abram, https://podwise.ai/dashboard/episodes/2768285

3. **Put the lesson inside a spectacle.** Teach through a build, test or challenge people want to watch anyway, and keep questions open through setbacks until the payoff. Creator: Mark Rober. Sources: https://rosetta.to/u/ted/how-to-hide-science-vegetables-in-viral-videos-with-markrober-rober-rethinking-w, https://stanforddaily.com/2025/05/19/youtuber-and-former-nasa-engineer-mark-rober-draws-full-crowd-speaks-to-scientific-storytelling/, https://www.opus.pro/blog/mark-robers-growth-playbook-how-he-engineered-one-of-youtubes-most-trusted-brands (THIRD-PARTY)

4. **Show how the trick was done.** Pairing the finished result with the making-of can be what makes a clip spread. This fits AI demos well, where the audience's question is "how?". Creators: Karen X. Cheng; also Simone Giertz, whose failed builds are the content. Sources: https://lilys.ai/notes/90349, https://campaignbriefasia.com/?p=118818, https://www.youtube.com/watch?v=c0bsKc4tiuY

5. **Compress hard and get to the point fast.** Cover a 30-minute topic in about 100 seconds. Combine useful information with a story and some humour, and shorten the time to the first useful point. Creators: Fireship; Kallaway. Sources: https://yespress.io/jeff-delaney, https://rosetta.to/u/fireship/how-to-get-a-million-youtube-subscribers-in-100-seconds, https://www.castmagic.io/podcast/rhythm-hooks-and-a-billion-views-kane-kallaways-short-form-video-content-secrets

6. **Make the subject clear almost immediately.** Use one subject and one question per video. Short sentences and a turn against the expected view help the opening. Creator: Kallaway. Sources: https://briefread.pages.dev/en/summary/how-to-create-irresistible-hooks-and, https://recapio.com/digest/how-to-create-a-killer-hook-impossible-to-skip-by-kallaway

7. **Make short-form for each platform rather than cutting down long-form.** Do not compare view counts across platforms as if they were equal. Creator: MKBHD. Sources: https://techcrunch.com/?p=2345613, https://dailydot.com/marques-brownlee

8. **Pair the news with a personal take, and follow what the audience already cares about.** There is no fixed virality formula, and recommendation systems mostly reflect viewer demand. Creator: Varun Mayya. Sources: https://yourstory.com/2026/10/cancellation-creators-biggest-turning-point-varun-mayya, https://yourstory.com/2026/01/ai-authenticity-the-creators-edge-lessons-from-varun-mayya

9. **Answer real questions from the audience.** Questions people submit are ready-made hooks, and each short answer handles one fact well. Creator: Hank Green. Sources: https://www.yalescientific.org/?p=16972, https://thehowler.org/11692/uncategorized/hank-green (secondary)

10. **Treat research and visible sources as part of the product.** Do deep reading first, get experts to fact-check, and publish the sources. Creators: Kurzgesagt; Cleo Abram's scripts track a source for each line. Sources: https://kurzgesagt.org/youtube/, https://rosetta.to/u/kurzgesagt/how-to-make-a-kurzgesagt-video-in-1200-hours, https://podwise.ai/dashboard/episodes/2768285

11. **Build a repeatable system and learn through volume.** Batch production, reuse openers that are known to work, and let a high number of videos teach you what works. Creators: Sabrina Ramonov (her own product blog); Trakin Tech (850+ personal videos in 2024, self-reported). Sources: https://www.blotato.com/blog/social-media-hooks, https://x.com/8ap/status/1874033467530375285

12. **For AI video, editing and planning matter more than the model.** Plan the story first and treat traditional editing as the core skill. Creators: Theoretically Media; Linus Ekenstam (in a paid-partnership post). Sources: https://x.com/TheoMediaAI/status/2008201392536891572, https://x.com/LinusEkenstam/status/2061454380218581188

## 5. What remains NOT OBSERVED, and what to measure next

### Not observed for any creator
- Opening line: the exact first words and the on-screen text at 0 seconds.
- First frame and whether the creator appears on camera.
- Video duration, speaking pace (words per minute), cut rate, caption style, music and b-roll ratio.
- Any short video from the last 30 days with its URL, date and metrics.
- Views, likes, comments, shares and saves per video, and therefore any performance ratio.
- How often each creator actually posted short-form in 2026. A short-form account existing is not the same as current activity.
- The language mix (English, Hindi or Hinglish) for 10 of the 13 Indian creators.
- Live follower counts for every row. Every number in the CSV is second-hand.
- Storytelling or process sources for 40 of the 58 verified creators. These include Vaibhav Sisinty, Sanidhya Tulsinandan, Ayushman Pandita, Bilawal Sidhu, Matt Wolfe and Two Minute Papers.

### What someone with platform access should measure next
For each creator, take the 10 most recent short videos plus their top 3 of the last 90 days, and log one row per video:
1. **Opening line:** the first sentence, word for word; the on-screen text at 0 seconds; what is in the first frame; and how many seconds pass before the topic is clear.
2. **Duration:** length in seconds, plus the time stamp of the payoff or reveal.
3. **Views compared with the creator's median:** this video's views divided by the median of their last 20 short videos (an outlier score), and views divided by followers.
4. **Shares:** shares or sends divided by views (where visible), and saves divided by views.
5. **Comments:** comments divided by views, plus the top 5 comment themes (questions, disagreement, requests).
6. Format type (face to camera, screen demo, voiceover over b-roll, AI avatar), language mix, caption style and call to action.
7. **Housekeeping:**
   - Re-read follower counts from the live profiles and overwrite the tracker figures, with dates.
   - Confirm the YouTube channel URLs not yet surfaced: AI Explained, Unbox Therapy, Marcus House, Igor Pogany's AI Advantage, and Ankur Warikoo's main channel.
   - Confirm Instagram handles known only from trackers: Varun Mayya, Ayushman Pandita and Matt Wolfe.
   - Confirm that `@nickautomates` belongs to Nick Saraev.
   - Resolve the three PARTIAL rows.
