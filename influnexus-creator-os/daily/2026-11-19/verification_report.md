# Independent verification: 2026-11-19 script (ALS brain implant)

Method: an independent checker was given only the script (not the earlier fact-check) and searched the primary sites' own
indexed text (nature.com, biorxiv.org, health.ucdavis.edu, nejm.org, ncbi.nlm.nih.gov); 19 searches. No page could be opened
from the cloud environment, so quotes are as indexed and should be checked on the live pages before quoting verbatim.

Sources: Nature Medicine 32, 2504–2510, 15 June 2026 (https://www.nature.com/articles/s41591-026-04414-6); bioRxiv preprint
10.1101/2025.06.26.661591; UC Davis Health releases June 2026 and August 2024; Card et al., NEJM 2024.

| Claim in the original script | Finding | Action |
|---|---|---|
| "lost his voice to ALS" | Paper: "severe dysarthria due to ALS" (speech very hard to understand, not absent) | **Changed** to "ALS took his clear speech" |
| "A brain implant gave it back" | UC Davis: "allows man with ALS to 'speak' again" (their quotes) | **Changed** to "gave him a way to talk again" |
| Sensors catch signals when he tries to speak | 4 microelectrode arrays, 256 electrodes, left precentral gyrus; attempted speech | Kept |
| "Software turns them into words, read out in a voice trained on his old recordings" | Main output is on-screen text; a voice "optimized to sound similar to his pre-ALS voice" reads sentences at the end, optionally | **Qualified**: "puts the words on screen, and can read them aloud in a voice built from his old recordings" |
| 3,800+ hours at home | Paper: "Over a 19-month period … in his home for more than 3,800 h" | Kept (time in use, not continuous speaking) |
| "with no researchers there" | Paper: "used at home with no researcher intervention"; care partners did daily setup | **Changed** to "without researchers' help" |
| Nearly two million words | Paper: 183,060 sentences, 1,960,163 words, ~56 wpm | Kept |
| "He kept working full-time" | Peer-reviewed paper: "maintaining full-time employment" (also in preprint) | Kept; claim table upgraded from preprint to journal |
| "This is Casey Harrell" | Named by UC Davis (2024, 2026); "T15" in the paper | Kept |
| Closing line | Editorial opinion | "gave a man his words back" (accurate: decoded words he intended) |

Not used: accuracy figures ("99%" is from prompted tests; home accuracy was self-rated, 92% at least mostly correct); his age
(sources differ: 45 at enrolment, later 47/48).

Result: corrected script re-validated, RECORDING READY, 90 words, ~37.8 s.

# Fresh-session test of "Script for today"
A new cloud session (fresh container and clone of this branch) was given only the text "Script for today" at 00:31 IST.
It read CLAUDE.md, installed the project, found today's READY package, re-checked it, re-ran `creatoros package`, logged
`logs/runs.jsonl` (start 19:02:06Z, end 19:02:12Z, READY), pushed commit 1c70e18, and replied with the script in about 39 s.
It ran before the corrections above, so it delivered the earlier wording; the corrected package is what the 08:41 run will deliver.
