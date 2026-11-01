---
name: paper-review
description: "LaTeX 论文投稿前的写作与审阅，尤重 IEEE / IEEEtran 会议论文。写作侧：定故事线、先大纲后成文、分节模板、段落角色与反向大纲、claim-evidence 对齐、五维对抗式自审、逐条核实引用是否真实存在。审阅侧：句级语法与逻辑、术语与缩写一致性、引用编号与参考文献完整性、图表编号与正文顺序、单位与冠词、LaTeX 静态健康（非 ASCII / 花括号 / \text{} 里的数学命令）、页数与版面、图内文字与正文冲突、以及「提交的 PDF 是否真由当前源码编出」。Triggers: 改论文, 审论文, 润色论文, 论文结构, 重写某节, 查引用, 检查 LaTeX, 编译不过, 页数超了, 图表编号, IEEEtran, proofread paper, review paper, revise paper, page limit, stale bbl."
---

# Paper Review

## Overview

There are two halves to pre-submission work, and this skill covers both. **Review** a LaTeX paper the
way a hostile but fair reviewer would, then fix what is fixable without touching the template: the
failure modes that survive to submission are rarely typographical — a subject that does not match its
predicate, an acronym defined at its third appearance, a figure numbered out of order, a reference
list that silently renumbered, a build error caused by one math command in a text-mode argument, a
claim with no evidence behind it. **Write and revise** with the same criteria used the other way round:
to generate rather than to detect — pin the paper's story, outline before prose, draft section by
section, then audit your own draft adversarially. Both halves share two hard constraints: every claim
must map to evidence, and every citation must really exist.

## When to use

Review track:

- Review / audit / proofread a paper, or a section of one, before submission.
- Answer "is this sentence right?", "what is the subject here?", "should this be `a` or `an`?".
- Check consistency of a term or acronym across abstract, body and keywords.
- Reorder figures or verify that figure numbering matches the order the text cites them.
- Diagnose page count over the limit, or a missing figure, or cascading LaTeX errors.
- Produce a defect list with severity, for someone else to act on.
- Confirm the submission-side facts before upload: review mode (anonymous or not), page limit,
  funding list, author-name style.

Writing track:

- Draft a paper, a section, or an abstract from notes, data or a rough draft.
- Restructure a draft whose sections do not build on each other, or whose contribution is buried.
- Rewrite a paragraph, an introduction, or a related-work section that reads as a list.
- Map the claims in the abstract and introduction to the evidence actually in the paper.
- Run an adversarial self-review before sending the draft to an advisor or a venue.
- Verify that every reference is real, traceable and formatted consistently.

Most real tasks use both tracks: write or revise in the writing track, then prove it in the review
track. Say which one you are in before you start.

The paper is usually under version control with a companion `<name>.log.md` change log. Read the log
first: it records earlier decisions and the reasons for them, including terms that must **not** be
changed again.

## Workflow

### Step 0 — Establish the state before changing anything

1. Run `git status` and report any uncommitted work, including changes staged by someone else.
2. Identify the authoritative source. A working copy on the desktop and a repository copy can differ;
   never assume which is newer. Compare with `sha256` and trust content over location.
3. Read the change log (`main.log.md` or equivalent) for decisions already settled.

### Step 0b — Local compile environment

> 本机（ZCode 工作机）实测：TeX Live 2026 已装于 `D:\Software\texlive\2026\bin\windows`，
> pdflatex / xelatex / bibtex / booktabs / subfig 等齐全，**无需 --install**；check_layout 所需
> PyMuPDF 已装（miniconda python）。直接跑 `check_env.py` 报一遍即可确认。

Estimates are not results, so aim for a local compile. Check the toolchain before promising a page
count:

```
python scripts/check_env.py --need subfig,dblfloatfix,algorithmic,cite,booktabs
```

Reports which engines exist (`pdflatex` / `xelatex` / `lualatex` / `latexmk`), the absolute path of
each, and whether the listed packages resolve. **Exit code 1 means unusable** — do not tell the
author to compile until this passes.

