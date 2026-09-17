# The gate that vetoed real attacks: measuring, not voting, in aRGus NDR

*Building aRGus, an open-source C++20 Network Detection and Response system, one detection head at a time. Today's lesson came from a number I bet against — and lost.*

## The setup

aRGus classifies network flows in a cascade: a Level-1 model decides "attack or benign," and only if it says *attack* does the traffic reach the specialized Level-2 heads (DDoS, ransomware, and so on). It's an efficient design — you don't run every expensive detector on every packet. It also has a single point of failure I'd been circling for days: **Level-1 holds a veto.** If it says *benign*, the DDoS head never even sees the flow.

Yesterday I measured what that veto costs. I replayed a real UDP flood from CICDDoS2019 through the full pipeline. Level-1 classified **13,567 flood flows as benign and 1 as attack** — recall ≈ 0. The DDoS head, which exists specifically to catch this, was never given the chance. The gate stayed shut.

That raised the real question, and it split into a bet. My working partner in this (an AI I use as a sparring board) argued the DDoS head is structurally blind anyway: a flood flow in isolation is a single 1-packet datagram, statistically indistinguishable from normal UDP; the attack signature lives in the *aggregate* — thousands of flows hitting one victim — so no per-flow head could detect it. My counter-bet: the head works fine on its own; it's the veto and the interference that starve it. We wrote both predictions down **before running anything.** That discipline — *measure, don't vote* — is the whole method. A prediction you fix in advance can't be quietly reshaped to fit whatever the log shows.

## What it took to even ask the question

To measure the head directly I had to force the gate open. That meant a small, reversible debug flag (`--force-all-heads`) wired through the build system so a normal start never opens it — a compile-time invariant, never a hand-edited config that dies on the next rebuild. I pulled the gate condition out into a pure, dependency-free predicate so it could be unit-tested in isolation: a truth table proving the forced path opens the gate and, just as important, that the *non-forced* path behaves exactly as it does in production. Regression first, experiment second.

One subtlety nearly cost me the reading. The head's verdict log printed `probability` — the confidence of the *winning* class. On a "benign" verdict that's P(benign), which tells you nothing about how much attack signal was there. The quantity that answers the question is P(attack). Different field. If I'd read the wrong one I'd have concluded "the head is blind" from a number that was actually saying "90% confident it's benign." So before running, I instrumented the log to print the attack probability explicitly. The right measurement instrument matters as much as the experiment.

## The number

With the gate forced open, the DDoS head classified **~21% of the real flood as attack** (988 of 4,661 verdicts), and the "benign" flows carried attack probabilities as high as 0.44 — nowhere near zero, right up against the threshold.

I lost the bet, cleanly. The head is **not** blind to isolated flows. It extracts signal and fires on one in five.

Then I chased the mechanism, because identical-looking 1-packet flows splitting 21/79 means *something* varies. I'd assumed it would be the one aggregate feature the head consumes — a source-dispersion statistic computed over a sliding window. I logged it. It was pinned to a single constant value across all 13,258 flows: under a dense flood the window's event cap saturates and the formula degenerates to a constant. The aggregate feature contributes nothing here. What *did* vary was a per-flow feature — packet-size entropy. So the head discriminates on genuine per-flow content, not on aggregation. My mechanism was as wrong as my prediction.

## What survives — and it's the part that matters

Two bets lost, and yet the day produced its most solid architectural result, precisely *because* the bet was measured rather than argued:

**Forcing the gate open recovered ~21% recall on real DDoS traffic that the Level-1 veto was driving to zero.** The cascade wasn't just inefficient — it was suppressing detections the specialized head already knew how to make. That's not a theory anymore; it's a delta between two logged runs. The fix follows from the data, not from taste: Level-1 should score alongside the other heads, not veto them. Parallel scoring with a fusion rule, justified by a measurement.

There's an honest caveat, and it's part of the method too: this is a lab replay, the 21% is at the verdict level with some ambient traffic mixed in, and the single-source test file neuters the very aggregate feature I'd bet on — so "the head also needs aggregation for full recall" isn't disproven, just parked for an experiment with a proper multi-source flood. The head recovered a fifth of the attacks, not all of them. There's more to do.

## The takeaway

I went in confident about the mechanism and wrong on two counts. That's not a bad day — it's the point. The value wasn't in being right; it was in having written the prediction down so the number could overrule me, in instrumenting the exact quantity that settles it, and in a reversible one-flag change that let me observe the system without rebuilding its architecture on a hunch. A veto that silently suppresses real detections is invisible until you force the path open and count. So you force it open, and you count.

*Via Appia quality: built to last, measured stone by stone.*