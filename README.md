# alawyer 智能法律顾问平台

一个具有学术性、权威性并切合实际的全栈智能法律顾问系统。基于 RAG 检索增强与多智能体辩论技术，提供法律智能问答、合同多智能体审查、法律知识库管理与知识图谱可视化能力。

## 功能总览

| 模块 | 功能 | 权限 |
| --- | --- | --- |
| 封面页 | 品牌封面 + 滚轮/按键滚动进入登录注册 | 所有人 |
| 主页仪表盘 | 问候语、实时时间戳、今日咨询数、合同审核数、知识库文档数、总用户数、法律领域分布、Neo4j 知识图谱、功能分块导览 | 登录用户 |
| AI 问答 | qwen2.5:1.5b + RAG（bge-large-zh 向量检索 + Cross-Encoder 精排），Markdown 渲染回答 + 出处可视化 + Redis 缓存 | 登录用户 |
| 合同审查 | 多智能体辩论式审查（风险官/合规官/公证官/仲裁官），评分仪表盘 + 雷达图 + 固定居中优化方案弹窗 | 普通/律师/管理员功能各异 |
| 知识库 | 多格式文档导入删除、自定义或自动命名、更新时间戳、自动领域分类 | 普通用户只读；律师/管理员可增删 |
| 个人设置 | 头像/昵称/密码修改（需原密码） | 登录用户 |
| 用户管理 | 独立功能页：用户概览统计、律师/普通用户分块展示、每页 8 人分页、按用户名查询、调整职位 | 仅超级管理员 |
| 全局 | 在线/离线/隐身状态切换、Dark/Light 模式全局切换 | 登录用户 |

## 技术栈

- 前端：Vue 3.5 + TypeScript + Vite 5 + Element Plus + Pinia + ECharts + markdown-it
- 后端：FastAPI + SQLAlchemy + PyJWT + passlib
- 业务存储：MySQL 8.0（Docker，宿主机 3307）
- 缓存：Redis 7（Docker，6379）—— AI 问答结果缓存，命中直接返回并标注
- 知识图谱：Neo4j 5 Community（Docker，7474/7687）—— 文档-领域-关键词三层图谱
- 向量库：Chroma（本地持久化，bge-large-zh-v1.5 1024 维中文专业嵌入）
- 大模型：Ollama（qwen2.5:1.5b 生成 / quentinz/bge-large-zh-v1.5:latest 嵌入）
- 精排：my-rerank 容器（Cross-Encoder 批量精排，单次 HTTP 请求）

## 目录结构

```
alawyer/
├── docker-compose.yml          # MySQL + Redis + Neo4j 编排
├── alawyer_logo.png            # 品牌 logo 源文件
├── samples/                    # 示例合同
├── backend/
│   ├── .env                    # 环境变量（可覆盖 config.py 默认值）
│   ├── requirements.txt
│   ├── seed_docs/              # 6 份法律领域种子文档（首次启动自动导入）
│   ├── data/chroma/            # Chroma 向量库持久化
│   ├── uploads/                # 知识库文件与头像上传目录
│   └── app/
│       ├── main.py             # 应用入口 + SPA 静态托管 + 种子初始化
│       ├── config.py           # 全部配置项
│       ├── models.py           # MySQL ORM 模型
│       ├── schemas.py          # Pydantic 出入参
│       ├── deps.py             # JWT 认证与 RBAC 依赖
│       ├── utils.py            # 文件解析/分块/关键词/领域分类
│       ├── routers/            # auth / dashboard / chat / contracts / knowledge / users
│       └── services/
│           ├── ollama_client.py  # Ollama 封装（chat / embed / JSON 模式）
│           ├── embedding.py      # 嵌入服务（Ollama 不可用回退本地哈希向量）
│           ├── rerank.py         # Cross-Encoder 精排（不可用降级 LLM 逐条打分）
│           ├── chroma_store.py   # Chroma 向量存取
│           ├── rag.py            # 检索增强管线（召回→精排→阈值过滤→Prompt 组装）
│           ├── agents.py         # 多智能体合同审查（辩论 + 仲裁评分）
│           ├── neo4j_service.py  # 知识图谱构建
│           └── redis_cache.py    # 问答缓存
└── frontend/
    ├── src/
    │   ├── views/               # Cover / Home / Chat / Contract / Knowledge / UserManage / Settings
    │   ├── components/AppLayout.vue  # 侧边栏 + logo + 头像/状态/主题
    │   ├── stores/              # auth / theme (Pinia)
    │   ├── api/index.ts         # Axios 封装 + 全部 API
    │   └── router/index.ts      # 路由守卫
    └── dist/                    # 构建产物（由后端 :8000 直接托管）
```

## 快速启动

### 0. 前置条件

- Docker Desktop，且本地已有以下镜像：mysql:8.0、redis:7-alpine、neo4j:5-community、rerank 服务镜像
- 宿主机已安装 Ollama 并拉取模型：

```
ollama pull qwen2.5:1.5b
ollama pull quentinz/bge-large-zh-v1.5:latest
```

- Rerank 精排容器（Cross-Encoder，端口 9999）需处于运行状态；未运行时系统自动降级为 LLM 逐条打分，不影响使用。

### 1. 启动基础设施

```
cd E:\alawyer
docker compose up -d
```