If nothing is installed, install a portable TeX Live with no elevation and outside the system drive:

```
python scripts/check_env.py --install --scheme small --extra subfig,dblfloatfix,algorithmic
```

Unattended, roughly 300 MB, into `--texdir` (defaults to a non-system drive), with
`instopt_adjustpath 0` so PATH is not touched — the script prints the absolute binary paths to call.
State the download size to the author before running it. Engine choice matters: **`pdflatex` for
English/IEEE work**, **`xelatex` plus `ctex` and the bundled Fandol fonts for Chinese**. Both engines
come from the same TeX Live; there is no separate "Chinese LaTeX".

Fix the build sequence before trusting any number. If the bibliography is driven by `.bib`
(`\bibliography{...}`, no hand-written `thebibliography`), **every measurement must come from four
passes — `pdflatex → bibtex → pdflatex → pdflatex`**. A `pdflatex`-only run silently reuses whatever
`main.bbl` is already sitting in the directory, so a `.bib` fix appears to do nothing. Delete
`main.bbl` before the first build when in doubt, and read `main.blg` for the warning count.

### Step 1 — Static health

```
python scripts/check_paper.py main.tex --bib references.bib --figdir figures
```

Reports non-ASCII characters, brace balance, `$` parity, environment pairing, missing
`\includegraphics` files, math-only commands inside `\text{}`, bibliography order versus first
citation, literal `[17]`-style citations, figure/table numbering versus reference order, duplicate
acronym expansions, `a`/`an` before numbers, and bare spaces between number and unit.

A `FAIL` is a rule that is definitely broken. A `WARN` needs a human decision. Fix every `FAIL`
before continuing.

### Step 2 — Sentence-level review

Work sentence by sentence, never in bulk. For each sentence decide whether the **subject** can carry
its predicate, whether both sides of a contrast belong to the same category, and whether every
participle clause has somewhere to attach. The catalog of failure modes with worked examples is in
`references/cases.md` (items 1, 2, and the D section of the checklist).

Present findings as a menu: quote the original, state the defect, offer two concrete rewrites,
and let the author choose. Do not rewrite the whole paragraph on your own initiative.

### Step 3 — Terminology and acronyms

Treat the **abstract, the keyword list and the body as three independent regions**: an acronym may be
expanded once in each, because a reader who only sees the abstract never sees the body's definition.
Two expansions inside one region is the defect, not two across regions. A consequence worth stating
out loud to the author: the body may not lean on the abstract's definition, so an acronym expanded
only in the abstract still needs its full form at its first use in the body.

Then check for terms that are similar in form but different in meaning, where a global replace would
destroy the sense.

`references/checklist.md` section A carries the criteria; item 5 of `references/cases.md` is the
worked case where a global replace would have been wrong.

### Step 4 — Citations and bibliography

Verify that `\bibitem` order equals the order of first citation, that every entry is cited and every
citation has an entry, and that no literal number appears in the body. Before adding a citation,
compute where its first appearance would fall: inserting in the middle of the bibliography
renumbers everything after it.

If a `.bib` file exists alongside a hand-written `thebibliography`, it is a second source of truth
and will drift. Either delete it or rebuild it as an explicit mirror of the paper's list.

When the bibliography is driven by `.bib` + `IEEEtran.bst` (v1.14), audit five `.bib` traps that
produce broken or non-compliant output without raising a BibTeX error:

- **Never hardcode `and others` (`et al.`) in `.bib`.** Write out the complete author list from the
  publisher record. `IEEEtran.bst` (`names.max = 6, names.min = 1`) automatically prints all authors
  when $\le 6$ and truncates to `First Author et al.` when $\ge 7$, matching the IEEE template rule.
