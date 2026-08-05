"""
Lista de palavras positivas/negativas do Henry (2008) -- "Are Investors
Influenced By How Earnings Press Releases Are Written?" (SSRN 933100),
Figure 1, transcrita literalmente do PDF (ssrn-933100.pdf, paginas 25-26,
"POSITIVITY word list" / "NEGATIVITY word list").

Usada no metodo de Erasmus & Hollander (2020) replicado no paper do
usuario: bag-of-words sem peso (cada palavra conta 1), correspondencia
exata de forma (nao stem/wildcard) -- e assim que a lista foi publicada
originalmente por Henry, ja com todas as inflexoes (increase, increases,
increasing, increased, etc.) escritas por extenso.
"""

POSITIVE_WORDS = {
    "positive", "positives", "success", "successes", "successful", "succeed",
    "succeeds", "succeeding", "succeeded", "accomplish", "accomplishes",
    "accomplishing", "accomplished", "accomplishment", "accomplishments",
    "strong", "strength", "strengths", "certain", "certainty", "definite",
    "solid", "excellent", "good", "leading", "achieve", "achieves",
    "achieved", "achieving", "achievement", "achievements", "progress",
    "progressing", "deliver", "delivers", "delivered", "delivering",
    "leader", "pleased", "reward", "rewards", "rewarding", "rewarded",
    "opportunity", "opportunities", "enjoy", "enjoys", "enjoying", "enjoyed",
    "encouraged", "encouraging", "up", "increase", "increases", "increasing",
    "increased", "rise", "rises", "rising", "rose", "risen", "improve",
    "improves", "improving", "improved", "improvement", "improvements",
    "strengthen", "strengthens", "strengthening", "strengthened", "stronger",
    "strongest", "better", "best", "more", "most", "above", "record",
    "high", "higher", "highest", "greater", "greatest", "larger", "largest",
    "grow", "grows", "growing", "grew", "grown", "growth", "expand",
    "expands", "expanding", "expanded", "expansion", "exceed", "exceeds",
    "exceeded", "exceeding", "beat", "beats", "beating",
}

NEGATIVE_WORDS = {
    "negative", "negatives", "fail", "fails", "failing", "failure", "weak",
    "weakness", "weaknesses", "difficult", "difficulty", "hurdle",
    "hurdles", "obstacle", "obstacles", "slump", "slumps", "slumping",
    "slumped", "uncertain", "uncertainty", "unsettled", "unfavorable",
    "downturn", "depressed", "disappoint", "disappoints", "disappointing",
    "disappointed", "disappointment", "risk", "risks", "risky", "threat",
    "threats", "penalty", "penalties", "down", "decrease", "decreases",
    "decreasing", "decreased", "decline", "declines", "declining",
    "declined", "fall", "falls", "falling", "fell", "fallen", "drop",
    "drops", "dropping", "dropped", "deteriorate", "deteriorates",
    "deteriorating", "deteriorated", "worsen", "worsens", "worsening",
    "weaken", "weakens", "weakening", "weakened", "worse", "worst", "low",
    "lower", "lowest", "less", "least", "smaller", "smallest", "shrink",
    "shrinks", "shrinking", "shrunk", "below", "under", "challenge",
    "challenges", "challenging", "challenged",
}

assert not (POSITIVE_WORDS & NEGATIVE_WORDS), "overlap entre as duas listas"
