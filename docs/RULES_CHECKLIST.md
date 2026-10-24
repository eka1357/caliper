# Hackathon rules and submission checklist

## Known facts (from the event page, checked Oct 2026)

| Item | Value | Source |
| --- | --- | --- |
| Event | Meta Global AI Developer Hackathon, remote | [event page](https://dev.meta.ai/events/global-hackathon) |
| Build window | Oct 26 to Nov 4 2026, submissions due 9:00 PM ET Nov 4 | event page |
| Track | Indie developer: creativity, technical ambition, whether it works | event page |
| Theme | Push the Frontier | event page |
| Judging | Nov 4 to 8; closing ceremony with live finals Nov 9 | event page |
| Credits | $150 Meta Model API credits per selected participant (as announced by Meta) | Meta announcement |
| Status | Approved (confirmation email Oct 20) | Cerebral Valley email |

## To fill in when the official rules are published (before Oct 26)

- [ ] Is code written before Oct 26 allowed? If not, confirm that docs and config files are acceptable and disclose them in the README.
- [ ] Team size limits (we are solo).
- [ ] Required deliverables: repo (public?), demo video (max length?), hosted link, write-up.
- [ ] Required use of Meta models (which, how much).
- [ ] Open-source license requirement.
- [ ] Rules on third-party APIs, datasets and pre-trained models.
- [ ] Waiver and official rules accepted on the Cerebral Valley event page.

## Pre-submission checklist (Nov 3 to 4)

- [ ] `make test` and `make lint` pass on a clean clone
- [ ] `make report` regenerated every number in README, UI and video
- [ ] README: problem, how it works, results table, how to reproduce, limitations, credits, what existed before Oct 26
- [ ] Hosted demo works in replay mode from a private browser window
- [ ] No QuantiPhy videos in the repo or the hosted demo
- [ ] No secrets in git history (`git log -p | grep -i "api_key"` returns nothing sensitive)
- [ ] Demo video within the length limit, numbers checked against the data files
- [ ] Submitted at least 6 hours early. The deadline, 9:00 PM ET on Nov 4, is 7:30 AM IST on Nov 5, so submit by 1:30 AM IST on Nov 5 at the latest
