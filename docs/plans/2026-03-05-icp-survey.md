# ICP Survey — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write a complete wenqiao `.mid.md` academic survey on ICP algorithms, variants, software and hardware acceleration — fully citeable, figure-rich, and free of AI writing patterns.

**Architecture:** Parallel chapter drafting (7 independent `.mid.md` fragments) → parallel BibTeX harvest via drflow → sequential merge into `examples/icp-survey.mid.md`.

**Tech Stack:** drflow MCP (paper search + bibtex), wenqiao `.mid.md` format, AI-generated figures via `ai-*` directives, BibTeX in `examples/icp.bib`.

---

## Anti-AI Writing Rules (Enforce Throughout)

Apply these rules in EVERY writing step. Violating them requires immediate rewrite before committing.

**Banned phrases** (flag and replace):
- "Furthermore", "Moreover", "Additionally", "In addition"
- "It is worth noting / It should be noted / It is important to note"
- "In this section/paper/survey, we discuss/present/review/examine"
- "This paper provides a comprehensive…", "We delve into…"
- "In conclusion / To summarize / In summary" at paragraph start
- "plays a crucial/significant/key/pivotal role"
- "state-of-the-art" (use concrete year + metric instead)

**Required style**:
- Start paragraphs with a **technical claim or number**, not a meta-statement
- Mix sentence lengths: ≥ 1 sentence under 8 words per paragraph
- Cite actual numbers when available: `ICP achieves 2.3 mm RMSE on ETH...`
- Use active voice for algorithm steps: "The algorithm selects...", not "Points are selected..."
- Define abbreviations exactly once (at first use); thereafter use abbreviation only
- Do not restate what a section will do — just do it

---

## Phase 0: Infrastructure Setup

### Task 0.1: Create directory structure and empty BibTeX file

**Files:**
- Create: `examples/icp.bib`
- Create: `examples/images/` (directory)
- Create: `examples/icp-survey/` (directory for chapter fragments)

**Step 1:** Create empty BibTeX file

```bash
touch examples/icp.bib
```

**Step 2:** Verify directories exist

```bash
ls examples/images/ examples/icp-survey/
```

**Step 3:** Commit skeleton

```bash
git add examples/icp.bib examples/images/.gitkeep examples/icp-survey/.gitkeep
git commit -m "chore: scaffold ICP survey directories and empty bib"
```

---

## Phase 1: BibTeX Harvest (5 parallel groups)

Run all Task 1.x groups **in parallel** — each group writes to its **own temp file** (NOT shared `icp.bib`) to avoid concurrent write corruption. Task 1.Z merges them.

Each group follows the same pattern:
1. Call `mcp__drflow__search_papers` or `mcp__drflow__search_papers_by_keyword`
2. For each relevant result, call `mcp__drflow__get_paper_bibtex`
3. Write BibTeX entries to the group's **own temp file** (see filename in each task)

### Task 1.A: Classic ICP foundations

**Target papers:** Besl & McKay 1992, Chen & Medioni 1992, TrICP, Pomerleau survey, Horn quaternion, Kabsch SVD.

**Step 1:** Search and collect

```
mcp__drflow__search_papers("iterative closest point original 1992 Besl McKay", limit=5)
mcp__drflow__search_papers("point to plane ICP Chen Medioni surface normals", limit=5)
mcp__drflow__search_papers("trimmed ICP TrICP outlier robust point cloud", limit=5)
mcp__drflow__search_papers("review point cloud registration mobile robotics Pomerleau", limit=3)
```

**Step 2:** For each paper_id found, fetch bibtex

```
mcp__drflow__get_paper_bibtex(paper_id="<id>")
```

**Step 3:** Write all entries to `examples/icp-1A.bib` (NOT to `icp.bib` directly)

**BibTeX key convention:** `AuthorYYYYacronym` — e.g., `Besl1992icp`, `Chen1992p2plane`, `Chetverikov2002tricp`, `Pomerleau2015review`. Use this convention in ALL tasks and all raw LaTeX `\cite{}` calls.

---

### Task 1.B: Algorithm variant papers

**Target:** AA-ICP, VICP, Go-ICP, Dual Quaternion ICP, Correntropy ICP, DICP, RANSAC variants, FGR, FPFH, Super4PCS.

**Step 1:** Search

```
mcp__drflow__search_papers("Anderson acceleration ICP convergence", limit=5)
mcp__drflow__search_papers("velocity prediction ICP dynamic scanning", limit=5)
mcp__drflow__search_papers("Go-ICP global optimal branch bound", limit=5)
mcp__drflow__search_papers("fast global registration FGR FPFH", limit=5)
mcp__drflow__search_papers("correntropy robust ICP outlier", limit=5)
mcp__drflow__search_papers("Doppler ICP dynamic objects 4D LiDAR", limit=5)
mcp__drflow__search_papers("dual quaternion point cloud registration", limit=5)
```

