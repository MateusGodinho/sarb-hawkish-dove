# What 27 years of central bank speeches say about a "surprise" hold

*Draft — not yet published. ~950 words. Swap `[link]` for the article URL once it's
published (the repo link is already filled in below).*

On 23 July 2026, the South African Reserve Bank's Monetary Policy Committee held the repo
rate at 7.00%. Most of the market was positioned for a hike, with an energy price shock
tied to the US-Iran conflict as the main exogenous pressure. That gap — between what
traders expected and what the MPC actually did — is the reason this project exists. Not to
argue the SARB got the call wrong (that's a monetary-policy argument, and a different kind
of writer's job), but to ask a narrower, checkable question: given everything the SARB has
ever said publicly, was a hold actually the unusual outcome here?

To answer it properly required going back 27 years, not just one meeting. So this turned
into a full replication-and-update of du Rand, Erasmus, Hollander, Reid & van Lill (2021),
the most thorough existing text-mining study of SARB communication — which covers 1994
through 2020 and stops right before the interesting part (the pandemic, the fastest hiking
cycle of the inflation-targeting era, and a November 2025 redefinition of the inflation
target itself). I scraped everything the paper's dataset would now include if it were
updated — 173 MPC statements, 604 speeches (502 of them in English and usable) — and pushed
three of the paper's analyses forward to July 2026, then added a piece the original didn't
build.

**What the SARB has talked about, 1994–2026**

The first analysis is a topic model — Latent Dirichlet Allocation, an unsupervised
algorithm that groups vocabulary into themes purely from co-occurrence, no labels supplied.
The paper runs this over speeches (not statements — MPC statements are too formulaic to
separate into distinct topics, a finding I reproduced before doing anything else) and
settles on six themes with k=6. I wanted more resolution: specifically, I wanted to see
whether the *design* of the inflation-targeting regime (mandate, framework, objective) read
differently from the *day-to-day state* of inflation (this quarter's print, the forecast).
Six topics collapse those into one bucket.

Getting there took iteration — k=15 split things cleanly but turned unstable across random
seeds; k=10 made financial stability and a "global crisis" theme collapse into each other.
k=12 was the resolution where the important splits held up, and it surfaced a bonus theme:
explicit discussion of the SARB's own institutional independence. One split never held up at
any k — regime-design and current-inflation vocabulary kept bleeding together — so I merged
them back rather than force a distinction the data won't support.

The result reads like a coherent history: exchange-rate policy dominates the 1990s (peaking
in the 1996 rand crisis), fades to near-zero by the 2010s as inflation targeting takes over;
financial stability rises structurally, not cyclically, after 2008; a genuine "crisis dial"
tracks the GFC, the Euro debt crisis, and Covid; and inflation itself has been the single
largest topic in SARB speeches since roughly 2015 — which turns out to matter for what
comes next.

**Scoring the tone, not just the topic**

The second piece replicates the paper's sentiment method: a Henry (2008) bag-of-words
dictionary (via Erasmus & Hollander, 2020), counting "hawkish" and "dovish" words with no
LLM judgment involved — deliberately the same blunt instrument the literature uses, not
something fancier. I built it three ways: statements alone, speeches alone, and — following
the paper's own logic that speeches between meetings belong to the same communication
stream as the statement that follows — a combined series where every meeting's reading is
an *exact* decomposition of what the statement itself contributed versus what the speeches
since the last meeting contributed.

Two sanity checks matter here. The index does move with real policy: meetings that ended in
a hike average +0.78, holds +0.64, cuts +0.39 — the right ordering, even though every bucket
sits on the hawkish side of zero (a skew the original paper's version shares, and one I'd
attribute to the dictionary being built for equity-analyst earnings calls, not central-bank
text, rather than to anything specific to this implementation). And the extremes line up
with real history: the hottest readings cluster in 2002, right after the rand collapsed;
the coldest sit at February 2009, November 2019, and May 2020 — the GFC cutting cycle, the
pre-pandemic growth slowdown, and the pandemic emergency cut, respectively.

One more split worth a beat: scored on their own, statements track the decision they
announce far better than speeches predict it. From the start of inflation targeting
(February 2000), a statement's own tone correlates with the announced rate move at 0.46
(Pearson); the tone of speeches in the weeks before a meeting correlates with what that
meeting decides at only 0.14 — same direction, far weaker. Don't expect a run of speeches
to reliably telegraph the next move.

**So, was July 2026 a surprise?**

Here's the part that motivated all of it. July 2026's combined reading is +0.78 — hawkish,
consistent with the market's hike call. But pull every meeting since 1999 with a similarly
hawkish reading and look at what the MPC actually did: 52% held, 29% cut, and only 19%
hiked. On the SARB's own communication history, a hold was the *modal* outcome for a
meeting that talked like this one did.

There's a sharper cut, too. July 2026 didn't just sound hawkish — it came right after a
hike (May 2026). Narrowed to meetings that also followed a hike, the historical split is
close to a coin flip: 60% hiked again, 40% held. The unconditional lean toward "hold" turns
out to be driven mostly by hawkish-sounding meetings that came after a hold or a cut, where
holding is the obvious path. Once a hiking cycle is actually underway, tone alone doesn't
clearly call whether it continues or pauses — which is, I think, the honest and slightly
unsatisfying answer: the SARB's own words couldn't have told you in advance which way July
2026 would go.

The full piece has all six charts, the complete comparison table, and a section on exactly
where and how I used AI to build this (a lot of the scraping and debugging, none of the
underlying sentiment judgments): [link]. Code, data, and a notebook that reproduces every
number in this post from scratch: https://github.com/MateusGodinho/sarb-hawkish-dove.
