# ICP 算法综述 — 写作计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 以 wenqiao `.mid.md` 格式写一篇关于 ICP 算法发展与变体、软件加速、硬件加速的完整学术综述。

**技术栈：** drflow MCP（论文检索 + bibtex）、wenqiao `.mid.md` 格式、AI 生成插图（`ai-*` 指令）、BibTeX 存入 `examples/icp.bib`。

**文件结构：**

```
examples/
├── icp.bib                         ← 所有 BibTeX 条目
├── icp-survey-outline.md           ← 原始大纲（已存在）
├── icp-survey.mid.md               ← 最终合并文档
├── icp-survey/
│   ├── ch1-intro.mid.md
│   ├── ch2-background.mid.md
│   ├── ch3-variants.mid.md
│   ├── ch4-software.mid.md
│   ├── ch5-hardware.mid.md
│   ├── ch6-benchmarks.mid.md
│   └── ch7-conclusion.mid.md
└── images/
    ├── icp-pipeline.png
    ├── icp-taxonomy.png
    ├── convergence-curves.png
    ├── icp-timeline.png
    ├── dl-registration.png
    ├── fpga-pipeline.png
    ├── hw-comparison.png
    └── codesign-space.png
```

---

## 写作规范（贯穿全文）

### 反 AI 写作规则

以下词组一律禁止，发现即替换：

- "Furthermore / Moreover / Additionally / In addition"
- "It is worth noting / It should be noted / It is important to note"
- "In this section/paper/survey, we discuss/present/review/examine"
- "This paper provides a comprehensive…" / "We delve into…"
- "In conclusion / To summarize / In summary"（段落开头）
- "plays a crucial/significant/key/pivotal role"
- "state-of-the-art"（改用年份 + 具体指标）

**写作风格要求：**

- 段落以**技术断言或数字**开头，不以元陈述开头
- 每段至少一句 8 词以内的短句
- 引用实际数据：从论文里读，不要预设
- 算法步骤用主动语态："The algorithm selects…" 而非 "Points are selected…"
- 缩写在首次出现时定义，之后只用缩写
- 不要预告章节内容——直接写内容

### wenqiao 格式规范

- 章节片段（`icp-survey/ch*.mid.md`）：**裸内容**，无文档头，直接从 `## N. 标题` 开始
- 正文引用格式：`[作者 年份](cite:key)`，**不用** `\cite{key}`
- `<!-- begin: raw -->...<!-- end: raw -->` 块内的 LaTeX 才用 `\cite{key}`（直接传给 LaTeX）
- 标签附在**目标节点下方**：先写图/表/公式，再写 `<!-- label: ... -->`
- BibTeX key 规范：`AuthorYYYYacronym`，如 `Besl1992icp`、`Chen1992p2plane`

### 图片规范

- 图片文件放 `examples/images/`
- 每张图标注 `<!-- ai-generated: true -->`
- `<!-- ai-prompt: ... -->` 在**执行时**根据上下文现写，不在此计划中预填
- 提示词语言：英文；图中需出现的中文标签用 `""` 包裹，如 `"算法流程"`

---

## 插图清单

| 标签 | 文件 | 内容描述 |
|------|------|---------|
| `fig:icp-pipeline` | `images/icp-pipeline.png` | 经典 ICP 四步流程图 |
| `fig:taxonomy` | `images/icp-taxonomy.png` | 变体分类树（6 大分支）|
| `fig:convergence` | `images/convergence-curves.png` | P2P / P2Plane / AA-ICP 收敛曲线对比 |
| `fig:timeline` | `images/icp-timeline.png` | 1992–2025 发展时间轴 |
| `fig:dl-taxonomy` | `images/dl-registration.png` | 深度学习配准方法分类 |
| `fig:fpga-pipeline` | `images/fpga-pipeline.png` | FPGA 流式流水线架构 |
| `fig:hw-comparison` | `images/hw-comparison.png` | CPU/GPU/FPGA/ASIC/PIM 延迟与功耗对比柱状图 |
| `fig:codesign-space` | `images/codesign-space.png` | 精度–延迟–功耗 Pareto 前沿散点图 |

