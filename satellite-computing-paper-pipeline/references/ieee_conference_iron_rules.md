# IEEE Satellite & Aerospace Conference Paper: 12 Universal Iron Rules & Pre-Flight Checklist

This guide documents the empirical engineering standards, academic rigor requirements, and submission best practices established during the drafting and refinement of space-borne edge computing and radiation reliability papers for IEEE conferences (e.g., IEEE Satellite, IEEE TNS, IEEE Aero, etc.).

---

## Part 1: The 12 Universal Iron Rules

### Rule 1: Strict Monotonic Ascending Citations
* **Principle**: In the manuscript body, reference markers must appear strictly in numerical ascending order: `[1]`, `[2]`, `[3]`, ..., `[N]`.
* **Prohibited**:
  - Out-of-order first appearances (e.g., citing `[5]` before `[3]`).
  - Orphan references (listed in bibliography or checklist but never cited in body).
  - Inverted citation clusters (e.g., `[4], [2]` instead of `[2], [4]`).
* **Enforcement**: Run `python scripts/check_monotonic_citations.py` before every major revision and submission.

### Rule 2: Strict Page Ceiling & Balance Control
* **Principle**: If the conference sets a 6-page limit (including references), the paper must fit completely inside 6 pages. Exceeding by even 1 line onto page 7 will cause desk rejection.
* **Layout Geometry**:
  - The two columns on the final page must be visually balanced (`\usepackage{balance}` or `\IEEEtriggeratref{N}`).
  - Maintain standard margins (0.75 in top/bottom, 0.625 in left/right) and font sizes.
* **Vertical Space Budgeting**:
  - Cut bloated figure captions before shrinking text font.
  - Group related subplots into compound figures (e.g., Fig. 1(a), 1(b)).
  - Reduce redundant transitional paragraphs between adjacent subsections.

### Rule 3: Tri-Fold Orthogonal Telemetry Fingerprinting
* **Principle**: Space radiation failure characterization must decouple observations across at least three orthogonal physical/logical domains:
  1. **In-Band Software Layer**: OS heartbeat, syslog, kernel panic dmesg, workload process throughput.
  2. **Primary Bus Electrical Layer**: High-speed DC voltage, current draw, and power consumption profile.
  3. **Out-of-Band Physical / Supervisory Layer**: Accelerator beam flux/fluence dosimetry, board temperatures, and reset pin signal lines.
* **Rationale**: Single-channel diagnosis is susceptible to false positives (e.g., equating an OS freeze with chip destruction).

### Rule 4: Three-Tier Orthogonal Elimination Framework
* **Principle**: Root cause attribution must proceed through a disciplined elimination matrix rather than speculative declaration.
  - **Tier 1 (Software/OS Level)**: Rule out kernel freeze / thread deadlock by evaluating watchdog timeouts and power level incongruence.
  - **Tier 2 (Destructive Physical Level)**: Rule out permanent Single-Event Latchup (SEL) or dielectric rupture by proving current drops rather than surges, and verifying zero permanent post-annealing damage.
  - **Tier 3 (Power Management / Rail SEFI Level)**: Confirm selective rail dropout where auxiliary standby power remains alive while main core rails collapse.

### Rule 5: Quantified Cold-Power-Cycling Decay Constraint ($\Delta t_{\text{off}} \ge 10\text{ s}$)
* **Principle**: In-space recovery protocols cannot assume trivial instantaneous reset.
* **Physics Justification**: High-density compute modules incorporate large input/output decoupling capacitor banks ($C_{\text{bulk}} > 1000\ \mu\text{F}$). A brief glitch or $<2\text{ s}$ power drop leaves internal parasitic nodes charged, holding PMIC control flip-flops latched in the fault state.
* **Requirement**: Always explicitly state the quantified cold decay duration ($\Delta t_{\text{off}} \ge 10\text{ s}$) required to bleed rail voltages below $0.1\text{ V}$.