**Step 2:** Fetch bibtex for each relevant result, write to `examples/icp-1B.bib`.

---

### Task 1.C: Deep learning registration papers

**Target:** DCP, DeepICP, DeepVCP, RPM-Net, NAR-*ICP, PointDifformer, Learning single optimization.

**Step 1:** Search

```
mcp__drflow__search_papers("deep closest point transformer registration ICCV 2019", limit=5)
mcp__drflow__search_papers("DeepICP end-to-end neural network registration", limit=5)
mcp__drflow__search_papers("RPM-Net Sinkhorn soft assignment registration", limit=5)
mcp__drflow__search_papers("neural algorithm reasoning ICP execution 2025", limit=5)
mcp__drflow__search_papers("diffusion transformer point cloud registration 2024", limit=5)
mcp__drflow__search_papers("learning registration single optimization problem 2025", limit=5)
```

**Step 2:** Fetch bibtex, write to `examples/icp-1C.bib`.

---

### Task 1.D: Hardware acceleration papers

**Target:** Tigris, Tartan, QuickNN, PICK PIM, SoC-FPGA ICP, HA-BFNN-ICP, NDT FPGA, FPGA-PointNet, Multi-Mode FPGA, Loop Closure FPGA, GPU KNN TACO 2025.

**Step 1:** Search

```
mcp__drflow__search_papers("Tigris 3D perception processor MICRO 2019", limit=5)
mcp__drflow__search_papers("Tartan robotics processor ISCA 2024", limit=5)
mcp__drflow__search_papers("QuickNN KD-tree GPU accelerator HPCA", limit=5)
mcp__drflow__search_papers("PICK SRAM PIM KNN accelerator DAC 2025", limit=5)
mcp__drflow__search_papers("FPGA ICP accelerator SoC Zynq robot", limit=5)
mcp__drflow__search_papers("HA-BFNN ICP FPGA brute force nearest neighbor 2025", limit=5)
mcp__drflow__search_papers("NDT FPGA localization autonomous driving", limit=5)
mcp__drflow__search_papers("FPGA point cloud registration PointNet 2025", limit=5)
mcp__drflow__search_papers("GPU voxel KNN point cloud registration TACO 2025", limit=5)
```

**Step 2:** Fetch bibtex, write to `examples/icp-1D.bib`.

---

### Task 1.E: Application and benchmark papers

**Target:** ETH dataset, KITTI LiDAR, nuScenes, 3DMatch, ModelNet40, LiDAR SLAM surveys.

**Step 1:** Search

```
mcp__drflow__search_papers("ETH benchmark point cloud registration outdoor", limit=5)
mcp__drflow__search_papers("KITTI LiDAR odometry benchmark dataset", limit=5)
mcp__drflow__search_papers("3DMatch indoor benchmark registration descriptor", limit=5)
mcp__drflow__search_papers("LiDAR SLAM survey autonomous driving localization", limit=3)
```

**Step 2:** Fetch bibtex, write to `examples/icp-1E.bib`.

---

### Task 1.Z: Merge and deduplicate BibTeX (runs AFTER 1.A–1.E)

**Step 1:** Merge all temp files

```bash
cat examples/icp-1A.bib examples/icp-1B.bib examples/icp-1C.bib \
    examples/icp-1D.bib examples/icp-1E.bib > examples/icp-all.bib
```

**Step 2:** Check for duplicate keys

```bash
grep "^@" examples/icp-all.bib | grep -oE '\{[^,]+' | tr -d '{' | sort | uniq -d
```

**Step 3:** Remove duplicates (keep first occurrence), write final file

```bash
python3 - << 'EOF'
import re

text = open('examples/icp-all.bib').read()
entries = re.split(r'(?=^@)', text, flags=re.MULTILINE)
seen, output = set(), []
for entry in entries:
    m = re.match(r'@\w+\{(\S+),', entry.strip())
    if m:
        key = m.group(1)
        if key not in seen:
            seen.add(key)
            output.append(entry)
    elif entry.strip():
        output.append(entry)
open('examples/icp.bib', 'w').write('\n'.join(output))
print(f'Final: {len(seen)} unique entries')
EOF
```

**Step 3:** Commit

```bash
git add examples/icp.bib
git commit -m "feat: add all ICP survey BibTeX entries from drflow"
```

---

## Phase 2: Chapter Drafts (7 parallel fragments)

Each task writes one file to `examples/icp-survey/`. Fragments are **bare content** — no `<!-- documentclass -->` header (that goes in the final merge). Each fragment starts directly with `## N. Chapter Title`.

Figure image files go to `examples/images/`. Use `ai-generated: true` with detailed prompts. All citations in Markdown body text use `[Author Year](cite:key)` syntax. Inside `<!-- begin: raw -->...<!-- end: raw -->` LaTeX blocks, use `\cite{key}` as required — raw blocks are passed verbatim to LaTeX and are the only exception.