---

## Phase 0：基础设施

创建目录结构和空 BibTeX 文件，提交骨架：

```bash
mkdir -p examples/images examples/icp-survey
touch examples/icp.bib
git add examples/ && git commit -m "chore: scaffold ICP survey directories"
```

---

## Phase 1：BibTeX 收集（5 组并行）

每组写入**独立临时文件**（避免并发冲突），最后由 Task 1.Z 合并。

对每篇相关论文：用 `mcp__drflow__search_papers` 或 `mcp__drflow__search_papers_by_keyword` 检索，用 `mcp__drflow__get_paper_bibtex` 获取条目，写入对应临时文件。

### Task 1.A：经典 ICP 基础

**目标论文：** Besl & McKay 1992、Chen & Medioni 1992、TrICP、Pomerleau survey、Horn 四元数法、Kabsch SVD。

**写入：** `examples/icp-1A.bib`

**参考搜索词：**
- `"iterative closest point original 1992 Besl McKay"`
- `"point to plane ICP Chen Medioni surface normals"`
- `"trimmed ICP TrICP outlier robust point cloud"`
- `"review point cloud registration mobile robotics Pomerleau"`

---

### Task 1.B：算法变体论文

**目标论文：** AA-ICP、VICP、Go-ICP、Dual Quaternion ICP、Correntropy ICP、DICP、RANSAC 变体、FGR、FPFH、Super4PCS。

**写入：** `examples/icp-1B.bib`

**参考搜索词：**
- `"Anderson acceleration ICP convergence"`
- `"velocity prediction ICP dynamic scanning"`
- `"Go-ICP global optimal branch bound"`
- `"fast global registration FGR FPFH"`
- `"correntropy robust ICP outlier"`
- `"Doppler ICP dynamic objects 4D LiDAR"`

---

### Task 1.C：深度学习配准论文

**目标论文：** DCP、DeepICP、DeepVCP、RPM-Net、NAR-\*ICP、PointDifformer、Learning single optimization。

**写入：** `examples/icp-1C.bib`

**参考搜索词：**
- `"deep closest point transformer registration ICCV 2019"`
- `"RPM-Net Sinkhorn soft assignment registration"`
- `"neural algorithm reasoning ICP execution 2025"`
- `"diffusion transformer point cloud registration 2024"`

---

### Task 1.D：硬件加速论文

**目标论文：** Tigris、Tartan、QuickNN、PICK PIM、SoC-FPGA ICP、HA-BFNN-ICP、NDT FPGA、FPGA-PointNet、Multi-Mode FPGA、GPU KNN TACO 2025。

**写入：** `examples/icp-1D.bib`

**参考搜索词：**
- `"Tigris 3D perception processor MICRO 2019"`
- `"Tartan robotics processor ISCA 2024"`
- `"QuickNN KD-tree GPU accelerator HPCA"`
- `"PICK SRAM PIM KNN accelerator DAC 2025"`
- `"HA-BFNN ICP FPGA brute force nearest neighbor 2025"`
- `"NDT FPGA localization autonomous driving"`
- `"GPU voxel KNN point cloud registration TACO 2025"`

---

### Task 1.E：应用与基准论文

**目标论文：** ETH dataset、KITTI LiDAR、nuScenes、3DMatch、ModelNet40、LiDAR SLAM surveys。

**写入：** `examples/icp-1E.bib`

**参考搜索词：**
- `"ETH benchmark point cloud registration outdoor"`
- `"KITTI LiDAR odometry benchmark dataset"`
- `"3DMatch indoor benchmark registration descriptor"`
- `"LiDAR SLAM survey autonomous driving localization"`

---

### Task 1.Z：合并与去重（在 1.A–1.E 之后）

合并五个临时文件，去除重复 key，写入 `examples/icp.bib`：

