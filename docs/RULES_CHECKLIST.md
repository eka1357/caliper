# Hackathon rules and submission checklist

Full text: docs/OFFICIAL_RULES.md. Times converted to IST (US daylight saving ends Nov 1, so ET is UTC-4 until then and UTC-5 after).

## Key facts

| Item | Value |
| --- | --- |
| Building period | Oct 27 to Nov 4 (ET). Start code after Oct 27 00:00 ET = 9:30 AM IST Oct 27 |
| Kickoff livestream | Mon Oct 26, 12:00 PM ET = 9:30 PM IST (the CV calendar entry shows 10:30 PM IST; join early) |
| Workshops | Oct 27 Agents 101, Oct 28 Agents 102 (verifiable agents: attend), Oct 30 Fireworks open models; 12:00 PM ET = 9:30 PM IST |
| Office hours | Weekdays 10 to 11 AM ET in #office-hours = 7:30 to 8:30 PM IST until Oct 30, 8:30 to 9:30 PM IST from Nov 2 |
| Deadline | Wed Nov 4, 9:00 PM ET = Thu Nov 5, 7:30 AM IST. Our target: submit by Nov 4, 11:59 PM IST |
| Judging | Stage One pass/fail; Stage Two four equal criteria (Impact, Use of Meta AI Tooling, Technical Depth and Execution, Demo), 0 to 10 each; Stage Three top 5 per track, video watched live |
| Indie prizes | $150K, $100K, $75K, $50K, $25K |
| Bonus prizes we can target | Most Viral on X ($20K), Best Build on Meta Open Weight Models ($10K, needs Muse Spark Open or Muse Glimmer), Community Vote ($10K), Best Agentic Use-Case ($5K) |
| Team | Solo allowed; you are the Representative |

## Rules that affect us

- [ ] Repo public at submission; check history for secrets first.
- [ ] New work only: code written from Oct 27 ET; README states what existed before (planning docs, config, field clips) and what was built during the event.
- [ ] Demo video shows only features built during the hackathon.
- [ ] Only code, data and assets we have rights to: QuantiPhy used for evaluation only and never shown; components, fonts and models credited with their licenses.
- [ ] Not an anti-project: no medical advice, sports analysis, education chatbot, or political framing.
- [ ] Meta models used meaningfully: Muse Spark 1.3 (spec and audit), SAM 3.1 (tracking); stretch Muse Spark Open.

## Credits and accounts

- [ ] Add a credit card to the Meta Model API account (required for calls; enable international payments on an Indian card).
- [ ] Set a Spend Limit notification on the Billing page at $150 or lower.
- [ ] Claim the $150 credits when the link arrives; claim by Nov 4, 9:00 PM ET.
- [ ] Request Modal credits now (first 1,000 participants).
- [ ] Request Baseten credits (up to 2,000, reviewed by use case); model `meta-models/muse-spark-open-1026`.
- [ ] Join the Discord; post in #intros.

## Pre-submission checklist (Nov 3 to 4)

- [ ] `make test` and `make lint` pass on a clean clone
- [ ] `make report` regenerated every number in README, UI, video and X post
- [ ] README complete: problem and users, how it works, results, speed study, reproduce in one command, limitations, built during vs before, credits and licenses
- [ ] Live product works (live run within caps and cached runs) from a private window
- [ ] No QuantiPhy videos in the repo, hosted demo, or video
- [ ] No secrets in git history (`git log -p | Select-String -Pattern "api_key|MODEL_API_KEY="` shows nothing sensitive)
- [ ] 3-minute video uploaded, link opens without login
- [ ] Submission on the CV platform: repo link, video link, live link, X post link
- [ ] X post published (30 to 45 s cut) and its link submitted