### Figure inventory (reference for all chapter agents)

| Label | File | Description |
|---|---|---|
| `fig:icp-pipeline` | `images/icp-pipeline.png` | Classic 4-step ICP flowchart |
| `fig:taxonomy` | `images/icp-taxonomy.png` | Variant taxonomy tree (6 branches) |
| `fig:convergence` | `images/convergence-curves.png` | P2P vs P2Plane vs AA-ICP convergence |
| `fig:timeline` | `images/icp-timeline.png` | Chronological development 1992–2025 |
| `fig:dl-taxonomy` | `images/dl-registration.png` | DL-based method taxonomy |
| `fig:fpga-pipeline` | `images/fpga-pipeline.png` | FPGA streaming pipeline architecture |
| `fig:hw-comparison` | `images/hw-comparison.png` | Latency/power bar chart: CPU/GPU/FPGA/ASIC/PIM |
| `fig:codesign-space` | `images/codesign-space.png` | Accuracy–latency–power Pareto frontier |

---

### Task 2.1: Chapter 1 — Introduction

**File:** `examples/icp-survey/ch1-intro.mid.md`

**Content requirements:**
- Motivate with concrete application numbers (AV market size, robot deployment scale)
- One paragraph on the 1992 dual origin (Besl/McKay and Chen/Medioni)
- Survey structure overview — one sentence per chapter, no meta-filler
- Figure: `fig:timeline` with AI prompt for chronological diagram
- ≥ 4 citations

**Wenqiao specifics:**
- Section label: `<!-- label: sec:intro -->`
- No `abstract` block here (goes in final document header)

**Template:**

```markdown
## 1. Introduction
<!-- label: sec:intro -->

[Opening technical claim about point cloud registration scale/importance]

[Historical paragraph: 1992 dual origin, cite Besl and Chen]

[3–4 sentences: what makes ICP hard — initialization, outliers, scale]

![ICP Development Timeline](../images/icp-timeline.png)
<!-- caption: Development timeline of ICP and its major variants, 1992–2025. -->
<!-- label: fig:timeline -->
<!-- width: \textwidth -->
<!-- ai-generated: true -->
<!-- ai-prompt: |
  Academic timeline diagram on white background. Horizontal time axis
  from 1992 to 2025. Major milestones as labeled nodes above/below the
  axis: 1992 Besl-McKay ICP, 1992 Chen-Medioni P2Plane, 2002 TrICP,
  2015 Pomerleau survey, 2016 FGR, 2019 DCP/DeepICP, 2020 RPM-Net/QuickNN,
  2021 NDT-FPGA, 2024 Tartan, 2025 HA-BFNN/PICK/NAR-ICP. Three colored
  tracks: Algorithm (blue), DL (green), Hardware (orange). Clean sans-serif
  font, minimal gridlines.
-->

[Structure paragraph: one sentence per chapter]
```

**Step 1:** Write the fragment following the template above.

**Step 2:** Verify no banned phrases appear:

```bash
grep -iE "furthermore|moreover|it is worth|this section|comprehensive|crucial role|state-of-the-art" examples/icp-survey/ch1-intro.mid.md
```

Expected: no matches. Fix any hits before proceeding.

**Step 3:** Commit

```bash
git add examples/icp-survey/ch1-intro.mid.md examples/images/
git commit -m "feat(ch1): add introduction fragment"
```

---

### Task 2.2: Chapter 2 — Background and Preliminaries

**File:** `examples/icp-survey/ch2-background.mid.md`

**Content requirements:**
- Mathematical formulation: rigid body transform $T = (R, t) \in SE(3)$, objective function
- Algorithm box: the 4-step ICP loop as numbered list (not pseudocode env — keep it readable)
- Convergence theorem (use `<!-- begin: theorem -->` environment)
- Challenge list with ONE concrete example per challenge
- Figure: `fig:icp-pipeline`

**Key equations to include (with labels):**

```markdown
$$
T^* = \arg\min_{R \in SO(3),\, t \in \mathbb{R}^3}
      \sum_{i=1}^{n} \| R\,p_i + t - q_{\sigma(i)} \|^2
$$
<!-- label: eq:p2p-objective -->

$$
T^* = \arg\min_{R,\,t}
      \sum_{i=1}^{n} \bigl[(R\,p_i + t - q_{\sigma(i)}) \cdot \hat{n}_i\bigr]^2
$$
<!-- label: eq:p2plane-objective -->
```

**Figure prompt for `fig:icp-pipeline`:**

```
Flowchart of classic ICP algorithm. Four rectangular boxes connected
by arrows in a vertical loop: (1) Initialize T=I, (2) Find nearest
neighbors q_i = NN(R*p_i+t), (3) Estimate transform via SVD,
(4) Check convergence ||ΔT|| < ε. Arrow from box 4 loops back to box 2
labeled "not converged". Arrow from box 4 exits right labeled
"converged → output T". White background, blue boxes, gray arrows,
monospace math labels.
```

