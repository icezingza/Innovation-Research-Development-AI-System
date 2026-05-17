---
name: ai-research
description: Systematic AI research process. Use when the user is AI researcher and the project is involved in AI research project.
---

# AI Research Guide

This document consolidates all modules and templates for AI research methodology.

---

# Modules

---

title: Overview; Explore → Understand → Distill
tags: overview, stages, workflow, north-star
description: The research process model; what each stage is for, what progress means, and when switching stages is normal.

---

## Overview: Explore → Understand → Distill

Research often feels messy because you’re holding yourself to the wrong standard for the stage you’re actually in.

This bundle breaks research into three core stages (plus ideation), each with a different “north star”:

- **Ideation:** choose a problem / direction
- **Exploration:** gain surface area
  - **North star:** information gained per unit time
- **Understanding:** test hypotheses
  - **North star:** evidence that convinces you a key hypothesis is true/false
- **Distillation:** compress, refine, communicate
  - **North star:** concise, defensible, communicable truth

---

## How stages relate

### Exploration → Understanding

Exploration produces:

- a map of the space
- interesting anomalies
- candidate hypotheses
- a sense of which questions matter

Understanding begins when you can:

- write down specific hypotheses, and
- describe what evidence would change your mind

### Understanding → Distillation

Distillation begins when:

- you’re fairly convinced about the key hypotheses, and

---

---

title: Stage Classifier
tags: stage, triage, exploration, understanding, distillation
description: Diagnose which research stage you are in and what “progress” should mean right now.

---

## Stage classifier

Correctly identifying the stage is often the highest-leverage move.

### You are in **Exploration** if:

- You don’t yet have crisp hypotheses
- You’re unsure what questions matter
- Results feel scattered but informative
- You’re saying “I should already know what’s going on”

**North star:** information gained per unit time

---

### You are in **Understanding** if:

- You can write down specific hypotheses
- You know what evidence would change your mind
- Experiments are designed to distinguish explanations
- Confounds and baselines matter a lot

**North star:** evidence that convinces you

---

### You are in **Distillation** if:

- You mostly believe your conclusions
- The confusion is about _claims_, _scope_, or _communication_
- Writing reveals missing experiments
- You’re preparing a paper, blog post, or report

**North star:** concise, defensible, communicable truth

---

### If unsure

Default to **Exploration** for 30–90 minutes:

- Run surface-area experiments
- Then reclassify

Misclassifying early stages as “understanding” is a common junior failure mode.

---

---

title: Ideation; Choosing a Problem
tags: ideation, problem-selection, literature, replication, mentor
description: Choose a problem/domain and get oriented without needing deep literature mastery upfront.

---

## Ideation: choosing a problem

Ideation ranges from:

- broad exploration across areas to find a promising angle, to
- being handed a problem by a mentor.

### What to do

1. If new, start by replicating/extending a strong existing paper.
2. Get a quick map of the literature:
   - what’s known
   - what’s open
   - what adjacent work is relevant
3. Prefer mentorship or high-quality research agendas early.
4. Build hands-on experience before trying to “know everything” in the literature.

### Taste shows up here

Problem choice is one facet of taste. Taste also governs:

- which anomalies are interesting (exploration)
- which experiments distinguish hypotheses (understanding)
- what narrative/claims are defensible (distillation)

### Output

- candidate problem list (3–10)
- why each might matter
- fastest “sign of life” tests / mini-projects
- an initial reading list (5–15 items)

---

---

title: Exploration; Maximize Information Gain
tags: exploration, surface-area, curiosity, prioritization
description: How to explore effectively when you don’t yet know the right questions.

---

## Exploration: information gain

Exploration is about **learning what questions to ask**, not validating specific theories.

### North star

Maximize **information gained per unit time**.

---

## What to do

1. Run many small, cheap experiments
2. Visualize data in multiple ways
3. Follow curiosity and anomalies
4. Keep a highlights doc of interesting results
5. Move fast; avoid perfectionism

Ask frequently:

> “Am I learning enough per unit time?”

If the answer is no, change tactics.

---

## Prioritization heuristic

When usefulness is unclear, prioritize by:

