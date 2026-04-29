# rag-nano 中文使用指南（傻瓜版）

> 英文版：[`README.md`](README.md) · 完整规约：[`specs/001-minimal-rag-loop/`](specs/001-minimal-rag-loop/)

## 这是什么

一句话：**一个让你的本地知识"变得能被 AI 检索"的小工具**。

你把笔记、FAQ、SOP 等文档喂进去 → 它切块、做向量、存索引 → 外部的 AI agent 通过一个 HTTP 接口来查 → 每次返回相关片段 + 出处（哪份文件、第几段、相关分）。

它**不是**：聊天机器人、问答模型、prompt 框架。**只**负责"找到相关内容并标清出处"，怎么用这些内容讲话是 agent 自己的事。

---

## 第一次准备（5 步）

打开任何一个终端（macOS 的「终端」.app、iTerm、VS Code 内置终端都行），**所有命令都在项目目录下执行**：

```bash
# 1. 进项目目录（以下所有命令都在这里跑）
cd /Users/3bluebytes/workspace/projects/rag-nano

# 2. 装依赖（uv 自动建虚拟环境）
uv sync

# 3. 下载嵌入模型（约 2.3GB，仅第一次）
uv run scripts/download_models.sh

# 4. 复制配置文件（可选，默认值就能跑）
cp .env.example .env

# 5. 验证：看看种子语料是否在
uv run rag-nano stats
```

如果第 5 步看到 `Chunk count: 10` / `Source count: 5` 就说明环境 OK 了。

---

## 5 个常用命令

| 命令 | 用途 |
|---|---|
| `uv run rag-nano stats` | 看现在索引里有多少内容 |
| `uv run rag-nano ingest <路径>` | 把新文档喂进去 |
| `uv run rag-nano serve` | 开 HTTP 服务（让 agent 来查） |
| `uv run rag-nano eval` | 跑测试集，量化检索质量 |
| `uv run rag-nano wipe-index --yes` | 清空所有索引（**不可恢复**） |

---

## 看看现在里面到底有啥

### 总览

```bash
uv run rag-nano stats
```

### 列出每一份文档

```bash
sqlite3 .rag-nano/structured.db -box \
  "SELECT source_path, data_type, category, chunk_count
   FROM knowledge_source ORDER BY ingested_at DESC;"
```

### 看某份文档被切成了什么样

```bash
sqlite3 .rag-nano/structured.db -box \
  "SELECT position, substr(text, 1, 80) AS preview
   FROM knowledge_chunk
   WHERE source_id = (
     SELECT source_id FROM knowledge_source
     WHERE source_path = 'tests/fixtures/seed_corpus/sop_hotfix_zh.md'
   )
   ORDER BY position;"
```

把上面 `source_path = '...'` 里的路径换成你想看的那份即可。

### 用一句真实问题打个探针

先开服务（这个终端会一直占着）：
```bash
uv run rag-nano serve
```

**另开一个终端**，进同一个项目目录，发请求：
```bash
curl -s -X POST http://127.0.0.1:8089/v1/retrieve \
     -H 'content-type: application/json' \
     -d '{"query":"灰度发布","k":3}' | jq '.results[] | {source_path, score, data_type}'
```

如果返回空 / 都不相关 → 说明这块知识不够，该 ingest 更多了。

---

## 喂自己的文档进来

最常见的就是这一步：

```bash
# 单个文件
uv run rag-nano ingest ~/Documents/notes/我的SOP.md

# 整个目录（自动展开里面的文件）
uv run rag-nano ingest ~/Documents/我的笔记/

# 顺便指定类型 / 分类（覆盖文件 frontmatter）
uv run rag-nano ingest ~/notes/ --data-type sop --category ops
```

**支持的类型**（`--data-type` 可选值）：
`document`、`faq`、`sop`、`case_study`、`issue_summary`、`wiki`、`config_note`、`knowledge_card`、`code_summary`、`log_summary`。

**会被自动拒掉的内容**：
- 原始日志 / 栈跟踪 / JSON dump → `cold_data_*`
- 含 AWS / GitHub / Stripe key、JWT、`password=xxx` → `credential_*`
- 不支持的文件扩展名 → `unsupported_format`