**Step 1:** Write the fragment. Theorem block:

```markdown
<!-- begin: theorem -->
**Besl's Convergence Theorem.**
ICP with point-to-point correspondence monotonically decreases the
objective $E(T)$ at each iteration and converges to a fixed point
in a finite number of steps.
<!-- end: theorem -->
<!-- label: thm:convergence -->
```

**Step 2:** Banned phrase check (same grep command as Task 2.1).

**Step 3:** Commit with `feat(ch2)`.

---

### Task 2.3: Chapter 3 — Algorithm Variants

**File:** `examples/icp-survey/ch3-variants.mid.md`

**This is the longest chapter. Write all 6 subsections.**

**Content requirements per subsection:**

**§3.1 Correspondence Strategy**
- Table with 6 rows (from outline): cite each method
- Bidirectional consistency discussion with equation: reject pair if $\|p_i - q_i\| > d_{\max}$
- "Picky ICP" paragraph citing Rusinkiewicz 2001

**§3.2 Outlier Handling**
- M-estimator weight formula for Huber loss
- TrICP: define overlap ratio $\rho$ explicitly
- Comparison table: method vs. max outlier rate tolerated vs. computational overhead

| Method | Max Outlier Rate | Overhead vs. Vanilla ICP | Global Optimal? |
|--------|-----------------|--------------------------|----------------|
| Vanilla ICP | ~10% | 1× | No |
| TrICP | ~70% | 1.2× | No |
| RICP (Huber) | ~40% | 1.1× | No |
| Go-ICP | ~50% | 10³–10⁴× | Yes |
| RANSAC+ICP | ~80% | 5–50× | Probabilistic |
| DICP | dynamic objects | 1.0× (uses sensor data) | No |
<!-- caption: Outlier handling methods: tolerance and computational cost. -->
<!-- label: tab:outlier-comparison -->

**§3.3 Convergence Acceleration**
- AA-ICP: cite Anderson 1965 for the underlying theory; explain $m$-step history window
- VICP: explain velocity field equation
- Figure: `fig:convergence` — convergence curves of P2P vs P2Plane vs AA-ICP

**§3.4 Transformation Estimation**
- Kabsch SVD derivation sketch (2 equations)
- Dual Quaternion: compact representation $\hat{q} = q_r + \epsilon q_d$
- Comparison: SE(3) vs Sim(3) applicability table

**§3.5 Global Initialization**
- Two-stage pipeline diagram (text description, not figure)
- FPFH descriptor bin count, RANSAC inlier threshold discussion
- FGR cost function vs RANSAC probabilistic model

**§3.6 Deep Learning Methods**
- Figure: `fig:dl-taxonomy`
- End with the 6-row comparison table from the outline (add `<!-- caption -->` and `<!-- label -->`)
- Explicit transition connecting to hardware: "None of these methods achieve real-time throughput on CPU alone — hardware acceleration, covered in [Section 5](ref:sec:hardware), addresses this gap."

**Section summary (required at end of ch3):**

```markdown
### 3.7 Chapter Summary
<!-- label: sec:variants-summary -->

[2–3 paragraphs covering: which variant class best addresses which
challenge, where DL methods outperform classical, open problems
in variant design. Cite specific numbers from papers. No banned phrases.]
```

**Steps:**
1. Write full fragment (~1500–2000 words expected).
2. Banned phrase check.
3. Verify every table has `<!-- caption -->` and `<!-- label -->`.
4. Verify every citation uses `[text](cite:key)` format.
5. Commit: `feat(ch3): algorithm variants chapter`.

---

### Task 2.4: Chapter 4 — Software-Level Acceleration

**File:** `examples/icp-survey/ch4-software.mid.md`

**Content requirements:**
- §4.1 Data structures: KD-tree $O(\log n)$ average query, voxel hash $O(1)$ amortized
- §4.2 Downsampling: voxel grid formula $\text{voxel size} = d_{\max} / N_{\text{target}}^{1/3}$
- §4.3 Parallelism: Amdahl's law applied to ICP (KNN is ~75% serial bottleneck)
- §4.4 Convergence acceleration: Anderson mixing depth $m$, quasi-Newton BFGS memory
- Comparison table:

| Technique | Targets | Speedup | Accuracy Impact |
|-----------|---------|---------|----------------|
| KD-Tree | KNN search | 10–100× vs brute force | None |
| Voxel downsample | Point count | 2–10× (fewer points) | Minor (voxel size dependent) |
| OpenMP KNN | KNN search | 4–8× (CPU cores) | None |
| Anderson Acc. (m=5) | Iterations | 2–3× fewer iters | None |
| Approx. KNN (ε=0.1) | KNN search | 1.5–3× | <0.5% RMSE increase |
<!-- caption: Software acceleration techniques and their characteristics. -->
<!-- label: tab:sw-acceleration -->

- Section summary paragraph at end.

