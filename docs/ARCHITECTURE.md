# AgriGuard AI 系统架构

## 1. 项目边界

AgriGuard AI 当前聚焦 IP102 农业害虫目标检测，不包含植物病害模型。系统把三类结果明确分开：

1. YOLO 给出的检测框、原始类别、置信度和数量。
2. MySQL 与 Qdrant 返回的已审核知识和来源。
3. 大语言模型基于本次检索证据生成的结构化总结。

大语言模型不能修改检测结果，也不能自行构造引用。

## 2. 运行架构

```mermaid
flowchart LR
    Browser[Vue 3 浏览器页面] -->|HTTP /api 和 /media| Nginx[Nginx]
    Nginx --> API[FastAPI]

    API -->|异步 SQL| MySQL[(MySQL)]
    API -->|向量检索 + entity_id 过滤| Qdrant[(Qdrant)]
    API -->|限流和短期状态| Redis[(Redis)]
    API -->|图片推理| YOLO[IP102 YOLO]
    API -->|OpenAI-compatible HTTP| LLM{LLM Provider}

    LLM --> Ollama[本地 Ollama / Qwen]
    LLM --> Cloud[显式选择的云 API]

    API --> Storage[(上传图和标注图)]
```

Nginx 是浏览器唯一入口。Vue 使用相对地址访问 `/api` 和 `/media`，因此 API Key 不会进入前端，开发和生产也能使用相同 URL。

## 3. 一次检测请求

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as Vue/Nginx
    participant A as FastAPI
    participant Y as YOLO
    participant D as MySQL
    participant Q as Qdrant
    participant L as Qwen/API

    U->>F: 上传图片
    F->>A: POST /api/v1/detections
    A->>A: 校验大小、MIME、文件签名和像素数
    A->>Y: 单例模型推理
    Y-->>A: 类别、置信度、BBox
    A->>D: 事务保存任务和目标
    A-->>F: 检测结果和标注图 URL

    U->>F: 请求诊断
    F->>A: POST /detections/{id}/diagnosis
    A->>D: 读取检测结果和已审核实体映射
    A->>Q: entity_id 过滤后的 Top-K 检索
    Q-->>A: point_id 和相似度
    A->>D: 用 point_id 回查原文和引用
    A->>L: 检测事实 + 允许使用的证据
    L-->>A: 结构化 JSON
    A->>A: Pydantic、引用集合和安全规则校验
    A->>D: 保存报告
    A-->>F: 报告和可信引用
```

## 4. 后端分层

| 层 | 责任 | 不应承担的责任 |
|---|---|---|
| API Router | HTTP 参数、状态码、响应模型 | SQL、YOLO 输出解析 |
| Service | 业务流程、事务边界、状态机 | FastAPI 路由细节 |
| Repository | SQLAlchemy 查询和持久化 | 业务决策 |
| Predictor | 模型加载、推理、后处理 | 数据库写入 |
| RAG | 解析、切块、Embedding、过滤检索 | 自由生成答案 |
| LLM Provider | 统一模型调用、超时和重试 | 自动选择云端回退 |
| Schema | 输入输出校验 | ORM 会话管理 |

FastAPI lifespan 只创建一次数据库连接池、Redis、Qdrant 客户端、YOLO、Embedding 和 LLM Provider。关闭应用时按相反顺序释放资源。

## 5. 数据存储职责

- MySQL：检测任务、目标框、模型版本、标准实体、文档、分块关联、审核状态和诊断报告。
- Qdrant：分块向量和用于过滤的 payload，不作为引用正文的唯一事实来源。
- Redis：Agent 请求限流；Redis 不可用时限流接口失败关闭，避免绕过成本保护。
- 文件卷：原图、标注图和本地 Embedding 缓存。

## 6. RAG 可信边界

```mermaid
flowchart TD
    Class[YOLO class_id] --> Mapping{映射已审核?}
    Mapping -->|否| Stop1[拒绝生成诊断]
    Mapping -->|是| Entity[标准 pest_entity_id]
    Entity --> Filter[Qdrant Metadata Filter]
    Filter --> Lookup[MySQL 回查原文与来源]
    Lookup --> Review{知识已审核且来源充分?}
    Review -->|否| Stop2[知识不足]
    Review -->|是| Generate[结构化生成]
    Generate --> Validate{JSON、引用、安全规则通过?}
    Validate -->|否| Stop3[不保存不可信报告]
    Validate -->|是| Persist[持久化报告]
```

LangChain Agent 只用于规划跟进问题的检索词。它只有一个只读检索工具，实体范围由检测任务固定；Agent 的自由文本会被丢弃，面向用户的答案由第二次结构化调用生成并校验。

## 7. 模型部署选择

后端镜像有三个累计目标：

- `api`：不安装 PyTorch，适合数据库、接口和云服务联调。
- `rag`：增加本地 sentence-transformer Embedding。
- `full`：再增加 Ultralytics YOLO/PyTorch。

Windows 开发使用 Ollama 运行 Qwen。Linux GPU 服务器可把同一 Provider 地址切换到 vLLM 的 OpenAI-compatible API，RAG 和业务服务无需修改。

## 8. 当前验证状态

- 后端单元/集成测试、Ruff、Mypy 已通过。
- Vue 单元测试和生产构建已通过。
- MySQL、Qdrant、Redis 的已有容器健康。
- 本地 Qwen、真实 YOLO、RAG 诊断和受限 Agent 流程分别完成过真实验证。
- 完整 Nginx + FastAPI 镜像构建仍需在容器仓库 TLS 恢复后执行 `scripts/smoke_deployment.py` 完成最终验收。