- **Electronic article numbers (`Art. no.`) must not sit bare in `pages`.** A single number like
  `pages = {103316}` or `pages = {378}` (no `--` range) is rendered by `IEEEtran.bst` as `p. 103316`
  (a single page). Use `note = {{Art. no.} 103316}` (or `pages = {{Art. no.} 103316}` when `pages`
  is otherwise empty); for IEEE journals that have both a page range (`1--14`) and an article ID
  (`5517414`), keep `pages = {1--14}` and add `note = {{Art. no.} 5517414}`. Always wrap `{Art. no.}`
  in braces so `IEEEtran.bst` does not lowercase `Art.` to `art.`.
- **Do not duplicate `author` and `organization` in `@manual`.** `IEEEtran.bst` prints both fields
  for `@manual`, so putting `European Space Agency` or `JEDEC` in both prints the agency name twice
  in the same reference. Put the agency in `organization` (or `author`), not both.
- **Use `url = {https://...}` for online manuals.** `IEEEtran.bst` formats `url` as
  `. [Online]. Available: https://...`, matching the IEEE conference template.
- **Sync any companion reference ledger (e.g., `docs/文献引用对照清单.md`).** Check that placeholder
  DOIs (`xxxxxxx`), wrong DOIs, or stale page ranges (`pp. 1--7` vs. `pp. 1--6`) are updated in lockstep.

### Step 5 — Figures and tables

Rendered numbers follow the order the float environments are declared, not the order they land on
the page. Check both directions: declaration order must produce the numbering, and the text's
`\ref` sequence must be non-decreasing starting at 1. Adding a float at the top of the sequence
breaks both at once.

Report figure identity as "rendered number + filename + first line of the caption" so the author can
match it against what they see in the PDF.

### Step 5b — The text *inside* the figures is part of the paper

Extract the text layer of every figure PDF and diff its terms and numbers against the body:

```python
import fitz, re
t = re.sub(r"\s+", " ", " ".join(p.get_text() for p in fitz.open("figures/fig5.pdf")))
```

No source-level check can see this, and it catches two real defect classes:

- **Term split.** The body was changed to `partial power collapse` while the panel still says
  `asymmetric`. Words baked into a figure cannot be fixed by editing LaTeX — the figure has to be
  re-exported, so report this as its own class: *needs a new figure export*, not *needs a wording fix*.
- **Numbers that exist only inside a figure.** A value printed in a panel but never defined in the
  body (`60.5 W` alongside a body that only ever quotes input power) leaves the reader unable to
  trace it. Either define it in the text or label the basis inside the panel.

Run this for every figure whose labels carry words rather than units.

### Step 5c — Statement strength must be uniform

Collect every place one claim is made — abstract, contribution list, the section, both figure
captions, the text inside the figures, the conclusion — and check that they hedge to the same degree.
A body that says *we attribute* / *consistent with* next to a panel asserting *Converged Root Cause*
reads as an overclaim, and a reviewer will quote the stronger one back at you. This sweep is also the
cheapest guard against a half-finished terminology change: a narrative fix typically lives in six or
more spots, and fixing three of them is worse than fixing none.

### Step 6 — Layout and page limit

Measure before cutting. Work out the placement height from the figure's aspect ratio and the width
factor, convert to column-inches, and compare against the page budget. Treat that arithmetic as
directional only; the page count must be confirmed by a real compile.

Reduce cost in this order: delete redundant content, shrink or recompose figures, tighten float
widths, relax placement specifiers, and only then revisit any `\topfraction` / `\textfraction`
override that was added for full-width floats. Never change line spacing, font size or margins —
conference templates forbid overriding the default typesetting, and that is a rejection risk.
Details and the arithmetic are in `references/latex-ieee.md`.

🔴 The page budget is a **step function, not a length**. Measured on one 6-page paper: a two-word
deletion in the conclusion flipped it to 7 pages; a word-neutral rewrite of that same sentence also
flipped it; a five-word addition elsewhere was free. So:

- Never predict a delta, in either direction. Apply the edit to a scratch copy, compile, count.
- When an edit flips the count, do not drop it — look for a **comparable trim in the same paragraph
  or region** and land the two together. Edits that each flip alone are frequently free as a pair,
  because the paragraph re-breaks as a whole.
