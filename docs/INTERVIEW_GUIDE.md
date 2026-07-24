# AgriGuard AI 面试复盘

## 1. 一分钟项目介绍

AgriGuard AI 是一个农业害虫识别与知识问答平台。我使用训练完成的 IP102 YOLO 检测害虫，FastAPI 负责图片安全校验、模型推理和任务持久化。检测类别先映射为人工审核的标准实体，再用实体 ID 过滤 Qdrant 中的资料。Qwen 只能依据本次检索证据生成结构化报告，引用由服务端校验并重建。系统使用 MySQL 保存长期业务数据、Redis 做 Agent 限流，Vue 3 和 Nginx 提供演示页面，并支持本地 Ollama 或显式选择的云 API。

## 2. 高频问题

### 为什么不直接把 YOLO 类别交给大模型？

类别名称不能提供可追踪证据，大模型可能补充错误的寄主、传播条件或农药剂量。项目先做标准实体映射，再执行 metadata filter，只允许使用已审核资料，并返回具体文档和 chunk 引用。

### 为什么 MySQL 和 Qdrant 都要保存分块信息？

Qdrant负责快速相似度检索；MySQL负责关系、审核状态、原文和引用一致性。检索后用 Qdrant point ID 回查 MySQL，避免把向量库 payload 当作唯一事实来源。

### ORM Model 和 Pydantic Schema 有什么区别？

ORM Model 描述数据库表和关系，生命周期受 SQLAlchemy Session 管理。Pydantic Schema 描述 API 输入输出并执行校验。分开后数据库字段变化不会自动暴露到公网 API。

### Session 的事务边界在哪里？

Repository执行查询，Service决定一个业务动作需要哪些写入共同提交。例如一次检测任务和全部检测框应在一个事务内完成；中途失败时回滚，任务不能错误地保持 `completed`。

### 为什么模型在 lifespan 中加载？

YOLO 权重加载成本高。lifespan 在进程启动时创建一个共享模型实例，请求只执行推理；关闭时统一释放数据库、Redis、Qdrant 和 HTTP 客户端。注意多个 Uvicorn worker 仍会各自加载一份模型。

### GPU 并发如何处理？

当前单进程使用异步锁串行进入 Predictor，避免多个请求同时抢显存。生产扩展时应按 GPU 建立有限 worker 或任务队列，而不是盲目增加 Uvicorn worker。

### mAP50 高为什么不等于可生产？

mAP50 对框的位置要求相对宽松，而且总体值会掩盖长尾类别。还要看 mAP50-95、各类别 AP、Recall、混淆矩阵、小目标表现和真实场景误检漏检。

### 为什么 Redis 故障时 Agent 问答要失败？

Redis 保存成本限流计数。如果 Redis 不可用仍继续调用 Qwen，就等于静默绕过限流。项目选择失败关闭并返回 503，检测历史等不依赖该限流的接口仍可工作。

### 为什么本地模型失败后不自动调用云 API？

图片诊断和农业数据可能涉及隐私；自动回退会在用户不知情时上传上下文。Provider 可以配置本地或云端，但切换必须显式进行。

### Agent 在项目中做什么？

Agent 只把用户问题改写为最多三个检索查询，并调用一个只读工具。任务 ID 固定它能访问的害虫实体。Agent 最终自由文本被丢弃，第二次结构化调用生成答案，引用必须属于工具实际看到的结果。

### 如何防止上传攻击？

系统同时检查文件大小、扩展名、MIME、文件签名、Pillow 解码结果和像素总数；使用 UUID 文件名，不信任用户路径，也不向 API 返回本地磁盘路径。

### 为什么使用异步数据库？

数据库和外部 HTTP 调用主要等待 I/O，异步可以让一个进程在等待时处理其他请求。但 YOLO 是计算任务，不能因为路由写成 `async` 就自动并行，所以仍需要显式并发控制。

### Docker 三个后端 target 的意义是什么？

`api` 用于快速接口联调，不含 PyTorch；`rag` 增加本地 Embedding；`full` 增加 YOLO。这样既保持完整部署能力，也避免每次修改普通 API 都重新构建大型模型依赖。

### 如何证明结果可复现？

项目记录模型版本、权重 SHA-256、类数、输入尺寸和模型卡；固定回归图片验证推理。数据库使用 Alembic 迁移，Python 使用 `pyproject.toml` 版本范围，前端使用 lockfile，Compose 固定服务镜像版本。

### 这个项目目前最大的生产风险是什么？

IP102 具有长尾、小目标和复杂背景问题；知识覆盖只审核部分演示类；单机 GPU 吞吐有限；本地小模型的总结能力弱于大型云模型。项目通过不确定性字段、知识审核门、引用校验和不自动云回退来限制风险，但不能替代现场农技诊断。

## 3. 必须能现场画出的数据流

```text
image
  -> upload validation
  -> YOLO
  -> detection_tasks + detection_objects
  -> reviewed class mapping
  -> pest_entity_id metadata filter
  -> Qdrant Top-K
  -> MySQL source lookup
  -> structured LLM generation
  -> citation/safety validation
  -> diagnosis_reports
```

## 4. 诚实说明取舍

- 当前是模块化单体，不拆微服务，因为业务规模不需要独立部署复杂度。
- Redis 只解决已出现的限流需求，没有为了技术栈而引入 Celery。
- TensorRT、Kubernetes、实时视频和自动训练不属于 MVP。
- 本地 Qwen 适合隐私和低成本演示；Linux GPU 生产环境可换 vLLM，Provider 接口保持不变。
- 药剂使用建议必须受来源、地域和标签约束，系统不生成无条件的绝对剂量。