```bash
cat examples/icp-1A.bib examples/icp-1B.bib examples/icp-1C.bib \
    examples/icp-1D.bib examples/icp-1E.bib > examples/icp-all.bib

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

git add examples/icp.bib && git commit -m "feat: collect all ICP survey BibTeX entries"
```

---

## Phase 2：章节写作（7 章并行）

每章写一个独立 `.mid.md` 片段，存入 `examples/icp-survey/`。片段无文档头，直接从 `## N. 标题` 开始。读论文（`mcp__drflow__get_paper_summary`）后按实际内容填写，不要预填数字。

---

### 第 1 章：Introduction

**文件：** `examples/icp-survey/ch1-intro.mid.md`

**章节标签：** `<!-- label: sec:intro -->`

**内容结构：**
- 开篇：点云配准的规模与重要性（用具体应用数字，从论文里读）
- 历史段：1992 年双起源（Besl/McKay 与 Chen/Medioni）
- ICP 的三个核心挑战：初始化、异常值、计算量（各一句话概括）
- 综述结构导览：每章一句话，不写 "本文将…" 式元陈述

**必须包含：**
- 图：`fig:timeline`（时间轴图）
- ≥ 4 个引用

**写完后：** 检查禁用词组（grep 命令见规范部分），提交 `feat(ch1)`。

---

### 第 2 章：Background and Preliminaries

**文件：** `examples/icp-survey/ch2-background.mid.md`

**章节标签：** `<!-- label: sec:background -->`

**内容结构：**
- 刚体变换数学表达：$T = (R, t) \in SE(3)$，目标函数（P2P 和 P2Plane 两个变体，均标 `<!-- label: eq:... -->`）
- ICP 四步循环：以编号列表呈现（不用 algorithm 环境）
- 收敛定理：使用 `<!-- begin: theorem -->...<!-- end: theorem -->` 环境；定理内容从 Besl 1992 论文中读取
- 挑战清单：每个挑战配一个具体例子（数据从论文里读）

**必须包含：**
- 图：`fig:icp-pipeline`
- 两个带标签的数学环境（P2P 目标函数、P2Plane 目标函数）
- 一个定理环境（`<!-- label: thm:convergence -->`）

**写完后：** 禁用词检查，提交 `feat(ch2)`。

---

### 第 3 章：Algorithm Variants

**文件：** `examples/icp-survey/ch3-variants.mid.md`

**章节标签：** `<!-- label: sec:variants -->`

这是最长的章节，包含 6 个小节和 1 个章节总结。

**§3.1 Correspondence Strategy**（`<!-- label: sec:correspondence -->`）
- 6 种对应策略的比较（读论文后确定内容）
- 双向一致性检验的公式（阈值 $d_{\max}$，标 `<!-- label: eq:bidirectional -->`）
- 比较表：列 Method / 特点 / 计算开销（内容读论文后填）

**§3.2 Outlier Handling**（`<!-- label: sec:outlier -->`）
- M-estimator 权重公式（Huber loss）
- TrICP 重叠率 $\rho$ 的定义
- 比较表：列 Method / 最大异常值率 / 相对开销 / 是否全局最优（内容读论文后填）

**§3.3 Convergence Acceleration**（`<!-- label: sec:convergence-accel -->`）
- AA-ICP：Anderson 加速原理（历史窗口 $m$）
- VICP：速度场预测
- 图：`fig:convergence`（P2P vs P2Plane vs AA-ICP 收敛曲线）

**§3.4 Transformation Estimation**（`<!-- label: sec:transform -->`）
- Kabsch SVD 推导（公式简述，2 个方程）
- 对偶四元数表示
- SE(3) vs Sim(3) 适用场景对比（用一个表或简短段落）

**§3.5 Global Initialization**（`<!-- label: sec:global-init -->`）
- 两阶段流程（文字描述，不用图）
- FPFH 描述子 + RANSAC 参数讨论
- FGR vs RANSAC 的成本函数比较
- Go-ICP 的分支定界策略