- speed
- tractability
- diversity of perspectives

Fast, messy experiments often teach more than slow “correct” ones.

---

## Common failure modes

- Expecting a clear hypothesis too early
- Over-optimizing for “the best experiment”
- Getting stuck because you feel you _should_ understand already
- Not zooming out to ask “what else could be going on?”

---

## Output

- List of surprising observations
- Candidate hypotheses worth testing
- Updated sense of what questions matter

---

---

title: Understanding Hypotheses & Evidence
tags: hypotheses, experiments, baselines, skepticism
description: Turn vague ideas into testable hypotheses and design experiments that distinguish explanations.

---

## Understanding: hypotheses & evidence

You are in understanding once you can articulate what you believe and why.

### North star

Gather evidence that convinces **you** a hypothesis is true or false.

---

## Core loop

1. Write down hypotheses explicitly
2. For each hypothesis:
   - What does it predict?
   - What evidence would change your mind?
3. Design experiments that distinguish _plausible alternatives_
4. Implement strong baselines
5. Check for bugs and confounds

---

## Good experiments

A great experiment:

- cleanly distinguishes explanations
- tests non-trivial predictions
- is tractable in practice

You won’t always get this ideal — aim toward it.

---

## Fast-fail question

> “If this hypothesis is wrong, how could I discover that as fast as possible?”

Often several small tests beat one large, slow one.

---

## Common failure modes

- Falling in love with a hypothesis
- Ignoring boring alternative explanations
- Weak or missing baselines
- Cherry-picked qualitative examples

---

## Output

- Refined hypotheses
- Evidence map (hypothesis → experiment → risk)
- Clear next experiments

---

---

title: Distillation; Communicable Truth
tags: distillation, claims, writing, rigor, communication
description: Compress messy work into a small set of defensible claims with a rigorous evidence case.

---

## Distillation: communicable truth

Distillation begins when you’re fairly convinced about the key hypotheses.
The work shifts from “what’s going on?” to “what exactly can we claim, and how do we justify it?”

### North star

Compress findings into concise, rigorous truth you can communicate to the world.

---

## Core principles

### 1) Compress into well-scoped claims

- Aim for **1–5 claims** (often 1–3 for most readers).
- Compress as far as possible without losing the message.

Prompts:

- How would you explain this to a peer?
- What would you say in a lightning talk?

### 2) Refine evidence into a rigorous case

Raise the bar above “convincing yourself”:

- strong baselines
- sanity checks
- robustness/statistical checks (as appropriate)
- legibility for outsiders

### 3) Red-team hard

- What alternative hypotheses explain the observations?
- What experiments distinguish them?
- What would a skeptical reader attack?

### 4) Communicate clearly (inform, not persuade)

Make:

- claims
- evidence
- limitations
  explicit.

Format doesn’t matter (paper/blog/report). Clarity does.

---

## Common distortions

- Under-rating distillation (“writing is wasting time”): writing forces clarity and reveals missing experiments.
- Over-rating “acceptance optimization”: choosing narratives for reviewers rather than truth.

Returning to understanding/exploration is normal if writing reveals gaps.

---

## Output

- claim list (scoped, precise)
- claim → evidence map
- limitations / open questions
- missing experiments list (ranked)

---

---

title: Truth-Seeking
tags: truth-seeking, skepticism, baselines, bias
description: Stage-specific practices for active skepticism: avoid boring explanations, test baselines, and resist narrative bias.

---

## Truth-seeking

By default, many research insights will be false unless you actively resist bias.

A common failure mode: a simple boring explanation exists and nobody tests it.

### Truth-seeking in exploration

Failure modes:

- getting attached to the first plausible hypothesis
- failing to generate alternative hypotheses

What to do:

1. Resist entering “understanding” too early:
   - Are there unexplained anomalies?
   - Do you have enough surface area?
2. Regularly zoom out:
   - “What else could explain this?”
   - ask a mentor/peer
   - ask an LLM for cheap alternative hypotheses
3. It’s okay to believe false things briefly — but reflexively try to falsify them.

Watch for the opposite failure mode:

- being so skeptical you never explore implications enough to design good tests.