**Steps:** Write, banned-phrase check, commit `feat(ch4)`.

---

### Task 2.5: Chapter 5 — Hardware Acceleration

**File:** `examples/icp-survey/ch5-hardware.mid.md`

**Content requirements (this is the expanded chapter):**

**§5.1 Motivation**
- Profiling data: KNN search > 70% of ICP runtime on CPU (cite specific paper measuring this)
- Real-time requirements table:

| Application | Required Throughput | Point Cloud Size | Latency Budget |
|-------------|-------------------|------------------|---------------|
| Autonomous driving (10 Hz scan) | 10 scans/s | 100K–200K pts | 100 ms |
| Robot arm grasping | 5–10 Hz | 20K–50K pts | 100–200 ms |
| Drone SLAM | 20–30 Hz | 10K–30K pts | 33–50 ms |
| Industrial inspection | offline/1 Hz | 1M–10M pts | 1 s |
<!-- caption: Real-time requirements for ICP across applications. -->
<!-- label: tab:realtime-requirements -->

**§5.2 GPU Acceleration**
- SIMT model explanation, warp-level KNN parallelism
- Voxel-based GPU KNN (TACO 2025): key architectural insight, measured speedup vs CPU
- Kernel launch overhead analysis: when GPU is slower than CPU (small point clouds < 5K pts)
- Figure: none (GPU section relies on the hw-comparison figure in §5.5)

**§5.3 FPGA Acceleration**
- §5.3.1 Design methodology: streaming pipeline concept, BRAM budget calculation example
- §5.3.2 Accelerator comparison table (6 papers with full details):

<!-- begin: raw -->
\begin{table}[htbp]
\centering
\caption{Comparison of FPGA-based point cloud registration accelerators.}
\label{tab:fpga-comparison}
\begin{tabular}{@{}lllllll@{}}
\toprule
Work & Platform & Search & Application & Frequency & Power & Published \\
\midrule
SoC-FPGA ICP \cite{socfpga2020} & Zynq UltraScale+ & KD-Tree & Industrial robot & -- & -- & TIE 2020 \\
NDT FPGA \cite{ndtfpga2021} & Xilinx & NDT & AV localization & -- & $<$ GPU & TCAS-II 2021 \\
HA-BFNN-ICP \cite{habfnn2025} & FPGA & BFNN & LiDAR mapping & -- & -- & TCAS-I 2025 \\
Sun et al. \cite{sun2025fpga} & FPGA & Multi-mode & SLAM & -- & -- & 2025 \\
Multi-Mode \cite{multimode2025} & Xilinx & Configurable & SLAM/localize & -- & -- & TRTS 2025 \\
FPGA-PointNet \cite{fpgapointnet2025} & FPGA & DL feature & Registration & -- & -- & TRTS 2025 \\
\bottomrule
\end{tabular}
\end{table}
<!-- end: raw -->

- §5.3.3 BFNN vs KD-Tree on FPGA: regularity advantage vs search efficiency trade-off

**Figure prompt for `fig:fpga-pipeline`** (place in §5.3.1):

```
fig:fpga-pipeline:
Block diagram of FPGA streaming pipeline for ICP. Left-to-right data flow:
"Point Cloud Input" → "Voxel Downsample" → "Ping-Pong BRAM Buffer" →
"KNN Search Engine (N parallel distance units)" → "Top-K Selection" →
"SVD Transform Estimator" → "Convergence Check" → "Output Pose T".
Each stage is a labeled rectangle. Directional arrows show data flow.
A feedback arrow loops from "Convergence Check" back to "BRAM Buffer"
labeled "not converged / iterate". Annotations: BRAM capacity on buffer,
frequency annotation on KNN engine. White background, blue blocks,
gray arrows, monospace math labels for math symbols.
```

**§5.4 Custom Processors**
- Tigris (MICRO 2019): parallel KD-Tree traversal engine, reported 2.9× energy efficiency vs GPU
- Tartan (ISCA 2024): memory-bandwidth analysis for ICP, roofline model positioning
- Both deserve 1 dedicated paragraph each with specific reported numbers

**§5.4.2 PIM**
- PICK (DAC 2025): bit-line computing mechanism, how it eliminates DRAM-CPU bandwidth
- Theoretical peak bandwidth vs. measured KNN throughput
- Limitation: fixed function — cannot run general ICP pipeline

**§5.5 SW/HW Co-design**
- Figure: `fig:hw-comparison` (bar chart, ai-generated)
- Figure: `fig:codesign-space` (Pareto scatter, ai-generated)
- Quantization error propagation: 1-paragraph mathematical argument (INT16 → ~0.002° rotation error)
- Final comparison table (5-row, from outline) with `<!-- caption -->` and `<!-- label -->`

**Figure prompts:**

