# PRD 体系版本与协作记录约定

本文定义仓库内 **产品需求文档（PRD 正文）**、**变更日志**、**人机交互纪要**、**代码实现登记** 之间的关系与升位规则。执行开发或讨论后请按此更新，保证可追溯。

---

## 1. 文件角色

| 文件 | 作用 |
|------|------|
| [PRD_v1.0.3.md](PRD_v1.0.3.md) | **需求冻结正文**（当前 v1.0.3）。仅当商业/物理/公式承诺变化时修改正文并升版。 |
| [CHANGELOG.md](CHANGELOG.md) | **正式版本线**：每个对外可见的文档或产品版本至少一行（版本号、日期、摘要）。 |
| [SESSION_LOG.md](SESSION_LOG.md) | **交互纪要**：每次与协作者（含 AI）有意义对话结束后，提炼要点追加一节。 |
| [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md) | **实现登记**：每次完成代码层级交付后，列出改动文件与行为、关联 PRD 章节。 |
| [requirements.md](requirements.md) | **需求池（Rxxx）**：讨论中条目；已冻结入 PRD 的条目须在 CHANGELOG/正文可追溯到版本。 |
| [implementation_matrix.md](implementation_matrix.md) | **追溯矩阵**：PRD 章节 ↔ 代码 ↔ 测试，便于审计与补缺。 |

---

## 2. 语义化版本 X.Y.Z（PRD 正文与发布标签）

与 [CHANGELOG.md](CHANGELOG.md) 表内版本一致，细化为：

- **X（主版本）**：不兼容变化——例如结算/物理口径变更导致旧方案 JSON 或 CSV 语义失效、公式对用户可见结果的定义反转。
- **Y（次版本）**：向后兼容的**功能扩展**——新电价模式、新批发结算模式、新页面、新配置字段，旧数据仍可读。
- **Z（修订号）**：**澄清、措辞、笔误、纯测试、无行为变化的重构**；或仅增补 SESSION_LOG / IMPLEMENTATION_LOG / 矩阵而不改 PRD 正文时，可在 CHANGELOG 记 **文档/流程** 类条目（可不升 PRD 正文标题版本）。

**交互纪要（SESSION_LOG）**：默认**不**升 PRD 正文版本；若纪要结论写入 PRD 冻结段落，则必须：正文升版 + CHANGELOG 一行 + 如有代码则 IMPLEMENTATION_LOG 一节。

**代码实现**：凡改变运行时行为，**必须** IMPLEMENTATION_LOG；若行为已在 PRD 承诺内且仅为修复对齐，通常升 Z；若新增对外能力，通常至少升 Y。

---

## 3. 每次工作结束时的检查清单

1. 若有产品/公式层面的正文修改：更新 `PRD_v*.md` 顶部版本与目录相关章节 → **CHANGELOG** 新行。
2. 若有对话决策 worth 记住：**SESSION_LOG** 新节（日期 + bullet）。
3. 若有代码合并：**IMPLEMENTATION_LOG** 新节（文件列表 + 行为 + 关联 §）。
4. **implementation_matrix**：若新增模块或 PRD 章节职责变化，更新对应行。

---

## 4. 当前状态（维护者手动更新）

| 项目 | 值 |
|------|-----|
| PRD 正文冻结版本 | v1.0.3 |
| PRD 规范文件名 | `PRD/PRD_v1.0.3.md` |
| 最近 CHANGELOG 标签 | v1.1.1（视觉返工落地，2026-05-25） |
| 最近文档体系发布 | 见 CHANGELOG 最新行 |