### Truth-seeking in understanding

What to do:

1. Use a comparative framing:
   - “Is this observation more likely under A or B?”
2. Prefer quantitative checks when possible.
3. If using qualitative cases:
   - sample randomly or use multiple examples
   - avoid cherry-picking

Exception:

- “there exists at least one example of X” claims.

### Truth-seeking in distillation

What to do:

- don’t pick narratives because they look good
- publish negative results when informative
- acknowledge key limitations and uncertainty

### Output

- list of plausible alternative explanations
- baseline/ablation checklist
- “what would change my mind?” statements

---

---

title: Prioritisation
tags: prioritization, planning, goal-setting, zoom-out
description: Choose high-value actions under time constraints; use goal/sub-goal/objective and regular zoom-outs.

---

## Prioritisation

Time is scarce and the action space is huge. Projects live or die by choosing good actions.

### Requires

- a clear north star (stage goal)
- judgment about which actions serve it
- time to reflect
- willingness to drop directions (while respecting switching costs)

### Stage goals

- Ideation: pick a fruitful problem
- Exploration: gain surface area
- Understanding: convince yourself of key hypotheses
- Distillation: produce concise, well-supported truth

---

## Practical structure

### Ask regularly

> “Do I endorse what I’m doing, and could I be doing something better?”

### Use 3 tiers

- **Goal** (months): overall north star
- **Sub-goal** (weeks): current chunk
- **Objective** (days): concrete outcome

### Plan lightly (especially in understanding/distillation)

- rough time estimates
- identify uncertainties
- question necessity

### If stuck

Set a 5-minute timer:

- brainstorm 10 possible actions
- pick the best by (expected value) / (time)

### Separate prioritizing from executing

- zoom out to decide
- then lock in and execute without constant re-litigation

---

## Weekly review prompts

- What is my goal right now?
- What progress have I made?
- What consumed the most time?
- What blocked me?
- What mistakes did I make, and how could I systematically change my approach?
- What am I confused about?
- Am I missing something?

### Output

- ranked action list with “why now”
- next objective with “done” criteria
- explicit deprioritized items

---

---

title: Moving Fast
tags: speed, feedback-loops, tooling, efficiency, uncertainty
description: Move faster without sacrificing quality: tighten feedback loops, improve tooling, audit time, and act under uncertainty.

---

## Moving fast

Moving fast is not “work more hours” or “cut corners.”
It’s reducing friction while keeping the work honest.

Key levers:

- tight feedback loops
- good tooling
- noticing/fixing inefficiency
- acting under uncertainty (avoid analysis paralysis)

See also:

- [Tight feedback loops](modules/09-tight-feedback-loops.md)
- [Fail fast](modules/10-fail-fast.md)
- [Action under uncertainty](modules/11-action-under-uncertainty.md)

### Output

- shortest path from idea → result
- a tooling/automation improvement list
- a fast-first experiment plan

---

---

title: Tight Feedback Loops
tags: feedback-loops, tooling, notebooks, iteration
description: Shorten the cycle time from experiment idea to results; optimize for quick iteration early.

---

## Tight feedback loops

A feedback loop is the time from “experiment idea” to “result you can interpret.”
Short loops matter because you start confused and need repeated feedback from reality.

### What to do

1. Prefer interactive workflows (notebooks / interactive REPL).
2. De-risk on the smallest setup that could work:
   - smallest model
   - smallest dataset
   - shortest run
3. Visualize flexibly (dataframes, quick plots, ad-hoc views).
4. If training is long:
   - run partial data/evals for signs of life
   - fail early rather than perfect late

### Mindset

Impatience: “this should be possible faster.”

### Output

- a “fast loop” version of the workflow
- a checklist of cycle-time bottlenecks

---

---

title: Fail Fast
tags: fail-fast, assumptions, decisive-tests, exploration, understanding
description: Discover doomed directions quickly with the fastest tests of key predictions and assumptions.

---

## Fail fast

A major time sink is spending weeks/months on a doomed direction.

Ask:

> If this direction is doomed, how could I discover that as fast as possible?

### Understanding-stage fail-fast

