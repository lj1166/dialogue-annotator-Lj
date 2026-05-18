# dialogue-annotator

客服对话质检用的标注小工具。读入 `conversations.json`，人工给每条客服回复打三个标签：准不准、有没有跑题、有没有瞎编，结果存本地，能导出。

后端 Python + FastAPI，前端 Vue3，图表用的 ECharts。另外接了个本机 Ollama，可以要一版 AI 建议，但最终还是要人点保存。

## 能干什么

- 左侧挑对话，中间看 user / assistant 气泡
- 右侧打标：准确 / 跑题 / 编造，可写备注
- 标注写在 `backend/data/annotations.json`，关掉再开还在
- 顶栏导出 JSON、CSV
- 「统计看板」页看整体进度
- 「AI 建议」需要本机跑着 Ollama（我用的 `qwen2.5:7b`），只是参考，不点保存不算数

## 环境

- Python 3.10+
- Node 18+
- Ollama（可选）

## 怎么跑

**后端**

```bash
cd backend
pip install -r requirements.txt
python run.py
```

http://localhost:8000 ，接口文档 `/docs`

**前端**

```bash
cd frontend
npm install
npm run dev
```

浏览器开 http://localhost:5173

Windows 下如果终端中文是乱码，先 `chcp 65001` 再启后端，不影响页面和 json 文件。

**Ollama（可选）**

```bash
ollama pull qwen2.5:7b
ollama serve
```

模型名不对就改环境变量 `OLLAMA_MODEL`。

## 数据放哪

| 文件 | 说明 |
|------|------|
| `backend/data/conversations.json` | 题目给的对话，别改 |
| `backend/data/annotations.json` | 标注结果，运行后自动生成 |

原始样例在根目录 `任务一_conversations.json`，和 `backend/data` 里那份一样。

## 目录

```
├── backend/          # API、读写 json、调 Ollama
├── frontend/         # 标注页 + 统计页
├── 任务一_conversations.json
└── README.md
```

## 开发时用的

- Cursor 写代码、改 bug
- 本地 Ollama + Qwen2.5 7B 试 AI 建议接口

## License

MIT