**§3.6 Deep Learning Methods**（`<!-- label: sec:dl -->`）
- 图：`fig:dl-taxonomy`
- 各类方法（基于特征匹配、端到端、混合）各 1–2 段
- 方法比较表：列 Method / 类别 / 骨干 / 数据集 / 是否需要法向量（内容读论文后填）
- 末尾自然过渡到硬件加速章节（用数据说明为何需要硬件）

**§3.7 Chapter Summary**（`<!-- label: sec:variants-summary -->`）
- 各变体类别与其解决挑战的对应关系
- DL 方法相对经典方法的优劣
- 变体设计的开放问题

**写完后：** 禁用词检查、所有表格有 `<!-- caption -->` 和 `<!-- label -->`、所有引用用 `[text](cite:key)` 格式，提交 `feat(ch3)`。

---

### 第 4 章：Software-Level Acceleration

**文件：** `examples/icp-survey/ch4-software.mid.md`

**章节标签：** `<!-- label: sec:software -->`

**内容结构：**

**§4.1 数据结构**（`<!-- label: sec:data-structures -->`）
- KD-Tree 平均查询复杂度与适用场景（读论文）
- 体素哈希表的均摊复杂度与优势
- 两者对比：适用规模、内存占用、GPU 友好性

**§4.2 降采样**（`<!-- label: sec:downsampling -->`）
- 体素网格降采样的参数选择
- 精度与速度的权衡（数据从论文里读）

**§4.3 并行化**（`<!-- label: sec:parallelism -->`）
- ICP 中 KNN 搜索的串行瓶颈分析（引用具体测量论文）
- OpenMP / CUDA 并行策略

**§4.4 近似 KNN**（`<!-- label: sec:approx-knn -->`）
- 近似精度参数 $\varepsilon$ 的定义和影响
- 精度损失与加速比的权衡

**比较表：** 列 Technique / 针对阶段 / 加速比 / 精度影响（内容读论文后填）

**章节小结段落**

**写完后：** 禁用词检查，提交 `feat(ch4)`。

---

### 第 5 章：Hardware Acceleration

**文件：** `examples/icp-survey/ch5-hardware.mid.md`

**章节标签：** `<!-- label: sec:hardware -->`

这是内容最丰富的章节，需要充分展开。

**§5.1 Motivation**（`<!-- label: sec:hw-motivation -->`）
- KNN 搜索在 ICP 中的运行时占比（引用论文测量数据）
- 各应用场景的实时性需求表：列 Application / 吞吐量 / 点云规模 / 延迟预算（内容读论文后填）

**§5.2 GPU Acceleration**（`<!-- label: sec:gpu -->`）
- SIMT 模型与 warp 级 KNN 并行
- 体素化 GPU KNN（TACO 2025）的架构特点与实测加速比（读论文）
- Kernel launch 开销分析：何时 GPU 反而慢于 CPU（阈值从论文读）

**§5.3 FPGA Acceleration**（`<!-- label: sec:fpga -->`）

§5.3.1 设计方法论：流式流水线概念、BRAM 预算（读论文）

§5.3.2 FPGA 加速器对比表（用 raw LaTeX，以支持多列）：
- 列：Work / Platform / Search Method / Application / 关键指标 / Published
- 行：SoC-FPGA ICP、NDT FPGA、HA-BFNN-ICP、Sun et al.、Multi-Mode、FPGA-PointNet
- 所有具体数值从论文读取后填入，不预填

§5.3.3 BFNN vs KD-Tree on FPGA：规则性优势 vs 搜索效率的权衡

**§5.4 Custom Processors**（`<!-- label: sec:custom-proc -->`）
- Tigris（MICRO 2019）：并行 KD-Tree 遍历引擎，能效与 GPU 对比（读论文）
- Tartan（ISCA 2024）：ICP 内存带宽分析，roofline 模型定位（读论文）
- 各一段，包含论文实测数字