1. Identify confident predictions of the hypothesis.
2. Design the quickest dirtiest test for those predictions.
3. Run several small tests from different angles.

### Exploration-stage fail-fast

1. Identify fundamental assumptions that make the domain interesting.
2. Test those assumptions with minimal experiments.
3. If they fail, pivot early.

### Output

- a ranked list of “decisive tests”
- an explicit pivot criterion

---

---

title: Taking Action Under Uncertainty
tags: uncertainty, decision-making, execution, momentum
description: Choose a reasonable next step without needing to know the “right” move; treat decisions as data.

---

## Taking action under uncertainty

You often can’t know the “right” next step. In practice, there isn’t one.

### What to do

1. Accept uncertainty emotionally: you won’t get certainty before acting.
2. Make a best guess from noisy evidence.
3. Act anyway.
4. Stay self-aware enough to notice when it’s no longer best.
5. Treat bad calls as data that improves your judgment next time.

Especially early:

- the learning value dominates
- stakes are low
- moving beats freezing

### Output

- 1–2 concrete next actions with “done” criteria
- a re-evaluation trigger (“if X happens, reconsider”)

---

---

title: Research Taste; Overview
tags: taste, judgment, intuition, learning
description: Research taste is learned judgment across the whole project (not just choosing problems); it improves with experience and reflection.

---

## Research taste: overview

Taste is often treated as mystical. It’s real and valuable, but largely learned.

Taste = the intuitions and judgments that guide ambiguous research decisions:

- which anomalies to chase
- which experiments will be compelling vs inconclusive
- what narrative is defensible and interesting

New researchers lacking taste is normal.
You can start anyway.

### Analogy

Taste develops like training a model:

- bad initialization
- needs diverse high-quality data
- improves with feedback over time

Hard part:

- feedback for strategic taste is slow and noisy

### Output

- a “taste training loop” for the project
- a list of decisions worth reflecting on

---

---

title: Research Taste; Ingredients
tags: taste, intuition, framework, strategy, conviction
description: Decompose taste into components: intuition, conceptual frameworks, strategic big picture, and conviction/confidence.

---

## Decomposing taste: ingredients

Taste is a bundle of interacting parts.

### 1) Intuition (System 1)

Fast gut feelings:

- “promising”
- “rabbit hole”
- “important anomaly”

Built slowly via exposure and feedback.

### 2) Conceptual framework (System 2)

Domain knowledge and principles that:

- generate hypotheses
- spot inconsistencies
- constrain what’s plausible
- enable better experiments

### 3) Strategic big picture

Sense of:

- what problems matter
- what counts as a meaningful contribution
- what approaches have been tried

Aim to align curiosity with importance rather than forcing obligation.

### 4) Conviction & confidence

Conviction can maintain momentum through setbacks.
But it can also lock you into wrong ideas.

Ideal: strategic conviction

- act confidently to make progress
- zoom out regularly to stay skeptical and update

### Output

- a list of which “taste component” is currently limiting progress
- a targeted plan to improve it

---

---

title: Cultivating Research Taste
tags: taste, reflection, mentors, papers, prediction, postmortem
description: Train taste faster via better data and better sample-efficiency: predictions, post-mortems, mentors, and active reading.

---

## Cultivating research taste

Improve taste like improving a model:

- more/better data
- better sample-efficiency

---

## Learn more from each data point

Each data point is richer than success/failure.

What to do:

1. Make explicit predictions (write them down).
2. Act (run experiment / ask mentor / read paper).
3. Review accuracy.
4. Post-mortem:
   - what did I miss?
   - what heuristic would have helped?
   - what do I do differently next time?

Keep a research log.

---

## Get more data

### Mentors (biggest accelerator)

Treat mentors like supervised data.

- predict their advice first
- when surprised, ask “what heuristic did you use?”
- paraphrase their reasoning back in your own words

### Learn critically from papers

- predict methods/results/limitations before reading
- reconstruct the thought process
- engage with flaws (papers are often flawed)

### Collaborate and discuss

Explaining forces clarity and surfaces alternative perspectives.

### Prefer clearer feedback early

Projects with testable intermediate hypotheses teach faster than long moonshots.

