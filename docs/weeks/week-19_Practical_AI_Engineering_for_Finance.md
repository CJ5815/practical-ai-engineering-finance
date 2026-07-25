# Week 19: Reading — Loops, Expertise, and Self-Evolving Skills

**Course:** Practical AI Engineering for Finance  
**Audience:** Senior undergraduate students  
**Schedule:** 1 hour per day, 4 days per week  
**Week Theme:** Three recent papers on agentic AI engineering, read against this course's own `sec_thesis` CLI (Week 18) and `investment-philosopher` skill (Week 17)

---

## Week Overview

Weeks 17 and 18 built two real artifacts: a Value Investor skill that forms an investment thesis, and `sec_thesis`, a standalone CLI that fetches and indexes SEC filings under a written set of engineering rules (`src/sec_thesis/CLAUDE.md`). This week steps back and reads three papers that describe, at a level above any one line of code, what those artifacts could become — an autonomous loop, a system whose real bottleneck is the user's domain expertise rather than their coding skill, and a skill document that improves itself under the same discipline as a machine learning training loop.

None of this week's papers are abstract theory disconnected from what you've built. Each one maps onto a specific file already in this repository — `src/sec_thesis/CLAUDE.md`'s fifteen rules, `.claude/skills/investment-philosopher/SKILL.md`, or your own transcript of Claude Code sessions this semester. Finding those mappings *is* the assignment.

All three papers are included in full under `docs/resources/papers/` — read them there, not just the summaries below.

---

## Contents