**§5.4.2 Processing-in-Memory**（`<!-- label: sec:pim -->`）
- PICK（DAC 2025）：bit-line 计算机制，消除 DRAM-CPU 带宽瓶颈（读论文）
- 峰值带宽 vs 实测 KNN 吞吐量
- 局限性：固定功能，无法运行完整 ICP 流水线

**§5.5 SW/HW Co-design**（`<!-- label: sec:codesign -->`）
- 图：`fig:hw-comparison`（各平台延迟与功耗对比）
- 图：`fig:codesign-space`（延迟 vs 功耗 Pareto 前沿）
- 量化误差传播分析（INT16 精度对旋转误差的影响，从论文读数据）
- 综合比较表：列 Platform / 典型延迟 / 功耗 / 精度损失 / 可编程性（内容读论文后填）

**§5.6 Chapter Summary**（`<!-- label: sec:hw-summary -->`）
- GPU vs FPGA vs 定制处理器的横向比较
- 未解决的开放问题
- 引用 4–5 篇论文的具体数字

**写完后：**
- 禁用词检查
- raw LaTeX 表格语法验证
- 确认所有表/图有 caption 和 label
- 提交 `feat(ch5)`

---

### 第 6 章：Applications and Benchmarks

**文件：** `examples/icp-survey/ch6-benchmarks.mid.md`

**章节标签：** `<!-- label: sec:benchmarks -->`

**§6.1 Applications**（`<!-- label: sec:applications -->`）
- 四个应用场景各一段：自动驾驶、机械臂抓取、无人机 SLAM、工业检测
- 每段包含：使用的 ICP 变体、精度/延迟要求、代表性系统引用（读论文）

**§6.2 Datasets**（`<!-- label: sec:datasets -->`）
- 数据集比较表：列 Dataset / Type / 规模 / Ground Truth / 常见用途
- 数据集：Stanford Bunny、ETH（ASL）、KITTI Odometry、3DMatch、nuScenes、ModelNet40
- 具体扫描数、点数等从论文/数据集文档读取后填

**§6.3 Evaluation Metrics**（`<!-- label: sec:metrics -->`）
- 定义 RTE、RRE、Recall、Chamfer Distance、runtime（各一个公式，标签）

**§6.4 Method Comparison**（`<!-- label: sec:comparison -->`）
- 大型对比表（raw LaTeX，支持多列）：列 Method / ETH RTE / ETH RRE / KITTI RTE / Time / Category
- 覆盖：P2P ICP、P2Plane ICP、NDT、AA-ICP、FGR+ICP、DCP、RPM-Net、HA-BFNN 等
- 所有数值从论文（`mcp__drflow__get_paper_summary`）读取后填，不可用的标 `--`

**写完后：** 禁用词检查，所有表格有 caption 和 label，提交 `feat(ch6)`。

---

### 第 7 章：Future Directions & Conclusion

**文件：** `examples/icp-survey/ch7-conclusion.mid.md`

**§7 Open Challenges and Future Directions**（`<!-- label: sec:future -->`）

每个挑战写一段实质性内容（从论文读数据后展开），不只是列表：

1. **实时百万点处理** — 当前 FPGA/GPU 设计的规模上限（读论文），差距分析
2. **动态场景鲁棒性** — DICP 的 Doppler 方案局限；预过滤替代方案
3. **经典–深度学习协同** — NAR-\*ICP 的探索；跨域泛化的开放问题
4. **统一 SW/HW 优化** — 现有加速器未联合优化全流程；编译器级协同机会
5. **深度变体的收敛理论** — DCP/RPM-Net 缺乏收敛保证；与最优传输理论的联系
6. **量化精度界** — INT8 ICP 的误差界作为开放理论问题

**§8 Conclusion**（`<!-- label: sec:conclusion -->`）

两段，不超过：
- 第一段：ICP 是什么，为什么重要（具体陈述）
- 第二段：三个主轴（算法、软件、硬件）的现状与走向