ingest 结束会打印 per-file 的 ✓ / ✗，被拒的会写明原因。

**重要**：ingest 完后如果服务还开着，要重启它（v1 没做热加载）：
```bash
# 在跑 serve 那个终端按 Ctrl+C，然后重新开
uv run rag-nano serve
```

---

## 让 agent / 程序来用（HTTP 接口）

服务开起来后（`uv run rag-nano serve`），任何能发 HTTP 请求的代码都能用。

**Python 示例**：
```python
import httpx

resp = httpx.post(
    "http://127.0.0.1:8089/v1/retrieve",
    json={"query": "怎么部署热修复", "k": 5},
)
for hit in resp.json()["results"]:
    print(f"[{hit['score']:.2f}] {hit['source_path']}")
    print(hit["text"][:200])
    print()
```

**只查 SOP / FAQ 类型**：
```python
httpx.post(URL, json={
    "query": "怎么部署热修复",
    "k": 5,
    "filters": {"data_types": ["sop", "faq"]}
})
```

每条返回都带 7 个字段：`chunk_id` / `source_id` / `source_path` / `score` / `data_type` / `category` / `text` —— 你的 agent 自己拼答案 + 引用就行。

完整接口规约：[`specs/001-minimal-rag-loop/contracts/retrieval-api.md`](specs/001-minimal-rag-loop/contracts/retrieval-api.md)。

---

## 评估检索质量

```bash
uv run rag-nano eval
```

输出长这样：
```
recall@5 = 0.8500
hit_rate    = 0.8500
cases       = 20
delta vs previous: recall +0.0000, hit_rate +0.0000
```

**怎么改测试集**：直接编辑 [`eval/cases.yaml`](eval/cases.yaml)，加你自己的"用户会问什么 → 应该返回什么"对子。改完直接重跑，不用改代码。

每跑一次会追加一行到 `eval/history.jsonl`，方便回看质量随时间的变化。

---

## 常见问题

**Q：服务跑不起来，提示端口被占？**
```bash
lsof -i :8089       # 看谁占着
uv run rag-nano serve --port 8090   # 或换个端口
```

**Q：我 ingest 完了，但 `/v1/retrieve` 查不到新内容？**
v1 没做热重载。重启 `serve` 即可（`Ctrl+C` 然后再开一次）。

**Q：想推倒重来？**
```bash
uv run rag-nano wipe-index --yes
```
会删除整个 `.rag-nano/` 目录（SQLite + 向量矩阵）。`eval/history.jsonl` 不会被动。

**Q：第一次 ingest / serve 卡住很久？**
在下载嵌入模型（约 2.3GB），只第一次需要。之后会缓存到 `~/.cache/huggingface/`。

**Q：能换嵌入模型吗？**
能。改 `.env` 里的 `RAG_NANO_EMBEDDING_MODEL=...` 即可。**但换模型后必须 `wipe-index` + 重新 ingest**（不同模型向量空间不兼容）。

**Q：同一份文档重新 ingest 会重复吗？**
不会。系统按 `(路径, 内容哈希)` 去重：内容没变 → 跳过；内容变了 → 原子替换旧 chunk。

**Q：可以从其他目录运行命令吗？**
不能。所有 `uv run rag-nano ...` 命令必须在项目根（`pyproject.toml` 同级）执行，否则找不到虚拟环境和 `.rag-nano/` 索引。文档路径用绝对路径就好（如 `~/Documents/...`）。

---

## 想看更深的

- 完整 quickstart：[`specs/001-minimal-rag-loop/quickstart.md`](specs/001-minimal-rag-loop/quickstart.md)
- 为什么这么设计：[`specs/001-minimal-rag-loop/spec.md`](specs/001-minimal-rag-loop/spec.md)
- HTTP 接口规约：[`specs/001-minimal-rag-loop/contracts/retrieval-api.md`](specs/001-minimal-rag-loop/contracts/retrieval-api.md)
- 集成示例代码：[`tests/integration/test_agent_integration_chat.py`](tests/integration/test_agent_integration_chat.py)、[`tests/integration/test_agent_integration_workflow.py`](tests/integration/test_agent_integration_workflow.py)