- [Learning Objectives](#learning-objectives)
- [Weekly Schedule](#weekly-schedule)
- [Day 1: Loop Engineering](#day-1-loop-engineering)
- [Day 2: Agentic Coding and Persistent Returns to Expertise](#day-2-agentic-coding-and-persistent-returns-to-expertise)
- [Day 3: SkillOpt](#day-3-skillopt)
- [Day 4: Synthesis and Reflection](#day-4-synthesis-and-reflection)
- [Week 19 Reflection](#week-19-reflection)
- [Key Terms](#key-terms)
- [Week Summary](#week-summary)
- [The Papers](#the-papers)

---

# Learning Objectives

By the end of Week 19, you should be able to:

- Explain Loop Engineering's five moves (discovery, handoff, verification, persistence, scheduling) and identify which of `sec_thesis`'s existing rules already implement each one.
- Explain why the "Agentic Coding and Persistent Returns to Expertise" study found that domain expertise, not coding background, predicts success with Claude Code — and what that implies for how you use it this semester.
- Explain SkillOpt's core idea (a skill document as a trainable artifact, edited under a bounded, validation-gated loop) and describe one concrete way it could improve the `investment-philosopher` skill.
- Connect all three papers to specific files in this repository, not just to the abstract concepts they describe.

---

# Weekly Schedule

| Day | Topic | Main Deliverable |
|---|---|---|
| Day 1 | Loop Engineering | Notes mapping the five moves onto `sec_thesis` |
| Day 2 | Returns to expertise | A self-assessment against the paper's expertise rubric |
| Day 3 | SkillOpt | Notes comparing SkillOpt's loop to `investment-philosopher` |
| Day 4 | Synthesis | `week19_reflection.md` |

Each class follows the same session structure as prior weeks: review, new concept, guided practice, testing/discussion, and committing the work — except "testing" this week means "does my reflection actually cite a specific file," not `pytest`.

---

# Day 1: Loop Engineering

## 1.1 The Core Claim

*Loop Engineering* (the paper walks through Addy Osmani's, Peter Steinberger's, and Boris Cherny's independent June 2026 formulations of the same idea) argues that prompt, context, and harness engineering all still assume a human sits at the keyboard, directing an agent turn by turn. **Loop engineering removes that assumption**: instead of prompting the agent, you design the system that prompts it.

```text
Prompt engineering   -> the words you write for the model
Context engineering   -> what goes in the window right now
Harness engineering   -> arming a single run: tools, actions, "done"
Loop engineering      -> scheduling on the harness: make it run itself, over and over
```

## 1.2 The Five Moves

A single turn of a loop is five moves, and the paper's central diagnostic tool is that **every loop failure is exactly one of these five moves, skipped**:

| Move | What It Does | Skipped → |
|---|---|---|
| Discovery | Finds what this turn should do | The Blind Loop (a human still hands it the work) |
| Handoff | Hands the task to an isolated agent | The Tangled Loop (parallel agents collide) |
| Verification | An independent check that can say "no" | The Nodding Loop (the agent grades its own homework) |
| Persistence | Writes state outside the conversation | The Amnesiac Loop (no cumulative progress) |
| Scheduling | A real trigger, not a human remembering | The Manual Loop (works once, then silently stops) |

## 1.3 Why the Evaluator Is the Hard Part

The paper's sharpest empirical claim, credited to Anthropic engineer Prithvi Rajasekaran: an agent asked to grade its own output tends to praise it, even when the quality is mediocre — not because it's unintelligent, but because the context it wrote the code in is already full of the reasons it made those choices. The fix is structural, not a better prompt: a **separate** evaluator agent, defaulting to doubt, that verifies by *acting* (running tests, clicking through a UI) rather than just reading code and pattern-matching "looks right."

## 1.4 Mapping the Five Moves onto `sec_thesis`

This is the exercise, not just the reading. Open `src/sec_thesis/CLAUDE.md` side by side with the paper and find the moves already there:

- **Persistence** is not hypothetical — `storage/filings_db.py`'s DuckDB filing index *is* "memory... a markdown file or a board... the agent forgets, the repo does not," in the paper's own words, just implemented as a database table instead of Markdown.
- **Rule 11**, "Never overwrite previous thesis versions," is the paper's "Stop" section made concrete: *"Never merge. Never delete. Anything you are less than confident about goes to `./inbox/` for a human."*
- The **Required Quality Controls**' last line — *"Human approval before changing conviction or issuing a recommendation"* — is precisely the paper's "keep one door open" principle: a checkpoint that exists not because a human will always intervene, but because its existence keeps a human *able to*.
- **Rules 6–7** (deterministic Python for calculations; an LLM only for classification, extraction, comparison, synthesis) mirror the paper's account of Stripe's Minions pipeline: interleave deterministic gates and creative LLM steps, and keep anything rule-bound out of the probabilistic model.
- What `sec_thesis` does **not** yet have is **discovery** and **scheduling** — nothing currently decides on its own to check for new filings, and nothing runs it on a timer. That gap is this week's discussion question, not a coding assignment.

## Day 1 Activity

Read Sections I–VI of the paper. In your notes, name one `sec_thesis` rule or file for each of the five moves — and explicitly note that discovery and scheduling are still missing.

---

# Day 2: Agentic Coding and Persistent Returns to Expertise

## 2.1 The Core Claim

This Anthropic report analyzes roughly 400,000 real Claude Code sessions and asks a direct question: **does coding background matter more than domain expertise for succeeding with an agent?** The answer is no. On coding tasks, every major occupation succeeds at nearly the software engineers' own rate. What predicts success instead is **domain expertise at the specific task** — and that's *task-specific*, not a job title: "an accountant who has never used Python, but tells Claude exactly which reconciliation rules a Python script must enforce... is an expert at that task."

## 2.2 The Division of Labor

Across sessions, people make about 70% of *planning* decisions (what to do, what counts as done) while Claude makes about 80% of *execution* decisions (which files, what code, which commands). The more expertise a person brings, the more work Claude does per instruction — expert sessions trigger action chains more than twice as long as novice sessions, carrying five times the output.

## 2.3 The Expertise Rubric

The paper rates users on a five-point scale by three signals: how precisely they frame directions, what they ask Claude to verify, and whether they correct Claude or Claude corrects them.

| Level | Signal |
|---|---|
| 1 (Novice) | Generic requests; no domain nomenclature; doesn't recognize Claude's errors |
| 2 (Beginner) | Some domain terminology; untargeted verification |
| 3 (Intermediate) | Some domain specificity; asks for non-generic checks |
| 4 (Advanced) | Domain knowledge; anticipates tradeoffs; catches at least one domain mistake |
| 5 (Expert) | Sophisticated domain jargon; precise, targeted verification; rarely corrected by Claude |

Expert-rated sessions reach the paper's strictest "verified success" measure more than twice as often as novice sessions — but most of that gap is between novice and intermediate; intermediate-to-expert is a much smaller step. In plain terms: **competence, not mastery, captures most of the benefit.**

The table above is a condensed summary. The [paper's appendix](../resources/papers/agentic-coding-returns-to-expertise-appendix.pdf) has the actual classifier prompt used to produce it — the full text behind each level, plus the three signals it weighs (setup specificity, verification type, direction of correction). Use the appendix's real rubric for Day 2's activity, not the summary table, if you want the exact standard the paper's researchers applied.

## 2.4 Why This Matters for This Course

This finding is the whole course's premise, stated as an empirical result instead of a marketing claim. You are not a professional software engineer. You are (or are becoming) a finance domain expert. The paper's data says that's the thing that predicts whether Claude Code sessions succeed — not your prior coding background. Every week of this course has been building the domain-specific *and* technical vocabulary that lets you frame precise requests and verify Claude's output like a finance professional, not just a novice programmer.

## Day 2 Activity

Pick two or three of your own Claude Code sessions from this semester (any week). Rate each against the appendix's actual "User expertise" classifier prompt (§2.3), honestly. Note one thing you'd frame more precisely, or verify more specifically, next time.

---

# Day 3: SkillOpt

## 3.1 The Core Claim

SkillOpt (Microsoft, with several university co-authors) starts from a specific gap: skills today are hand-written, generated once, or revised ad hoc — none of that behaves like a deep-learning optimizer, and none of it *reliably improves over its starting point under feedback*. Their proposal: treat the skill document itself as a trainable object, with an explicit analogy to weight-space optimization.

```text
skill document            -> parameter
trajectory-derived edit    -> gradient direction
edit budget                -> learning rate
held-out selection gate    -> validation check
```

## 3.2 The Loop

A separate optimizer model reads scored trajectories (successes and failures), proposes bounded `add`/`delete`/`replace` edits, and — this is the load-bearing step — **a candidate skill is accepted only if it strictly improves a held-out validation score.** Rejected edits aren't thrown away; they're kept as negative feedback so the optimizer doesn't repeat them. Across six benchmarks and seven models, this beat every baseline the authors tried, including hand-written skills, on all 52 evaluated cells.

## 3.3 Why Bounded and Gated, Not Free-Form Rewriting

Two design choices do most of the work, and both should sound familiar from this course's own testing philosophy (Weeks 3–5):

- **Bounded edits** (a textual "learning rate") prevent one bad reflection from erasing a working rule — the same reasoning behind small, reviewable commits instead of one giant rewrite.
- **The validation gate** is exactly train/validation/test discipline, applied to a prompt instead of a model: never accept a change on the same data you used to propose it.

## 3.4 Comparing SkillOpt to `investment-philosopher`

Week 17 built `.claude/skills/investment-philosopher/SKILL.md` as a **fixed** skill — written once, never revised against evidence. SkillOpt describes what Phase 2 of that skill could look like:

- **Rollout evidence** would be past runs of the Value Investor skill against real filings with a known, checkable outcome (did the bull/bear catalysts the skill identified actually happen?).
- **The held-out validation set** would be companies the skill was never tuned against — exactly the train/test split discipline `tests/test_value_investor.py` already uses for the underlying Python functions, just applied one level up, to the prompt itself.
- **Bounded edits** would mean small, reviewable changes to the skill's instructions, not a full rewrite after one bad thesis.
- This is also where SkillOpt's own limitation applies directly: it works best "when the target task has automatic verifiers, exact-match metrics, executable checks, or otherwise reliable feedback" — and a good investment thesis is judged over months or years, not exact-matched in a test suite. That gap is worth taking seriously, not glossing over.

## Day 3 Activity

Read Sections 1–3 of the paper. Write down what a held-out validation set for `investment-philosopher` would actually consist of, given that (unlike SkillOpt's benchmarks) there's no same-day exact-match answer for "was this thesis right."

---

# Day 4: Synthesis and Reflection

## 4.1 One Picture, Three Papers

Read together, the three papers describe one coherent next step for this course's own architecture, not three unrelated ideas:

- **Loop Engineering** supplies the *scaffolding*: discovery, handoff, verification, persistence, scheduling — the shape a `sec_thesis` automation would need.
- **Returns to Expertise** supplies the *justification for who should design it*: a finance domain expert directing Claude precisely produces better results than a strong coder directing it vaguely — so the person best positioned to design `sec_thesis`'s discovery logic (what's worth investigating) is someone with investment judgment, not just Python skill.
- **SkillOpt** supplies the *verification mechanism* for the loop's hardest move: instead of a human manually deciding whether `investment-philosopher`'s output improved, a held-out validation gate could do it automatically, the same way `pytest` already does for `analysis.py`'s ratio calculations.

## 4.2 Optional Design Sketch

Not required code — a paragraph is enough. Sketch what a `sec-thesis` loop's five moves would look like if you built them: what triggers discovery (a schedule checking for new filings?), what the evaluator would need to verify beyond "the code ran" (did the extracted numbers match the actual filing?), and where the human-approval checkpoint from `CLAUDE.md`'s Required Quality Controls would sit.

## Day 4 Activity

Write the required reflection (below) and discuss: which of the three papers most changes how you'll use Claude Code for the rest of this course?

---

# Week 19 Reflection

Write 250–350 words answering:

1. Pick one rule from `src/sec_thesis/CLAUDE.md` and explain which Loop Engineering move it implements, and why.
2. Rate one of your own Claude Code sessions against the expertise paper's five-point rubric. What would move it up a level?
3. Describe one concrete, bounded edit you'd propose to `.claude/skills/investment-philosopher/SKILL.md`, and what evidence would have to exist before a SkillOpt-style gate should accept it.
4. Which of the three papers most changes how you'll work with Claude Code for the rest of this course, and why?

Save as:

```text
week19_reflection.md
```

---

# Key Terms

| Term | Definition |
|---|---|
| Loop | A system that discovers, does, verifies, persists, and reschedules work without a human in the inner cycle |
| Discovery / Handoff / Verification / Persistence / Scheduling | The five moves of one turn of a loop |
| Generator / Evaluator separation | Splitting the agent that writes from a separate agent that judges, to avoid self-grading bias |
| Domain expertise (task-specific) | Precise, verifiable knowledge of the specific task at hand — not a job title or general coding skill |
| Verified success | This course's Week 19 papers' term for an outcome with both a positive judgment and hard evidence (passing tests, committed work) |
| Text-space optimization | Treating a natural-language artifact (a skill document) as a trainable object, edited under bounded, validation-gated updates |
| Held-out validation gate | Accepting a change only if it improves performance on data not used to propose the change |
| Bounded edit / textual learning rate | Limiting how much a skill document can change in one update, to preserve continuity |

---

# Week Summary

During Week 19, you:

- read *Loop Engineering* and mapped its five moves onto `sec_thesis`'s existing rules and files;
- read Anthropic's *Agentic Coding and Persistent Returns to Expertise* and self-assessed your own sessions against its expertise rubric;
- read *SkillOpt* and compared its bounded, validation-gated editing loop to the (currently fixed) `investment-philosopher` skill;
- connected all three papers to specific parts of this repository, not just to abstract concepts;
- wrote a reflection synthesizing what these papers suggest for the project's next phase.

---

# The Papers

All three are included in full, alongside this week's lesson:

- [Loop Engineering: The Anthropic Playbook for Designing Systems That Prompt Your Agents](../resources/papers/loop-engineering.pdf)
- [Agentic Coding and Persistent Returns to Expertise](../resources/papers/agentic-coding-returns-to-expertise.pdf) (Anthropic), with its [appendix](../resources/papers/agentic-coding-returns-to-expertise-appendix.pdf) — the full classifier prompts (work mode, user expertise, occupation, session outcome, success/failure signal) and the regression tables behind Section 4
- [SkillOpt: Executive Strategy for Self-Evolving Agent Skills](../resources/papers/skillopt.pdf) (Microsoft et al.)

---

# Next Week

Week 19 is the most recent addition to this course. There is no Week 20 yet — a natural next step, following directly from this week's synthesis, would be an optional Phase 2 for `sec_thesis`: adding discovery and scheduling (Loop Engineering, §1.4) and a first validation-gated revision loop for `investment-philosopher` (SkillOpt, §3.4).