- Know the sensitive regions: the conclusion's final paragraph, the abstract/keywords block at the
  top of page 1 (it wraps, and one extra wrapped line costs a page), and any paragraph whose last
  line already ends on a column break.
- **A figure re-export can cost a page with no text change at all.** Aspect ratio sets the printed
  height; re-measure after every figure replacement, and measure the width threshold rather than
  computing it (on one instance `0.72` and `0.70` were still 7 pages; `0.68` and `0.66` gave 6).
  Shrinking the width to absorb a taller figure also shrinks the in-figure type — prefer re-designing
  the panel to a wider aspect.

### Step 6b — Verify against a real compile

Estimates are not results. Ask the author for the compiled PDF and measure it:

```
python scripts/check_layout.py paper.pdf --verify "<a string only the latest revision has>"
```

`--verify` first, because a PDF of the wrong revision invalidates everything else: pick a token that
changed in the revision under review (a corrected grant number, a renamed label) and confirm it is
present. Then read: page count, per-column bottom margin, and the **spread of gaps before headings**.

A blank gap is abnormal or not only relative to the same document's own distribution — never against
an absolute threshold. A gap in the middle of a column with nothing in the source at that point is a
float artifact, and the test is to comment out the full-width float and recompile.

Two further checks belong here, because "the artifact is current" is not something to assume — a
submission PDF that looked fine was in fact built from a source two edits old, and both packages
were 37 minutes behind:

- **Freshness, proven three ways.** (1) Compare the artifact's mtime against *all* inputs, source and
  every figure. (2) Rebuild from the current source in a scratch directory and compare the extracted
  text — identical text means the artifact *is* that revision. (3) For a package, hash-compare every
  entry against the working tree, per file; "I rebuilt it a moment ago" is not evidence.
- **Normalise before comparing text.** Strip whitespace *and* line-end hyphens. Otherwise a
  line-broken word (`mea-\nsured`) reads as a missing string and you report a false defect.
- **Fonts.** A submission PDF must have every font subset-embedded (names carry an `ABCDEF+` prefix).
  A font name without that prefix is one the venue's PDF checker may reject.

Report page count, bottom margin and the abnormal-gap verdict as measured numbers, and say which
items still need an author decision.

### Step 7 — Land the changes and report

For each edit: apply it, re-run Step 1, append an entry to the companion log (before text, after
text, reason, verbatim self-check data, scope), rebuild the submission package, and commit by
logical unit. Then confirm the commit contains only the intended files.