---

## Feedback loops determine learning speed

- tactical taste (minutes–days) improves faster
- strategic taste (months–years) improves slower

### Output

- a weekly reflection routine
- a prediction/post-mortem log
- a plan to use mentors/papers more actively

---

---

title: Common Failure Modes
tags: pitfalls, debugging, stage-errors, skepticism, speed
description: Common ways research gets stuck; quick diagnosis and fixes aligned to the stage model.

---

## Common failure modes (and fixes)

### 1) Misclassified stage

Symptom: “I’m stuck because I don’t have a hypothesis”
Fix: you’re probably in exploration → optimize information gain.

### 2) Too-early commitment

Symptom: one hypothesis dominates too fast
Fix: generate alternatives; keep exploring until anomalies are explained.

### 3) Weak skepticism

Symptom: results feel exciting but fragile
Fix: baselines, confounds, bug checks, alternative explanations.

### 4) Over-optimization / perfectionism

Symptom: slow progress, few experiments
Fix: more small experiments; prioritize info/evidence per unit time.

### 5) Long cycle times

Symptom: each iteration takes days/weeks
Fix: shrink the loop: smallest model/data; partial evals; notebook workflow.

### 6) Distillation avoidance

Symptom: “writing is wasting time”
Fix: start distillation early; writing reveals missing experiments.

### 7) Reviewer-optimization (distortion)

Symptom: chasing what looks good over what’s true
Fix: keep truth as north star; state limitations; publish negative results.

### Output

- diagnosed failure mode(s)
- 1–3 concrete interventions

---

# Templates

---

title: Distillation Claims Template
tags: distillation, claims, scope, communication
description: Produce a small set of scoped claims with confidence levels and explicit non-claims.

---

## Distillation claims

Aim for 1–5 claims (often 1–3).

### Claim 1

- Claim (precise):
- Scope (models/tasks/regimes):
- Evidence summary (1–3 bullets):
- Key limitations / caveats:
- Confidence (low/med/high):
- What I am NOT claiming:

### Claim 2 (optional)

- Claim:
- Scope:
- Evidence:
- Limitations:
- Confidence:
- Not claiming:

### Claim 3 (optional)

- Claim:
- Scope:
- Evidence:
- Limitations:
- Confidence:
- Not claiming:

### Takeaway (for a peer / lightning talk)

- One paragraph:
- One sentence:

---

---

title: Experiment Plan Template
tags: understanding, experiments, baselines, confounds
description: Fill-in template for designing a discriminating experiment with strong baselines and clear success criteria.

---

## Experiment Plan

**Hypothesis (H):**

- Statement:

**Alternative hypotheses (A1, A2, …):**

- A1:
- A2:

**Predictions**

- If H is true, I expect:
- If A1 is true, I expect:
- If A2 is true, I expect:

**Experiment design**

- Setup:
- Variables manipulated:
- Measurements:
- Dataset / prompts / sampling:
- Analysis method:

**Baselines / controls**

- Baseline 1:
- Baseline 2:
- Negative control:
- Sanity checks:

**Confounds / failure modes**

- Potential confound 1:
- Potential confound 2:
- Bug risks:

**Success criteria / decision rule**

- What result would support H?
- What result would falsify H?
- What result would be inconclusive?

**Runtime / cost**

- Expected time:
- Compute:
- Dependencies:

**Next actions**

- If supports H:
- If falsifies H:
- If inconclusive:

---

---

title: Highlights Doc Template
tags: exploration, highlights, logging
description: Lightweight log of the most interesting results to spot connections and guide next experiments.

---

## Highlights Doc

Use during exploration (and throughout) to capture “this seems important” results.

### Entry format

- Date:
- Setup/context:
- Observation/result:
- Why it seems interesting:
- Possible explanations:
- Follow-ups (ranked):
- Links (plots/notebooks/notes):

### Weekly synthesis

- Top 3 highlights this week:
- Emerging patterns / repeated anomalies:
- Hypotheses crystallizing:
- What to test next:

---

---

title: Hypothesis ↔ Evidence Map
tags: understanding, distillation, evidence, mapping
description: Map hypotheses/claims to supporting experiments, key risks, and missing discriminators.

