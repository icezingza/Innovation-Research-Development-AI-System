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
