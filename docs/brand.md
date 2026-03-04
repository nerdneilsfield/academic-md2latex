# 文桥 · Wenqiao

> **写在 Markdown，发于任何地方。**
> *Write once, render anywhere.*

---

## 品牌叙事：一座桥的诞生

学术写作之苦，不在思想深邃，而在格式纠缠。

你在 `.tex` 的括号森林里迷失，在 `\begin{} \end{}` 的迷宫里徘徊；你想用 Markdown 的简洁呼吸，却被引用、交叉引用、图表编号放逐至荒野。于是，**文桥**诞生了——

它无意取代 LaTeX 的严谨，也不否定 Markdown 的轻盈。
它只是**一座桥**：

> 一端连着你的思绪（Markdown 的纯净），  
> 一端连着世界的规则（LaTeX 的庄重、HTML 的开放、富文本的友好）。  
> 而你只需站在桥中央，写一份叫做 `.mid.md` 的稿子。

---

## 品牌定位

| 维度 | 表达 |
|------|------|
| **一句话** | 以 Markdown 为“唯一真源”，稳定渲染至 LaTeX、HTML 与富 Markdown |
| **核心意象** | 桥——连接创作与发表；同一份源文件，通往多种格式彼岸 |
| **差异主张** | `.mid.md` 中间稿格式、学术原生能力（引文/交叉引用/图表/环境）、可重复且可配置 |

---

## 命名体系

### 对外品牌
- **品牌名**：文桥 / Wenqiao
- **中间格式**：文桥 MID Markdown（口头简称：文桥中间稿）
- **源文件后缀**：`*.mid.md`

### 技术落地

| 场景 | 命名 |
|------|------|
| Git 仓库 | `wenqiao` |
| PyPI 包名 | `wenqiao` |
| Python 导入 | `import wenqiao` |
| CLI 命令 | `wenqiao` |
| 兼容别名 | `md-mid`（保留 1-2 版本，带 deprecation 提示） |

### 术语约定
- **渲染**（render）：统一使用，不混用 convert/compile
- **唯一真源**（canonical source）：`.mid.md` 的中间稿地位
- **模式**：`full`（完整稿）/ `body`（正文）/ `fragment`（片段）

---

## 口号选粹

### 中文
> 一稿多投，一桥通达。  
> 写在 Markdown，发于任何地方。  
> **把论文写作从"格式工程"里解放出来。**

### English
> Write once, render anywhere.  
> One manuscript, many outputs.  
> **Academic Markdown, rendered with rigor.**

---

## 产品故事

**问题**：学术写作在“内容”与“排版/投递格式”之间反复折腾。引用、交叉引用、图表、算法环境——这些让纯 Markdown 力不从心，也让纯 LaTeX 过于沉重。

**解法**：文桥定义 **Wenqiao MID Markdown** 为“唯一真源”。元数据栖身于 HTML 注释，正文保持 Markdown 的纯粹。一桥飞架，三方通达。

**结果**：同一份 `.mid.md`，稳定产出 LaTeX（投期刊）、HTML（做演示）、富 Markdown（协作审阅）。配合 `format` 与 `validate`，让写作可重复、可检查、可协作。

---

## 视觉气质

### Logo 意象
一座极简的桥拱。桥下流淌着 "MID"，桥两端分别是 "MD" 与 "TeX/HTML"。桥身一笔写成，如文人挥毫。

### 配色建议（选一套，从一而终）

| 风格 | 主色 | 辅色 | 强调 |
|------|------|------|------|
| **纸墨学术** | 米白 `#F5F5DC` | 墨黑 `#2C2C2C` | 青绿 `#5F9EA0` |
| **工程可靠** | 浅灰 `#F8F9FA` | 深蓝 `#1E3A5F` | 橙赭 `#D2691E` |

### 字体气质
- 展示：中文偏宋/仿宋之雅，英文衬线之稳
- 代码：等宽，不妥协

---

## 开源策略

**版本路径**  
从 `0.1.x` 起步，先稳格式规范，再赴 `1.0` 之约。

**兼容承诺**
- `.mid.md` 语法变更必附迁移指南
- CLI 老命令保留过渡期，温柔告别

**可信度建设**
- `examples/` 放 2-3 个范例：最小论文、图表引用、算法环境
- 配一张 "real-ish" 产物截图（LaTeX/PDF 与 HTML 并置）

---

## 命名细则

### 文件与配置
- 默认配置文件名：`wenqiao.toml`（或 `wenqiao.yaml`，二选一）
- 环境变量前缀：`WENQIAO_...`
- 模板目录名：`templates/wenqiao-*`（便于以后做模板库）

### 示例文件命名
- `paper.mid.md`（源）
- `paper.tex` / `paper.html` / `paper.md`（产物）

---

## 对外信息架构（官网/README 结构建议）

1. **Hero**：一句话定位 + 10 行 Quick Start
2. **概念**：Wenqiao MID 是什么，为什么需要中间格式
3. **能力**：引文、交叉引用、数学、图表、环境、模板、多层配置、i18n
4. **教程**：从 0 到出 LaTeX/HTML 的最小示例
5. **参考**：指令语法（HTML comment directives）与渲染差异表
6. **工程化**：format、validate、CI 建议、可复现构建
7. **Roadmap**：短期 3 项（模板生态、更多环境、错误信息改善）

---

## GitHub 项目简介（中英双语）

### 中文简介
文桥（Wenqiao）是以 Markdown 为“唯一真源”的学术写作工具，通过 `.mid.md` 中间稿格式，一键渲染至 LaTeX、HTML 与富 Markdown。

### English Description
Wenqiao treats Markdown as the canonical source for academic writing, rendering `.mid.md` intermediate format to LaTeX, HTML, and rich Markdown with one command.

---

## GitHub 项目标签

推荐使用以下标签，便于项目发现与分类：

- `markdown`
- `latex`
- `academic-writing`
- `publishing`
- `document-converter`
- `python`
- `research-tools`
- `citation`
- `cross-reference`
- `html`
- `static-site-generator`
- `cli`
- `open-source`

---

## 迁移落地清单

- [ ] `pyproject.toml`：name 改 `wenqiao`，description 焕新
- [ ] `src/md_mid` → `src/wenqiao`（含所有 import）
- [ ] CLI：新增 `wenqiao`，保留 `md-mid` 作别名
- [ ] README：全量替换品牌叙事
- [ ] 测试回归：全量通过

---

> *桥的意义不在于桥本身，而在于让渡者无感地到达彼岸。*  
> *—— 文桥*