Write each edit as a script file with assertions — anchor occurs exactly once, expected page count,
no forbidden string survives, output files byte-identical where expected — and run that. Inline
`python -c` one-liners have eaten backticks and quotes here, silently corrupting a change log entry
while still reporting success — and in this machine's cmd shell, a multi-line `python -c` additionally
loses stdout silently (you don't even see the success print), so always write a `.py` file and run it.
Hash comparisons on this machine: `certutil -hashfile <file> SHA256` (cmd) or `sha256sum` (Git Bash).

Keep build artifacts out of the package: `main.aux`, `main.log`, `main.out`, `main.toc`, `main.pdf`,
`missfont.log` — **and `main.bbl` / `main.blg`**. A stale `main.bbl` shipped next to `references.bib`
silently overrides it whenever the venue compiles without rerunning bibtex. Note that `.gitignore`
often covers `main.aux` and `main.pdf` while missing the `.bbl`/`.blg` pair, so they show up as
untracked files and get mistaken for pending work.

If the repository has more than one line of work in it, check `git status` immediately before
committing and stage by explicit pathspec: never sweep another line's modified figures into your
commit, and leave their uncommitted work exactly as you found it. The same applies to a shared
package — rebuilding it is fine, committing it on their behalf is not.

Report as a before/after table plus the self-check numbers. State explicitly which items could not be
verified without a real compile, and list anything deliberately left unchanged and why.

### Step 8 — Submission metadata and compliance

The items in `references/checklist.md` section I decide whether the paper *can* be submitted; static
checks never see them.

- **Review mode.** If the call for papers is unreachable, use the Wayback CDX API (case 23). Two
  independent sources must agree before you conclude; state the sources and their dates. If the venue
  is anonymous, the submitted PDF must not name authors or affiliations — and the funding
  acknowledgement has to go too, since it identifies the institution.
- **Page limit** from this venue's own call, not from another conference's habit.
- **Funding.** Compare the current list against *all* historical versions, not just the last commit;
  the current list is often not the union. Whether to restore a dropped grant is the group's call,
  not yours.
- **Names.** Byline in mixed case; `SURNAME, INITIALS` is IEEE Xplore's rendering, not a style to
  type.
- **Deadline** converted to the author's time zone, plus any hard action such as marking the
  submission ready for review.

Report these as a short table with what is confirmed and what is still open.

## Writing and revising track

Use these steps when the deliverable is prose rather than a defect list. Templates and rubrics live in
`references/writing.md`; what follows is the order of operations.

### Step W1 — Fix the story before the first sentence

Answer five questions in writing: what task is solved, why prior approaches fall short (**the technical
reason**, not "it is not accurate enough"), what the core challenge is, how the solution works in one
sentence, and what the extra contributions are. Then choose the contribution type — new task / new
metric / new technical challenge / new method / new finding — and do not change it mid-paper. A story
settled late costs a rewrite of more than the introduction.

### Step W2 — Mini-outline, 3–7 bullets

One bullet = one claim plus the evidence that supports it. Only then expand into prose. Do not open
with a naive baseline and then improve it; let the challenge appear first and present the method as the
response to it.

### Step W3 — Draft section by section, with roles

Follow the templates in `references/writing.md` §3. Label each paragraph's role as you write —
opening / challenge / method / advantage / evidence / limitation. A paragraph whose role cannot be
named is either two paragraphs or none.

### Step W4 — Reverse-outline the draft

Copy each paragraph's first sentence into a list, compare that list against the intended outline, then
check that the evidence inside each paragraph supports its own topic sentence. Paragraphs that do not
map cleanly get revised or deleted. This is the fastest structural check available, and it works on
someone else's draft too.

### Step W5 — Claim-evidence alignment

Extract every claim from the abstract and introduction into the table in `references/writing.md` §6:
claim (verbatim) | evidence (which figure, number or citation) | supported or needs evidence.
Assertive wording is allowed only for `supported`; anything resting on simulation alone must say so
(measured and simulated results must never merge in prose); a claim with no evidence gets softened or
cut. This step is what keeps a reviewer from finding an overclaim you would otherwise have shipped.

### Step W6 — Adversarial self-review

Read the paper as the reviewer who wants to reject it, and score five dimensions — contribution,
clarity, experimental strength, evaluation completeness, soundness of the design (§7 of
`references/writing.md`). Mark each one `pass / needs revision / needs new experiment`. Items needing a
new experiment cannot be fixed with wording and must be reported to the author as such.

### Step W7 — References must be real

Never write a citation you cannot verify. Query the Crossref REST API
(`https://api.crossref.org/works/<doi>` or `?query.bibliographic=...`) and publisher records
(IEEE Xplore, ScienceDirect, SpringerLink, MDPI, AIAA, ESA ESCC, JEDEC) to verify every entry's
complete author list, exact title, venue abbreviation, official volume/issue publication year
(updating Early Access years once assigned to a volume), page range or electronic article number
(`Art. no.`), conference location/month, and DOI. Mark anything you cannot confirm as `[待核实]` for
the author rather than supplying a plausible-looking author or year. Formatting is then checked
mechanically in Step 4.

Output convention for this track: the 3–7 bullet outline first, then the revised text with each
paragraph's role labelled, then the claim-evidence table, then a short self-check list covering
clarity, flow, terminology, unsupported claims and missing evidence.

## Reporting format

```
改前 → 改后 table, one row per change
校验: <verbatim output of the static check>
落盘: log entry, package rebuild, commit hash + file scope
仍需确认: <items needing a real compile or an author decision>
刻意未动: <with the reason, so it is not "fixed" again later>
```

## Red lines

- Do not change line spacing, font size or margins. Template compliance outranks a page limit.
- Do not apply a global replace before reading every occurrence in context.
- Do not reorder or renumber figures without re-running the numbering and reference-order checks.
- Do not "unify" a term that appears in the change log as deliberately kept.
- Do not claim a page count or a layout outcome without a real compile; label estimates as estimates.
- Do not edit more than the author asked for without flagging it explicitly and offering a one-word
  revert.
- Do not edit a formal `.md` with a tool that normalises Markdown; it will rewrite `~`, `\_` and
  every table in the file. Write the file directly and check the diff line count afterwards.
- Do not predict a page-count delta, in either direction. Measure it — and when a measured edit flips
  the count, try the paired trim before reporting it as unaffordable.
- Do not report a defect produced by your own tooling before checking the tool. Position indices,
  unescaped regex metacharacters and PDF hyphenation have each produced false positives here;
  corroborate with a second, independent route.
- Do not assume one place holds a claim. A corrected causal statement typically lives in six or more:
  abstract, contribution list, the section, both figure captions, the text inside the figures, the
  conclusion. Sweep them in one pass, then re-check numbering.
- Do not treat the text as finished while a figure still disagrees with it. Figure-internal wording
  needs a new export — a different owner, and a different deadline.
- Do not decide funding attribution, anonymity handling or author-name style on the author's behalf.
  Present the evidence and the options; those are their calls.
- **Never invent a citation, a number or a result.** A reference you cannot verify gets marked for the
  author, not filled in with a plausible author and year; a claim with no evidence gets softened or
  cut. Polishing must not change a claim's strength — turning `may` into `does`, or `consistent with`
  into `caused`, is fabrication rather than editing, and the reverse (flattening a supported claim into
  a vacuous sentence) is its own kind of damage.
- Do not let simulated results read as measured ones. When the evidence behind a claim is simulation,
  the sentence has to say so.
- When asked to rewrite, propose the outline first and get it approved. Restructuring silently turns a
  requested polish into an unrequested rewrite.

## Resources

- `scripts/check_env.py` — read-only LaTeX environment report (engines, versions, package
  resolution, the exact binary paths, exit code usable as a gate). `--install` is the only mode that
  downloads or writes anything: a portable, no-elevation TeX Live into a non-system drive.
- `scripts/check_paper.py` — read-only static checker on the LaTeX source. Never writes, never uses
  the network.
- `scripts/check_layout.py` — read-only layout forensics on a **compiled PDF**: per-column blank
  space, the spread of gaps before headings, where each float landed and whether it is full width,
  reference numbering, and a revision-consistency check. Needs PyMuPDF (本机已装). `--verify` miss
  exits 1, so it can gate a build script; a missing/corrupt PDF exits with a one-line error.
- `references/checklist.md` — the full checklist by dimension (terminology, citations, figures,
  sentence-level grammar, numbers and units, LaTeX health, layout, process), each item with its
  criterion and a note on whether it can be automated.
- `references/cases.md` — thirty-one real defects generalised into patterns, with how to
detect each. Cases 26–31 cover the layers the source cannot show: a stale `.bbl`, wording baked into
figure PDFs, a half-stated mechanism, a claim living in six places, a package that lags its source,
and `.bib` / `IEEEtran.bst` silent formatting traps.
- `references/latex-ieee.md` — layout arithmetic (including what a full-width float really costs),
  float placement behaviour, measuring a compiled PDF, template compliance, atomic
  submission-package rebuild, and the fixed sequence of actions for editing a paper.
- `references/writing.md` — the writing/revising side: story checklist, mini-outline, section
  templates (abstract / introduction / related work as a lineage / method by motivation-design-
  advantage), paragraph roles, reverse outlining, the claim-evidence table, the five-dimension
  self-review rubric, figures-as-content rules, register and wording rules, and the citation-reality
  procedure. Read it before drafting or rewriting anything.
