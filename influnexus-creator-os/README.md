# Influnexus Creator OS

Research, script, edit, QC, publish and measure one short tech video a day.
The 100,000-follower figure is a target, not a promise; nothing here manufactures engagement.

## Daily loop
1. **09:09 IST** a scheduled Claude session follows `RUNBOOK.md` and writes `daily/DATE/brief.md` (ready by 09:30).
2. Record the script on the iPhone and save it to `footage/incoming/DATE.mov`.
3. `creatoros edit footage/incoming/DATE.mov --date DATE` produces `final/DATE_{instagram,linkedin,x,youtube}.mp4` and a QC report in `renders/DATE/`. Files appear in `final/` only when QC passes.
4. Post (manually for now), then log results with `creatoros metrics-add` at 24 h, 72 h and 7 days.

## Setup
```
pip install -e ".[dev]"
tools/setup_models.sh                 # about 950 MB of speech models from GitHub releases; free
python -m pytest                      # 28 unit tests + 1 end-to-end render (needs --with-test-voice models)
```
Needs FFmpeg with libass, libx264 and zscale. On a Mac, `pip install -e ".[mac]"` adds faster-whisper for true word-level timestamps.

## Commands
| Command | Does |
|---|---|
| `creatoros probe VIDEO` | resolution, frame rate, codec, rotation, HDR flag, audio level and noise floor |
| `creatoros edit VIDEO --date DATE` | full edit and QC; resumes from cached steps |
| `creatoros script-check FILE` | word count, estimated duration, banned openings and endings |
| `creatoros factcheck FILE --script FILE` | rejects unverified or unattributed claims |
| `creatoros score FILE` | trend score for candidate stories |
| `creatoros story-check` / `story-add` | repeat prevention (`research/story_log.jsonl`) |
| `creatoros brief --date DATE` | validates `daily/DATE/brief.json` and renders the brief |
| `creatoros calibrate --date DATE` | records the creator's measured speaking pace from a finished edit |
| `creatoros metrics-add k=v ...` / `metrics-report` / `metrics-review` | analytics |
| `creatoros publish --date DATE --platform P [--reviewed] [--dry-run]` | gated publishing |

## How the edit works
1. Voice-activity detection (Silero) splits the audio; Whisper small transcribes each piece as Hindi.
2. Script (Roman Hinglish) and transcript (Devanagari) are reduced to phonetic keys and matched sentence by sentence.
3. For each sentence the best complete take is kept, later takes winning near-ties. False starts, repeated takes, asides and long pauses are dropped and listed in `edit_report.json`.
4. Cuts land on frame boundaries; framing changes slightly only across a real jump.
5. Audio: high-pass, mild denoise, presence, gentle compression, two-pass loudness to -14 LUFS, limiter. Optional original music bed, ducked under the voice.
6. Captions use the approved script's spelling, timed to the recorded audio, 2-5 words per group, inside Instagram's safe area. Sentences that matched weakly are flagged for a human check.
7. Title cards and labels come from `scripts/DATE_edit_plan.json`. Each factual overlay must cite a fact-checked claim.
8. One H.264 1080x1920 30 fps render, then QC (see `renders/DATE/qc_report.md`).

## Verified state (18 November 2026)
| Component | State | Evidence |
|---|---|---|
| Daily research | WORKING, with limits | `daily/2026-11-18/brief.md`: 11 candidates from web search. X, Instagram and most news sites cannot be opened from the cloud environment, so engagement counts are UNKNOWN |
| Source verification | PARTIALLY WORKING | Claims cross-checked across independent outlets via search; primary pages (Oracle, Calif) could not be opened here |
| Script generation and checks | WORKING | `scripts/2026-11-18_script.txt`; duration is an estimate at an assumed 150 wpm until calibrated |
| Footage ingestion | WORKING on synthetic footage | HEVC MOV 60 fps with rotation tag, and horizontal H.264 MP4. No real iPhone file has been processed yet |
| Transcription | WORKING, approximate timing | Whisper small via sherpa-onnx; word times inside a phrase are interpolated |
| Retake removal | WORKING on synthetic footage | false start, aside, bad take and 2.4 s pause removed in the end-to-end test |
| Subtitles | WORKING | `subtitles/*.srt` and burned-in captions; layout check passes |
| Graphics | WORKING | title, label, cards, split, credit, image. Video B-roll overlay is implemented but untested |
| Audio processing | WORKING | measured -14.0 LUFS, true peak below -1.5 dBFS; music ducking rendered in the horizontal sample |
| MP4 export | WORKING | 1080x1920 H.264/AAC 30 fps, four platform files |
| Automated QC | WORKING | 28 checks on the sample; lip-sync is not measured, only stream alignment |
| HDR tone-mapping | NOT TESTED | filter chain is in place; no HDR sample was available |
| Daily scheduling | WORKING | scheduled task "Influnexus daily brief", 09:09 Asia/Kolkata; first run not yet observed |
| Notification | PARTIALLY WORKING | push notification was requested by the app; delivery to a phone is not confirmed from here |
| Analytics storage | WORKING, no real data | CSV store and derived metrics are unit-tested; nothing has been published |
| Analytics from platform APIs | BLOCKED | no credentials; graph.facebook.com unreachable from this environment |
| Publishing: Instagram, YouTube | BLOCKED | adapters written against the official APIs but never run against them; need credentials (and a public video URL for Instagram) |
| Publishing: LinkedIn, X | NOT IMPLEMENTED | captions are prepared; post manually |
| Competitor video analysis | BLOCKED | no creator video could be watched; `research/` separates cited facts from hypotheses |
| Cloud video editing on real footage | NOT TESTED | renders complete in this cloud container (about 3 min per reel), but there is no upload path for raw iPhone footage yet |

## Cloud and local
- Cloud (no Mac needed): research, brief, scheduling, notification, story log.
- Editing runs anywhere FFmpeg and the models are installed. Today the practical path is the Mac, because the raw file is there. To edit in the cloud the footage must reach the session (for example a shared folder through Remote Control).

## Rules the code enforces
- A brief will not render with a banned opening, a script over 40 s, an UNVERIFIED claim in the script, or an attributed claim whose attribution is not spoken.
- High traction scores need recorded evidence; unknown metrics score zero.
- Publishing refuses without a passing QC report, a clean fact-check, credentials, and `--reviewed` when QC raised warnings or a disputed claim is used. A file or date is never published twice.
- Source footage is never moved or deleted. Tokens are read from the environment and redacted from logs.

## Layout
`config/` settings, style, platforms · `research/` benchmarks, style guide, story log · `daily/` briefs · `scripts/` script, sources, fact-check, edit plan · `footage/` raw in, processing records · `assets/` fonts, music, licence manifest · `src/creatoros/` code · `tests/` · `tools/` model setup and synthetic test footage.
