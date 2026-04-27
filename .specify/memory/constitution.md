<!--
=== Sync Impact Report ===
Version change: 0.0.0 → 1.0.0
Modified principles: All 10 principles created from template placeholders
Added sections: Core Principles (I through X), Governance
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check section is a placeholder; no hardcoded principle references)
  - .specify/templates/spec-template.md ✅ (no hardcoded principle references)
  - .specify/templates/tasks-template.md ✅ (no hardcoded principle references)
  - .specify/templates/commands/*.md — directory does not exist; nothing to check
Runtime guidance docs:
  - README.md — does not exist; nothing to check
Follow-up TODOs: None
=== End Sync Impact Report ===
-->

# RAG Nano Constitution

## Core Principles

### I. Documentation Before Implementation

任何功能开发前，必须先完成对应的设计文档、数据模型、接口定义、范围说明和验收标准。
不允许直接跳过设计进入编码。

- **MUST**: 每个功能在进入编码阶段前，拥有经评审的设计文档。
- **MUST**: 数据模型、接口定义和验收标准必须在实现前书面化。
- **MUST NOT**: 以"先写代码再补文档"的方式推进开发。

**Rationale**: 先文档后实现确保设计意图被记录、评审和共享，减少返工，
并为后续维护与知识沉淀提供可追溯的依据。

### II. Minimal Closed Loop First

第一版只允许实现 ingest、retrieval、evaluation 三条主链路。
不允许提前实现非第一版必须的能力。

- **MUST**: 第一版交付 ingest（数据摄取）、retrieval（知识检索）、evaluation（效果评测）
  三条主链路的完整闭环。
- **MUST NOT**: 在第一版中引入多 agent 编排、复杂前端、图数据库、复杂权限系统、
  消息队列或微服务拆分等能力。
- **MUST NOT**: 以"预留扩展性"为理由提前实现非必须组件。

**Rationale**: 最小闭环确保项目快速验证核心价值，避免过早优化和范围蔓延。
只有在主链路被验证有效后，才逐步扩展能力。

### III. High-Value Knowledge Priority

优先将高价值、高频复用的知识纳入知识库，而非无差别地收集所有数据。

优先进入知识库的数据类型包括：
- 文档、FAQ、SOP
- 历史案例、issue 总结
- wiki、配置说明
- 结构化知识卡片
- 代码摘要、日志摘要

- **MUST**: 数据入库前进行价值评估，确认其属于上述高价值类型之一。
- **MUST NOT**: 将低价值、低复用率的数据直接批量导入主知识库。

**Rationale**: 知识库的质量取决于内容价值而非数量。优先高价值知识可以最大化检索
命中率，降低噪音，提升用户体验。

### IV. Cold Data Prohibition

原始日志、全量源码、原始执行记录、超长对话、重复文档等属于冷数据，
不能直接进入主知识库。

- **MUST NOT**: 冷数据未经处理直接进入主知识库。
- **MUST**: 冷数据必须先经过清洗、摘要、归类、标签化和结构化处理，
  形成可复用知识卡片后才能入库。
- **MUST**: 建立冷数据处理流水线或最小化脚本，确保处理步骤可重复、可审计。

**Rationale**: 冷数据体积大、噪音高、检索价值低，直接入库会污染向量空间、
降低检索精度并增加存储成本。结构化处理是保障知识库质量的关键环节。

### V. Swappable Core Components

Embedding、Vector Store、Retriever、Metadata Extractor、Reranker、Structured Store
都必须通过接口抽象，不允许与某个具体模型、供应商、数据库或平台强绑定。

- **MUST**: 所有核心组件均通过接口或抽象基类定义契约。
- **MUST NOT**: 在业务逻辑中硬编码具体供应商（如特定 embedding 模型 API、
  特定向量数据库的查询语法）。
- **MUST**: 每个核心组件至少具备一个参考实现和一个 mock/testing 实现，
  以验证接口的通用性。

**Rationale**: 可替换性确保项目不被单一供应商锁定，允许根据效果、成本或合规要求
灵活切换底层实现，同时显著提升可测试性。

### VI. Pragmatic Technology Selection

如果多个技术方案都可行，优先选择本地容易跑通、容易调试、容易替换的方案，
而不是最复杂或最先进的方案。

- **MUST**: 技术选型文档中记录至少两个候选方案，并明确说明选择理由。
- **MUST**: 优先选择具备良好本地开发体验、充足文档和社区支持的方案。
- **MUST NOT**: 以"技术先进性"作为唯一或主要选型依据。

**Rationale**: 可落地与可调试的技术方案降低开发摩擦，加速迭代，并减少调试时间。
项目的核心目标是交付可用的知识检索能力，而非展示技术复杂度。

### VII. Explainable Retrieval

任何检索结果都必须返回来源、metadata、分数、所属分类、数据类型等信息，
不允许输出无法解释来源的答案。

- **MUST**: 每次检索返回的结果必须携带来源标识、 relevance 分数、数据类型、
  所属分类和原始 metadata。
- **MUST NOT**: 返回没有来源追溯的答案或摘要。
- **MUST**: 检索接口提供调试模式，可输出中间召回列表和重排序明细。

**Rationale**: 可解释性是知识检索系统建立用户信任的基础。开发者和最终用户必须
能够验证答案的来源和可信度，才能有效进行故障定位和知识审计。

### VIII. Loose Coupling with Agents

RAG 应当是一个可插拔组件，不应与某个具体 agent 强绑定。
任何 agent 都应该能够通过统一接口调用知识检索能力。

- **MUST**: 知识检索能力通过统一、稳定的 API 或 SDK 暴露。
- **MUST NOT**: 在检索层中嵌入特定 agent 的上下文格式、提示模板或业务逻辑。
- **MUST**: 文档中提供至少两个不同 agent 类型的接入示例（如聊天 agent、
  自动化工作流 agent）。

**Rationale**: 弱耦合确保 RAG 能力可以被多个 agent 复用，避免重复建设。
统一接口降低接入成本，使知识检索底座真正成为平台级能力。

### IX. Subtraction Over Addition

如果某项能力不是第一版必须项，则只保留接口或 TODO，不允许提前实现复杂版本。

- **MUST**: 功能实现前进行必要性审查；非必须项仅保留接口定义或 TODO 标记。
- **MUST NOT**: 为"未来可能用到"的场景提前实现完整功能。
- **MUST**: 每个 TODO 或接口占位符附带清晰的触发条件和验收标准，
  说明何时需要实现。

**Rationale**: 优先减法防止范围膨胀和过度工程化。保留接口但不实现，
既为未来扩展预留了空间，又避免当前代码库被未经验证的功能拖累。

### X. Minimum Evaluation Required

任何检索能力上线前，必须具备最小评测集、最小评测脚本，以及至少一个基础指标。

- **MUST**: 每个检索能力在上线前拥有不少于 20 条查询-期望结果对的评测集。
- **MUST**: 提供可自动化运行的评测脚本，输出至少一个基础指标
  （如 recall@k、hit rate 或 precision@k）。
- **MUST NOT**: 以"主观体验良好"替代量化评测作为上线依据。
- **MUST**: 评测结果随每次代码变更持续运行，并记录历史趋势。

**Rationale**: 量化评测是防止检索质量退化的唯一可靠手段。最小评测集确保
任何改动都可以被客观验证，为持续优化提供数据基础。

## Governance

### Amendment Procedure

对本章程的任何修改必须通过以下流程：

1. 以书面形式提出修改提案，说明修改内容、理由及对现有实现的影响。
2. 提案必须经过至少一次评审，确认修改不与现有原则冲突。
3. 修改被接受后，更新 `.specify/memory/constitution.md`，
   同步更新 `LAST_AMENDED_DATE` 和 `CONSTITUTION_VERSION`。
4. 在版本控制中提交修改，提交信息中注明版本变化和修改摘要。

### Versioning Policy

版本号遵循语义化版本控制（SemVer）：

- **MAJOR**（X.0.0）: 向后不兼容的治理变更，如原则的移除或重新定义。
- **MINOR**（x.Y.0）: 新增原则或章节，或对现有指导进行实质性扩展。
- **PATCH**（x.y.Z）: 措辞澄清、错别字修正、非语义性细化。

### Compliance Review

所有 Pull Request 和代码评审必须验证是否符合本章程原则：

- 新功能是否具备先文档的证据（如设计文档链接）。
- 新增组件是否通过接口抽象，未硬编码具体供应商。
- 检索相关变更是否伴随评测集或评测脚本的更新。
- 范围变更是否遵守"优先减法"原则，非必须项是否仅保留 TODO。
- 复杂度增加是否经过充分论证，并记录更简单的替代方案及拒绝理由。

**Version**: 1.0.0 | **Ratified**: 2026-04-23 | **Last Amended**: 2026-04-23