### Rule 6: Academic Hedging & Dormant Feature Blurring
* **Principle**: Never make absolute claims about subsystems that were not actively instrumented or verified in the beam.
* **Practice**:
  - If ECC was disabled or uncalibrated in the test firmware, do not claim "ECC failed to protect memory". Instead, state: *"The evaluation was conducted under default baseline memory configurations without auxiliary hardware parity intervention."*
  - Avoid definitive causal assertions without telemetry proof; use standard hedging: *"strongly points to"*, *"is physically consistent with"*, *"rules out the presence of"*.

### Rule 7: Zero-Hype Academic Tone & Precision
* **Forbidden Superlatives**: "Groundbreaking", "revolutionary", "flawless", "unprecedented", "first of its kind in history".
* **Preferred Terminology**:
  - Replace "we completely solved the problem" with *"the proposed architecture deterministically recovered 100% of tested radiation-induced lockup events"*.
  - Replace "huge power waste" with *"an abnormal quiescent standby plateau of 6.28 W"*.

### Rule 8: Concise & Self-Contained Figure Captions
* **Principle**: A figure caption should state *what* is shown and *the primary takeaway* in 20–40 words.
* **Anti-Pattern**: Writing a 120-word mini-discussion inside the `\caption{}`. Long discussions belong in the corresponding Section body text.
* **Format**:
  ```latex
  \caption{Empirical 3-stage failure timeline under 48~MeV proton radiation: (1) compute termination, (2) power drop to 6.28~W, and (3) persistent system lockup.}
  ```

### Rule 9: Dual-Format & Bilingual Data Synchronization
* **Principle**: Quantitative parameters across Chinese drafts, English LaTeX manuscripts, and literature tracking checklists must stay 100% synchronized:
  - Beam energy: `48 MeV`
  - Active load power: `66.8 W`
  - Fault plateau power: `6.28 W`
  - Power-down delay: `\ge 10 s`
  - Reference IDs and publication venues must match exactly.

### Rule 10: Scalable Vector Graphics & High-DPI Dual Deliverables
* **Rule**:
  - Primary figures in LaTeX must be vector PDFs (`.pdf`) or vector EPS (`.eps`) with embedded fonts to prevent pixelation on print zoom.
  - Accompanying preview assets must be rendered at 300+ DPI PNG (`.png`) for Markdown drafts, slides, and web inspection.
  - Script automation: Use PyMuPDF via `scripts/convert_figures.py`.

### Rule 11: Single Source of Truth for Citations
* **Principle**: Maintain an auditable `_文献回填清单.md` that tracks every cited work:
  - BibTeX citation key
  - In-text marker index (`[1]` to `[N]`)
  - DOI / verified URL
  - Direct relevance to the claim being cited
  - Full author list, venue, and year

### Rule 12: Automated Mirroring & Clean Submission Packaging
* **Rule**:
  - Workspaces must support dual hot mirroring to prevent data loss across drives or collaborative network directories.
  - Clean submission ZIP packages must contain ONLY source files (`.tex`, `.bib`, `.cls`, `.sty`, figure assets, README).
  - Exclude all compiler clutter: `.aux`, `.log`, `.out`, `.bbl`, `.blg`, `.synctex.gz`, `.fls`, `.fdb_latexmk`.

---

## Part 2: Pre-Flight Submission Checklist

Before clicking submit on IEEE Conference Management (e.g., EDAS, EasyChair, IEEE CPS):

- [ ] **1. Page Limit**: Document is strictly $\le 6$ pages (or conference max) including references.
- [ ] **2. PDF Font Embedding**: All fonts are Type 1 or TrueType, fully embedded (verified via `pdffonts paper.pdf`).
- [ ] **3. Monotonic Citations**: Checked via `python scripts/check_monotonic_citations.py` with 0 warnings.
- [ ] **4. Anonymity (if Double-Blind)**: Author names, affiliations, grant numbers, and lab identifiers removed from PDF.
- [ ] **5. High-Res Figures**: All figures legible in grayscale/black-and-white printing; text labels $\ge 7\text{ pt}$.
- [ ] **6. Table Quality**: Clean three-line booktabs (`\toprule`, `\midrule`, `\bottomrule`); no vertical lines.
- [ ] **7. Numerical Precision**: All reported values match raw laboratory logs and cross-manuscript references.
- [ ] **8. Clean ZIP Package**: Generated via `python scripts/sync_mirror_and_pack.py` without temporary compiler files.