**禁止：** "This paper provides a comprehensive overview…" 类句型。

**写完后：** 本章最容易出现 AI 写作风格，禁用词检查必须严格执行，提交 `feat(ch7-8)`。

---

### Task 2.8：生成 AI 插图（在所有章节完成后）

调用 `generate-figures` skill 扫描章节文件中的 `<!-- ai-generated: true -->` 和 `<!-- ai-prompt: ... -->` 指令，生成对应图片。

验证所有 8 张图片存在后提交。

---

## Phase 3：合并与润色

### Task 3.1：验证引用一致性

检查所有章节中使用的 `cite:key` 是否都在 `icp.bib` 中存在，缺失的从 drflow 补充。

```bash
for key in $(grep -hE '\]\(cite:[^)]+\)' examples/icp-survey/ch*.mid.md | \
             grep -oE 'cite:[^?,]+' | sed 's/cite://'); do
  grep -q "@.*{$key," examples/icp.bib || echo "MISSING: $key"
done
```

### Task 3.2：写文档头并合并

创建 `examples/icp-survey.mid.md`，写文档头（documentclass、packages、title、author、abstract 等），再追加各章节片段。

文档头须包含：
- `<!-- documentclass: article -->`（或 `ctexart` 如需中文）
- `<!-- bibliography: icp.bib -->`
- `<!-- bibstyle: IEEEtran -->`
- `<!-- title: Iterative Closest Point: ... -->`
- `<!-- abstract: | ... -->`（abstract 内容待章节写完后根据实际内容总结）
- `<!-- preamble: | ... -->`（`\norm`、`\argmin`、`\KNN` 等宏定义）

合并脚本：

```bash
for ch in ch1-intro ch2-background ch3-variants ch4-software \
           ch5-hardware ch6-benchmarks ch7-conclusion; do
  echo "" >> examples/icp-survey.mid.md
  cat examples/icp-survey/${ch}.mid.md >> examples/icp-survey.mid.md
done
```

检查重复标签：

```bash
grep "<!-- label:" examples/icp-survey.mid.md | sort | uniq -d
```

### Task 3.3：反 AI 润色

在合并后的文档上运行禁用词检查：

```bash
grep -inE "furthermore|moreover|it is worth|it should be noted|this (section|paper|survey) (presents|discusses|examines|reviews|provides)|comprehensive|crucial role|pivotal role|significant role|state-of-the-art|in conclusion,|to summarize,|in summary," examples/icp-survey.mid.md
```

每处命中均需改写：
- 把连接词开头改为技术断言
- 把 "plays a crucial role" 改为具体作用 + 数字
- 把 "state-of-the-art" 改为 "[年份方法] achieves X on Y dataset"

检查句子长度多样性（每段应有 ≥ 1 句 8 词以内短句），修正后提交。

---

## Phase 4：验证

运行 wenqiao 转换器检查格式：

```bash
uv run python -m wenqiao examples/icp-survey.mid.md --target latex -o /tmp/icp-survey.tex
grep -E "\\\\cite\{MISSING|undefined" /tmp/icp-survey.tex || echo "OK: no missing citations"
```

发现错误则修复源文件后重跑。

---

## 执行方式

Phase 1（BibTeX）和 Phase 2（章节写作）均为高度并行任务：
- Phase 1：5 个子 agent 同时执行 Task 1.A–1.E
- Phase 2：7 个子 agent 同时执行各章写作

每个章节子 agent 的交接说明：
> "写 `examples/icp-survey/chN-*.mid.md`，wenqiao `.mid.md` 片段格式（无文档头），直接从 `## N. 标题` 开始。遵守反 AI 写作规则。正文用 `[text](cite:key)` 引用，BibTeX key 已在 `examples/icp.bib`。图片放 `examples/images/`，标注 `ai-generated: true`，ai-prompt 在执行时根据上下文现写（英文，中文标签用 `""` 包裹）。所有数值从 drflow 读论文后填写，不预填。"
