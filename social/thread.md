# Social thread draft (X / LinkedIn)

Draft only — nothing here has been posted. Six posts, written to work as a numbered
thread on X or as a single LinkedIn post broken into paragraphs with the same beats.
Swap `[link]` for the actual article URL and `[repo]` for the GitHub repo URL before
using.

---

**1/6 — the hook**

On 23 July 2026, with an energy price shock from the US-Iran conflict pushing most of the
market to price a hike, the SARB held its repo rate at 7.00% instead. I got curious about
whether that was actually a "surprise," so I spent a few weeks text-mining 27 years of
everything the South African Reserve Bank has ever said publicly — 173 MPC statements,
502 speeches — to check.

*[Chart: none — text-only hook post]*

---

**2/6 — what this is**

Short version: I replicated and extended an academic paper (du Rand et al. 2021, Economic
History of Developing Regions) that text-mines SARB communication through 2020, and pushed
it through July 2026 — the fastest hiking cycle of the inflation-targeting era, the
pandemic, and a redefinition of the inflation target itself (Nov 2025). Then I added a
piece the original paper didn't build: a rate-decision-validated hawkish/dovish index.

*[Chart: communication-volume.png — sets the scene, shows the full 1994-2026 span]*

---

**3/6 — what the SARB actually talks about**

Ran a topic model (LDA) over every speech since 1994. Six themes fall out cleanly:
exchange rate policy (dominant in the 1990s rand crises, essentially gone by the 2010s),
financial stability (a structural rise after 2008, not a one-off), a genuine "global
crisis" dial (GFC, Euro debt crisis, Covid), and inflation itself — which has been the
single largest topic in SARB speeches since the mid-2010s.

*[Chart: topic-evolution-bars.png]*

---

**4/6 — building a hawkish/dovish score**

Replicated the sentiment method from the literature (Henry 2008 dictionary, via Erasmus &
Hollander 2020): count "hawkish" vs. "dovish" words, no LLM judgment involved. It tracks
real policy directionally — meetings that ended in a hike score +0.78 on average, holds
+0.64, cuts +0.39 — though the whole scale runs hotter than you'd expect (more on that in
the full piece). Speeches consistently score hotter than the terse, boilerplate MPC
statements — and, scored separately, the statement's own tone tracks its own decision far
better than the speeches leading up to a meeting predict it.

*[Chart: interactive combined-index chart, or a screenshot of it]*

---

**5/6 — so was July 2026 actually a surprise?**

Pulled every meeting since 1999 with a similarly hawkish reading to July 2026's. Answer:
not really — that level of hawkish-sounding communication has historically ended in a hold
52% of the time and a hike only 19% of the time. Narrow it further to meetings that, like
July 2026, came right after a hike, and it's close to a coin flip. The tone alone never
clearly said "hike again" — which is exactly why it's worth being careful about reading
too much into central-bank language in real time.

*[Chart: the comparison table from Section 4, as an image/screenshot]*

---

**6/6 — the rest**

Full writeup with all the charts, the methodology (including the dead ends — what didn't
work and why), and an honest account of where AI was and wasn't used in building this:
[link]

Code + data, fully reproducible from a notebook: [repo]

If you build or study anything like this for other central banks, I'd like to hear about
it.