---

## Hypothesis ↔ Evidence Map

Fill one row per hypothesis or claim.

| Hypothesis / Claim | Supporting evidence | Key baselines / sanity checks | Main alternative explanations | Missing discriminator | Confidence |
| ------------------ | ------------------- | ----------------------------- | ----------------------------- | --------------------- | ---------- |
|                    |                     |                               |                               |                       |            |
|                    |                     |                               |                               |                       |            |

### Notes

- Which row is weakest, and why?
- What single experiment would increase confidence the most?

---

---

title: Research Intake Template
tags: intake, context, constraints, artifacts
description: Minimal intake to diagnose stage and propose high-leverage next actions.

---

## Research Intake Template

Use this to quickly provide the context needed to run triage.

### Project snapshot (1–5 sentences)

- What are you trying to learn or build?
- Why does it matter (to you / to the field / to an application)?

### Current state

- What have you tried so far?
- What are the most important results (even if messy)?
- What is currently confusing or blocking you?

### Artifacts (if available)

- Links/snippets to:
  - plots
  - tables
  - notebooks
  - notes
  - draft text
  - experiment logs

### Constraints

- Deadline (if any):
- Compute / budget constraints:
- Scope constraints (what you will/won’t do):

### What you want from this session

Pick one:

- Decide what to do next (unstuck)
- Design experiments to test a hypothesis
- Stress-test results (baselines / alternative explanations)
- Distill into claims + evidence + limitations
- Improve research taste / reflection loop

---

---

title: Red-Team Template
tags: red-team, skepticism, distillation, truth-seeking
description: Systematically stress-test claims: alternative explanations, missing checks, and decisive discriminators.

---

## Red-team

**Target claim / conclusion:**

- Claim:

### What could I be missing?

- Missing factor 1:
- Missing factor 2:

### Alternative explanations

- Alternative A:
- Alternative B:
- Alternative C:

### Strongest boring explanation

- The simplest explanation that would make this uninteresting:

### What would change my mind?

- Evidence that would strongly falsify the claim:

### Discriminating experiments

For each alternative:

- Alternative:
- Quick discriminator experiment:
- Expected outcomes:

### Evidence quality audit

- Are there strong baselines?
- Are there ablations?
- Any cherry-picking risk?
- Any measurement artifacts?

### Decision

- Current confidence:
- Biggest remaining risk:
- Next test to reduce risk fastest:

---

---

title: Research Triage Output
tags: triage, prioritization, next-steps
description: Standard output for diagnosing research stage and deciding next actions.

---

## Research Triage Output

**Stage:**  
(Explore / Understand / Distill)

**North star:**  
(What progress means right now)

---

### Top uncertainties

1.
2.
3.

---

### Prioritized next actions

1. Action:
   - Why this?
   - Expected information/evidence:
2. Action:
   - Why this?
   - Expected information/evidence:
3. Action:
   - Why this?
   - Expected information/evidence:

---

### Fast-fail test

If this direction is wrong, what is the fastest way to find out?

---

### Alternative explanations / baselines to check

- …
- …
- …

---

### Notes

(Optional reflections, constraints, or risks)

---

---

title: Weekly Research Review Template
tags: prioritization, reflection, planning
description: Weekly zoom-out prompts for prioritization and learning from mistakes.

---

## Weekly review

### Goal alignment

- What is my goal right now?
- What is my sub-goal?
- What is my next objective (days)?

### Progress

- What progress did I make?
- What did I learn that changed my beliefs?

### Time audit

- What consumed the most time?
- Was it worth it? If not, what would I change?

### Blockers

- What blocked me?
- What’s the smallest action that would unblock me?

### Mistakes & system changes

- What mistakes did I make?
- How can I systematically change my approach to prevent them?

### Confusions

- What am I confused about?
- What’s the fastest way to reduce that confusion?

### Missing something?

- Am I missing an obvious alternative explanation?
- Did I skip a boring baseline?
- Is my stage classification correct?

### Plan

- Top 3 actions next week (ranked):
- What I will deliberately NOT do:

---
