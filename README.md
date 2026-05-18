# Dialogue Annotator

智能客服对话质量标注工具。面向人工质检场景，支持对 `assistant` 回复进行多维度标注、进度统计、结果导出，并可选接入本地大模型生成预标注建议（Human-in-the-Loop）。

## 功能特性

- **对话浏览**：列表检索、逐条查看 user / assistant 多轮对话
- **质量标注**：针对每条客服回复标注「准确性 / 是否跑题 / 是否编造信息」，支持备注
- **断点续标**：标注结果持久化至 JSON，刷新或重启后自动恢复
- **数据导出**：支持 JSON、CSV 两种格式，便于下游分析
- **统计看板**：ECharts 展示标注进度与标签分布
- **AI 辅助标注（可选）**：通过 Ollama 调用本地模型生成建议，人工确认后写入

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.10+、FastAPI、Pydantic v2 | REST API、请求校验、OpenAPI 文档 |
| 运行时 | Uvicorn | ASGI 服务，开发模式热重载 |
| HTTP 客户端 | httpx | 异步调用 Ollama Chat API |
| 前端 | Vue 3、Vite 5、Vue Router 4 | Composition API、组件化页面 |
| UI | Element Plus | 表单、布局、反馈组件 |
| 可视化 | ECharts 5 | 进度环图、柱状图、饼图 |
| 存储 | JSON 文件 | 无数据库依赖，轻量部署 |
| LLM（可选） | Ollama + Qwen2.5 7B | 本地推理，预标注建议 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Vue 3 SPA)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ 对话列表     │  │ 对话详情     │  │ 质量标注 / 统计看板   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                 │                      │             │
│         └─────────────────┴──────────────────────┘             │
│                           │ axios (/api → proxy)               │
└───────────────────────────┼─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (:8000)                       │
│  conversations │ annotations │ stats │ export │ ai/suggest   │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
            ▼                             ▼
   data/conversations.json      Ollama (:11434) [可选]
   data/annotations.json
```

**设计要点**

- 前后端分离，接口契约由 Pydantic Model 约束，自动生成 Swagger 文档（`/docs`）
- 标注粒度：`conversation_id` + `turn_index`，仅对 `role=assistant` 的轮次落库
- AI 建议与正式标注解耦：模型输出经布尔值规范化后回填表单，须用户点击「保存」才写入 `annotations.json`

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- （可选）Ollama，并已拉取 `qwen2.5:7b`

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

- 服务地址：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

- 访问地址：http://localhost:5173
- 开发环境通过 Vite 代理将 `/api` 转发至后端

### 3. 生产构建（可选）

```bash
cd frontend && npm run build
# 可将 dist/ 交由任意静态服务器托管，并反向代理 /api 至后端
```

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # 路由与业务编排
│   │   ├── models.py            # Pydantic 数据模型
│   │   ├── store.py             # JSON 读写
│   │   ├── logging_config.py    # 日志 UTF-8 配置
│   │   └── services/
│   │       └── ollama.py        # Ollama 调用与 JSON 解析
│   ├── data/
│   │   ├── conversations.json   # 原始对话（只读）
│   │   └── annotations.json     # 标注结果（读写）
│   ├── requirements.txt
│   ├── run.py
│   └── test_api.py              # 接口冒烟测试
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── AnnotateView.vue # 标注工作台
│   │   │   └── StatsView.vue    # 统计看板
│   │   ├── api/index.js         # API 封装
│   │   └── router/index.js
│   └── vite.config.js
├── 任务一_conversations.json      # 题目原始数据备份
└── README.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/conversations` | 对话列表（含标注进度摘要） |
| GET | `/api/conversations/{id}` | 单条对话详情 |
| GET | `/api/annotations/{id}/{turn_index}` | 读取单条标注 |
| PUT | `/api/annotations` | 保存/更新标注 |
| GET | `/api/stats` | 全局统计（进度、标签分布） |
| POST | `/api/ai/suggest` | AI 预标注建议 |
| GET | `/api/export/json` | 导出 JSON |
| GET | `/api/export/csv` | 导出 CSV（UTF-8 BOM） |

## 数据格式

**输入对话**（`conversations.json`）

```json
{
  "id": "001",
  "turns": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ]
}
```

**标注记录**（`annotations.json`，key 为 `{conversation_id}:{turn_index}`）

```json
{
  "001:1": {
    "conversation_id": "001",
    "turn_index": 1,
    "accurate": true,
    "off_topic": false,
    "fabricated": false,
    "note": "",
    "ai_reason": "回复符合售后政策",
    "updated_at": "2026-05-18T12:00:00Z"
  }
}
```

**导出结构**（`/api/export/json`）

```json
{
  "exported_at": "2026-05-18T12:00:00Z",
  "items": [
    {
      "conversation_id": "001",
      "turn_index": 1,
      "user_content": "...",
      "assistant_content": "...",
      "accurate": true,
      "off_topic": false,
      "fabricated": false,
      "note": "",
      "ai_reason": "",
      "updated_at": "..."
    }
  ]
}
```

## 配置项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `qwen2.5:7b` | 模型名称 |

Windows 终端中文日志乱码时，启动前执行 `chcp 65001` 并设置 `PYTHONUTF8=1`（仅影响控制台显示，不影响 API 与文件编码）。

## 开发与测试

```bash
# 后端接口冒烟测试（需先启动 run.py）
cd backend && python test_api.py
```

后端采用分层组织：`store` 负责持久化，`services/ollama` 封装 LLM 调用与响应 JSON 提取；对模型返回的字符串布尔值（如 `"true"`）做规范化，避免前端无法回填。

前端标注页为三栏布局（列表 / 对话+进度 / 标注），统计页独立路由；通过 `provide/inject` 同步顶栏进度条。

## 开发工具

- **Cursor**：代码生成与调试辅助
- **Ollama**：本地 LLM 推理，用于 AI 建议接口验证

## License

MIT