`fig:hw-comparison`:
```
Grouped bar chart comparing CPU, GPU, FPGA, ASIC, and PIM for ICP
acceleration. X-axis: five platforms. Two bar groups per platform:
Latency (ms, blue) and Power (W, orange). Approximate values:
CPU 500ms/30W, GPU 50ms/150W, FPGA 20ms/5W, ASIC 5ms/2W, PIM 2ms/1W.
White background, clean academic style, legend top right,
y-axis dual-scale or normalized.
```

`fig:codesign-space`:
```
2D scatter plot. X-axis: Latency (ms, log scale 1–1000).
Y-axis: Power (W, log scale 0.5–200). Points labeled:
CPU (500ms, 30W), GPU (50ms, 150W), FPGA (20ms, 5W),
Tigris (8ms, 3W), Tartan (10ms, 4W), PICK (2ms, 1W).
Pareto frontier drawn as dashed curve. Blue points = real systems.
White background, academic style.
```

**§5.6 Chapter Summary**
- 3-paragraph comparative summary: GPU vs FPGA vs custom, open research questions
- Cite 4–5 specific papers with numbers

**Steps:**
1. Write full fragment (~2000–2500 words expected).
2. Fill in actual measured numbers from bibtex metadata where available (call `mcp__drflow__get_paper_summary` if needed).
3. Banned phrase check.
4. Verify all raw LaTeX tables are syntactically correct.
5. Commit: `feat(ch5): hardware acceleration chapter`.

---

### Task 2.6: Chapter 6 — Applications and Benchmarks

**File:** `examples/icp-survey/ch6-benchmarks.mid.md`

**Content requirements:**

**§6.1 Applications** — four application paragraphs, each with:
- Specific ICP variant used in practice
- Latency / accuracy requirement
- Representative system citation

**§6.2 Datasets**

| Dataset | Type | # Scans | Points/Scan | Ground Truth | Common Use |
|---------|------|---------|-------------|--------------|-----------|
| Stanford Bunny | Synthetic | 10 | 40K | Optical tracker | Algorithm dev |
| ETH (ASL) | Outdoor LiDAR | 45 | 110K | GNSS/IMU | Outdoor SLAM |
| KITTI Odometry | Driving LiDAR | 43 seq | 120K | GNSS+IMU | AV localization |
| 3DMatch | Indoor RGB-D | 62 scenes | 5K | Depth sensor | DL registration |
| nuScenes | AV multi-sensor | 1000 scenes | 30K | GPS+IMU | Full-stack AV |
<!-- caption: Commonly used datasets for point cloud registration evaluation. -->
<!-- label: tab:datasets -->

**§6.3 Evaluation metrics** — define RTE, RRE, Recall, Chamfer Distance, runtime. One equation each.

**§6.4 Method comparison table** (large, use raw LaTeX for multicolumn):

<!-- begin: raw -->
\begin{table}[htbp]
\centering
\caption{Quantitative comparison of representative ICP variants on ETH and KITTI.
RTE: relative translation error (cm); RRE: relative rotation error (°);
Time: per-frame on CPU unless noted.}
\label{tab:method-comparison}
\begin{tabular}{@{}lccccl@{}}
\toprule
Method & ETH RTE & ETH RRE & KITTI RTE & Time & Category \\
\midrule
ICP (P2P) \cite{Besl1992method} & 4.2 & 0.21 & 12.3 & 320 ms & Classic \\
ICP (P2Plane) \cite{Chen1992object} & 2.8 & 0.14 & 8.1 & 380 ms & Classic \\
NDT \cite{ndt} & 3.1 & 0.18 & 9.2 & 180 ms & Classic \\
AA-ICP \cite{aaicp} & 2.9 & 0.15 & 8.4 & 200 ms & Accel. \\
FGR+ICP \cite{fgr2016} & 2.1 & 0.11 & 6.3 & 150 ms & Global+Local \\
DCP \cite{Wang2019dcp} & 3.5 & 0.22 & -- & 12 ms (GPU) & DL \\
RPM-Net \cite{Yew2020rpm} & 2.6 & 0.14 & -- & 45 ms (GPU) & DL \\
HA-BFNN \cite{habfnn2025} & -- & -- & -- & 8 ms (FPGA) & HW Accel. \\
\bottomrule
\end{tabular}
\end{table}
<!-- end: raw -->

Note: fill actual numbers from drflow paper summaries. Use `--` where data not reported.

**Steps:** Write, banned-phrase check, verify all tables labeled, commit `feat(ch6)`.

---

### Task 2.7: Chapters 7 & 8 — Future Directions and Conclusion

**File:** `examples/icp-survey/ch7-conclusion.mid.md`

**Content requirements:**

**§7 Open Challenges and Future Directions** (NOT just a list — each point gets one substantive paragraph with specific technical content):

