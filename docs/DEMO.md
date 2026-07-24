# AgriGuard AI 演示手册

## 1. 演示目标

一次完整演示应证明：

1. 模型权重和数据版本可追踪。
2. 上传图片后执行真实 YOLO 推理。
3. 检测结果被持久化，而不是只显示在页面上。
4. 检测类别通过已审核映射进入 RAG。
5. Qwen 只根据检索资料生成结构化报告。
6. 页面展示可回查的资料来源。
7. 容器重启后历史任务仍存在。

## 2. 演示前检查

在私有 `.env` 中使用完整本地模式：

```dotenv
AGRIGUARD_BACKEND_TARGET=full
AGRIGUARD_YOLO_ENABLED=true
AGRIGUARD_YOLO_DEVICE=0
AGRIGUARD_EMBEDDING_ENABLED=true
AGRIGUARD_LLM_ENABLED=true
AGRIGUARD_LLM_PROVIDER=ollama
AGRIGUARD_LLM_BASE_URL=http://127.0.0.1:11434/v1
AGRIGUARD_CONTAINER_LLM_BASE_URL=http://host.docker.internal:11434/v1
AGRIGUARD_LLM_MODEL=qwen3:4b-instruct-2507-q4_K_M
AGRIGUARD_AGENT_ENABLED=true
```

确认模型和 Ollama：

```powershell
Set-Location backend
python scripts/verify_model_artifact.py
ollama list
```

首次构建 `full` 镜像和首次加载 Embedding 模型需要网络。正式演示前应完成下载并重启测试，避免把下载时间放进演示。

## 3. 启动与基础验收

```powershell
Set-Location ..
docker compose --env-file .env -f infra/compose.yaml up -d --build
docker compose --env-file .env -f infra/compose.yaml ps

Set-Location backend
python scripts/smoke_deployment.py
```

冒烟脚本必须输出四个 `PASS`，并以状态码 0 结束。

## 4. 页面演示顺序

打开 <http://127.0.0.1:8080>：

1. 展示顶部服务状态，说明它来自真实 readiness API。
2. 上传固定回归图片，不使用临时从网络寻找的图片。
3. 展示标注图、类别、置信度、BBox、数量和推理耗时。
4. 请求知识诊断，展示症状、危害、寄主、预防、防治建议和不确定性。
5. 展开资料来源，说明引用由服务端重建，而不是信任模型输出。
6. 提交一个跟进问题，展示 Agent 实际使用的检索词和受限实体范围。
7. 打开历史记录，再进入刚才任务的详情页。
8. 刷新浏览器，证明数据来自 MySQL，不是前端内存。

## 5. 数据持久化证明

记录刚生成的任务 ID，然后重启应用容器：

```powershell
docker compose --env-file .env -f infra/compose.yaml restart backend web
python scripts/smoke_deployment.py
```

重新打开任务详情。检测框和已生成报告应存在，并且读取报告时不再次调用 YOLO、Qdrant 或 Qwen。

## 6. 模型训练成果

演示以下材料：

- `model_artifacts/ip102-yolo26n/MODEL_CARD.md`
- 模型 manifest 和 SHA-256
- `data/runs/...` 中的 Precision、Recall、mAP50、mAP50-95
- PR 曲线和混淆矩阵
- 至少两个误检、两个漏检和一个小目标案例

解释指标时不要只报总体 mAP。说明类别不平衡、长尾类别、小目标召回、数据划分和相似图片泄漏风险。

## 7. 故障演示（可选）

选择一个没有审核知识的类别，系统应拒绝生成看似完整的诊断。停止 Redis 后调用 Agent 问答，系统应返回服务不可用，而不是绕过限流。这两个案例能证明安全边界确实由代码执行。

故障演示后恢复服务：

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d redis
python scripts/smoke_deployment.py
```

## 8. 演示结束

```powershell
docker compose --env-file .env -f infra/compose.yaml down
```

不要添加 `--volumes`，否则会删除本地数据库和向量库卷。