包含：alawyer-mysql（3307）、alawyer-redis（6379）、alawyer-neo4j（7474/7687）。

### 2. 启动后端

```
cd E:\alawyer\backend
D:\anaconda3\python.exe -m pip install -r requirements.txt
D:\anaconda3\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> 运行环境：conda base（D:\anaconda3）。依赖已安装齐全，日常启动只需第二行命令。

首次启动自动完成：建表、写入内置账户、导入 6 份种子法律文档（分块 + 向量化）、构建 Neo4j 图谱。

### 3. 启动前端（二选一）

- 生产模式（推荐）：后端直接托管前端构建产物，访问 http://127.0.0.1:8000 即可

```
cd E:\alawyer\frontend
npm install
npm run build
```

- 开发模式（热更新，代理 API 到 8000）：

```
npm run dev
# 访问 http://127.0.0.1:5173
```

## 内置账户

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |
| lawyer01 | lawyer123 | 律师 |
| user01 | user123 | 普通用户 |

登录后系统按用户名自动识别角色并赋予对应功能（无需选择登录入口）。

## 权限矩阵

| 能力 | 普通用户 | 律师 | 超级管理员 |
| --- | --- | --- | --- |
| AI 问答 / 知识库查看 | Y | Y | Y |
| 合同上传与审查 | Y | Y | Y |
| 查看所有人审查记录 | - | - | Y |
| 律师复核（修改多智能体结论） | - | Y | - |
| 删除审查记录 | Y（本人） | - | Y |
| 知识库导入/删除 | - | Y | Y |
| 用户管理（分块/分页/查询/改职位） | - | - | Y |

## API 一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/health | 健康检查（各服务状态） |
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录（返回 JWT） |
| GET | /api/dashboard/summary | 仪表盘汇总统计 + 图谱 + 趋势 |
| POST | /api/chat/ask | AI 问答（RAG + Redis 缓存） |
| GET | /api/chat/history | 问答历史 |
| POST | /api/contracts/upload | 上传合同 |
| POST | /api/contracts/{id}/review | 触发多智能体审查 |
| GET | /api/contracts/list | 审查列表（按角色过滤） |
| GET | /api/contracts/{id} | 审查详情 |
| PUT | /api/contracts/{id}/lawyer-review | 律师复核 |
| DELETE | /api/contracts/{id} | 删除审查记录 |
| GET | /api/kb/list | 知识库文档列表 |
| POST | /api/kb/upload | 导入文档（自动命名/领域分类/向量化/图谱） |
| DELETE | /api/kb/{id} | 删除文档（同步清向量与图谱） |
| GET/PUT | /api/users/me | 个人信息 |
| PUT | /api/users/me/password | 修改密码（需原密码） |
| PUT | /api/users/me/status | 在线/离线/隐身 |
| POST | /api/users/me/avatar | 上传头像 |
| GET | /api/users/list | 用户分块分页查询（管理员） |
| PUT | /api/users/{id}/role | 调整职位（管理员） |

交互式文档：http://127.0.0.1:8000/docs （FastAPI Swagger）。

## 核心机制

### RAG 检索增强问答

1. 用户提问 → Redis 缓存命中则直接返回（标注"缓存"）
2. bge-large-zh-v1.5（1024 维）将问题向量化 → Chroma 召回 Top-8 相邻切片
3. my-rerank Cross-Encoder 单次 HTTP 请求批量精排 → 取 Top-4
4. 精排最高分低于阈值（0.35）判定知识库无相关内容 → LLM 直答并标注"大模型直答"
5. 相关切片注入 Prompt → qwen2.5:1.5b 生成 Markdown 回答
6. 前端渲染 Markdown 并可视化展示出处文档与匹配片段

### 多智能体合同审查

- 风险官 / 合规官 / 公证官 三个智能体分别基于知识库检索与 LLM 推理出具 JSON 意见（评分 + 要点）
- 智能体之间可见彼此意见并可反驳，仲裁官汇总辩论结果给出最终评分与结论
- 律师可在多智能体结论基础上复核修改；评分以仪表盘 + 雷达图可视化，优化方案以固定居中弹窗展示

### 降级策略

| 组件 | 主方案 | 降级方案 |
| --- | --- | --- |
| 嵌入 | Ollama bge-large-zh | 本地哈希向量（1024 维） |
| 精排 | Cross-Encoder 批量 | LLM 逐条打分 |
| 智能体 JSON 解析 | Ollama JSON 模式 | 格式转换重试 + 本地兜底解析 |

## 常见问题

- MySQL 连接失败：确认 docker compose 中 mysql 容器健康（`docker ps`），端口为宿主机 3307。
- 回答缓慢：qwen2.5:1.5b 为本地 CPU/GPU 推理，RAG 全链路通常 30-90 秒；重复提问命中 Redis 缓存后秒回。
- 知识图谱为空：检查 neo4j 容器与 `NEO4J_PASSWORD`（默认 alawyer12345），重启后端自动重建。
- 前端改动不生效：重新 `npm run build`；后端托管的是 dist 产物。

## 测试记录

全链路浏览器端到端测试 14/14 通过：封面滚动、三种角色登录、主页仪表盘、知识库权限差异、个人设置权限差异、用户分页查询、头像状态菜单、暗黑模式切换、AI 问答（库内 RAG + 库外直答）均验证通过，无控制台错误。