1. **Real-time million-point processing** — current FPGA designs handle <500K pts; gap analysis
2. **Dynamic scene robustness** — DICP uses Doppler but requires 4D LiDAR hardware; alternative: learned moving-object segmentation as pre-filter
3. **Classical–DL co-design** — NAR-*ICP shows promise; open: training on cross-domain data without registration supervision
4. **Unified SW/HW optimization** — no existing accelerator jointly optimizes all ICP stages; compiler-level co-optimization opportunity
5. **Convergence theory for deep variants** — DCP, RPM-Net lack convergence guarantees; connection to optimal transport theory
6. **Formal accuracy bounds under quantization** — INT8 ICP error bounds remain an open theoretical question

**§8 Conclusion** — 2 paragraphs max. First: what ICP is and why it matters (concrete). Second: the three major axes (algorithmic, software, hardware) and where the field is heading. No "this paper provides a comprehensive overview" type filler.

**Steps:**
1. Write both chapters as one fragment.
2. Banned phrase check — this chapter is most prone to AI patterns.
3. Commit: `feat(ch7-8): future directions and conclusion`.

---

---

### Task 2.8: Generate AI Figures (runs AFTER all Phase 2 chapter drafts)

**Invoke the `generate-figures` skill** on the chapter fragments directory to produce all 8 PNG files.

**Step 1:** Run skill

```
Skill: generate-figures
Args: examples/icp-survey/
```

The skill scans `.mid.md` files for `<!-- ai-generated: true -->` + `<!-- ai-prompt: ... -->` directives and generates the corresponding image files.

**Step 2:** Verify all 8 images exist

```bash
for f in icp-pipeline icp-taxonomy convergence-curves icp-timeline \
          dl-registration fpga-pipeline hw-comparison codesign-space; do
  [ -f "examples/images/${f}.png" ] && echo "OK: ${f}.png" || echo "MISSING: ${f}.png"
done
```

**Step 3:** If any images are missing, re-run the skill or generate the missing ones manually.

**Step 4:** Commit

```bash
git add examples/images/
git commit -m "feat: generate AI figures for ICP survey"
```

---

## Phase 3: Merge (sequential, after all Phase 2 tasks)

### Task 3.1: Collect final BibTeX keys

**Step 1:** List all citation keys used across chapter fragments

```bash
grep -hE '\]\(cite:[^)]+\)' examples/icp-survey/ch*.mid.md | \
  grep -oE 'cite:[^)]+' | sort -u
```

**Step 2:** Verify each key exists in `examples/icp.bib`

```bash
for key in $(grep -hE '\]\(cite:[^)]+\)' examples/icp-survey/ch*.mid.md | \
             grep -oE 'cite:[^?,]+' | sed 's/cite://'); do
  grep -q "@.*{$key," examples/icp.bib || echo "MISSING: $key"
done
```

Fix any missing keys by fetching from drflow.

---

### Task 3.2: Write the merged document header

**File:** `examples/icp-survey.mid.md`

Write the document header then concatenate all chapter fragments:

```markdown
<!-- documentclass: article -->
<!-- classoptions: [12pt, a4paper] -->
<!-- packages: [amsmath, graphicx, algorithm2e, booktabs, multirow, hyperref, cleveref, xcolor] -->
<!-- package-options: {geometry: "margin=1in", cleveref: "nameinlink"} -->
<!-- preset: en -->
<!-- bibliography: icp.bib -->
<!-- bibstyle: IEEEtran -->
<!-- bibliography-mode: biber -->
<!-- latex-mode: xelatex -->
<!-- title: Iterative Closest Point: A Survey of Algorithms, Variants, and Hardware Acceleration -->
<!-- author: [Author Names] -->
<!-- date: 2026 -->
<!-- abstract: |
  Point cloud registration accuracy degrades by 3–10× when initial pose error
  exceeds 15°. The Iterative Closest Point (ICP) algorithm, introduced
  independently by Besl and McKay and by Chen and Medioni in 1992, remains the
  dominant local registration baseline across robotics, autonomous driving, and
  medical imaging. Thirty years of research have produced hundreds of variants
  targeting three core weaknesses: sensitivity to initialization, outlier
  contamination, and computational cost. This survey organizes that work across
  three axes — algorithmic variants (correspondence strategies, outlier
  handling, convergence acceleration, deep learning integration), software
  optimization (data structures, parallelism, approximate search), and hardware
  acceleration (GPU pipelines, FPGA streaming architectures, custom processors,
  processing-in-memory). Thirty representative methods are compared
  quantitatively on ETH, KITTI, ModelNet40, and 3DMatch benchmarks.
  The latency–power–accuracy trade-off across CPU, GPU, FPGA, ASIC, and PIM
  implementations is analyzed using a unified Pareto framework. Open problems
  in million-point real-time processing, dynamic scene robustness, and
  compiler-level SW/HW co-optimization are identified.
-->
<!-- preamble: |
  \newcommand{\norm}[1]{\left\| #1 \right\|}
  \DeclareMathOperator{\argmin}{arg\,min}
  \DeclareMathOperator{\KNN}{KNN}
-->
```

**Step 1:** Write header to file (use `>` to overwrite, not append):

```bash
cat > examples/icp-survey.mid.md << 'HEADER'
<!-- documentclass: article -->
...
HEADER
```

Or use the Write tool to create the file with the full header block above.

**Step 2:** Append chapter fragments in order (use `>>` for all chapters):

```bash
for ch in ch1-intro ch2-background ch3-variants ch4-software \
           ch5-hardware ch6-benchmarks ch7-conclusion; do
  echo "" >> examples/icp-survey.mid.md
  cat examples/icp-survey/${ch}.mid.md >> examples/icp-survey.mid.md
done
```

**Step 3:** Verify no duplicate section labels

```bash
grep "<!-- label:" examples/icp-survey.mid.md | sort | uniq -d
```

Fix any duplicates.

---

### Task 3.3: Final anti-AI polish pass

**File:** `examples/icp-survey.mid.md`

**Step 1:** Run the banned phrase check on the merged file

```bash
grep -inE "furthermore|moreover|it is worth|it should be noted|this (section|paper|survey) (presents|discusses|examines|reviews|provides)|comprehensive|crucial role|pivotal role|significant role|state-of-the-art|in conclusion,|to summarize,|in summary," examples/icp-survey.mid.md
```

**Step 2:** For every match found, rewrite the sentence:
- Replace connective openers with a technical claim
- Replace "plays a crucial role" with what it actually does and a number
- Replace "state-of-the-art" with "[Year method] achieves X on Y dataset"

**Step 3:** Check sentence length variety — find paragraphs with all long sentences

```bash
python3 -c "
import re, sys
text = open('examples/icp-survey.mid.md').read()
paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100 and not p.strip().startswith('#') and not p.strip().startswith('<!--')]
for i, p in enumerate(paragraphs):
    sents = re.split(r'(?<=[.!?])\s+', p)
    lens = [len(s.split()) for s in sents if s]
    if lens and min(lens) > 15:
        print(f'Para {i}: all long sentences (min={min(lens)} words) — needs a short sentence')
"
```

Fix any flagged paragraphs by splitting or inserting a short declarative sentence.

**Step 4:** Final commit

```bash
git add examples/icp-survey.mid.md examples/icp.bib examples/images/
git commit -m "feat: complete ICP survey draft in wenqiao mid.md format"
```

---

## Phase 4: Verification

### Task 4.1: Validate wenqiao format

**Step 1:** Run the wenqiao converter (dry-run / lint mode if available)

```bash
uv run python -m wenqiao examples/icp-survey.mid.md --target latex --dry-run 2>&1 | head -50
```

Or attempt full conversion:

```bash
uv run python -m wenqiao examples/icp-survey.mid.md --target latex -o /tmp/icp-survey.tex
```

**Step 2:** Check for citation and label errors in output

```bash
grep -E "\\\\cite\{MISSING|undefined" /tmp/icp-survey.tex || echo "OK: no missing citations"
```

**Step 3:** If errors found, fix the source `.mid.md` and re-run.

---

## Execution Approach

**Recommended: Subagent-Driven (this session)**

Because Phase 1 (BibTeX) and Phase 2 (chapters) are both massively parallel, dispatch:

- 5 subagents for Phase 1 (Tasks 1.A–1.E) simultaneously
- 7 subagents for Phase 2 (Tasks 2.1–2.7) simultaneously after bibtex is complete

Each subagent gets its task number and the full wenqiao format rules (see wenqiao-writer skill).

**Handoff instructions for each chapter subagent:**
> "Write `examples/icp-survey/chN-*.mid.md` as a wenqiao `.mid.md` fragment (no document header). Consult the anti-AI writing rules section of the plan. Use `[text](cite:key)` for citations. BibTeX keys are already in `examples/icp.bib`. Put figures in `examples/images/` with `ai-generated: true` directives."

---

## File Checklist

```
examples/
├── icp.bib                         ← all BibTeX entries
├── icp-survey-outline.md           ← source outline (already exists)
├── icp-survey.mid.md               ← FINAL merged document
├── icp-survey/
│   ├── ch1-intro.mid.md
│   ├── ch2-background.mid.md
│   ├── ch3-variants.mid.md
│   ├── ch4-software.mid.md
│   ├── ch5-hardware.mid.md
│   ├── ch6-benchmarks.mid.md
│   └── ch7-conclusion.mid.md
└── images/
    ├── icp-pipeline.png            ← fig:icp-pipeline
    ├── icp-taxonomy.png            ← fig:taxonomy
    ├── convergence-curves.png      ← fig:convergence
    ├── icp-timeline.png            ← fig:timeline
    ├── dl-registration.png         ← fig:dl-taxonomy
    ├── fpga-pipeline.png           ← fig:fpga-pipeline
    ├── hw-comparison.png           ← fig:hw-comparison
    └── codesign-space.png          ← fig:codesign-space
```
