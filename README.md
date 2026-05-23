# 双色球数据分析与推荐系统

一个基于 `Python + Flask + SQLite + Docker` 的双色球数据采集、分析、推荐与命中校验系统。

项目目标不是做一次性脚本，而是搭一套可以长期运行的后台服务：
- 定期从双色球官网同步真实开奖数据
- 将数据持续增量保存到本地数据库
- 基于数据库中的全部历史数据生成分析快照
- 生成推荐号码并保存结果
- 在开奖后自动核对推荐命中情况，统计命中率和奖级表现
- 通过 Web 后台查看数据、分析结果、推荐结果和任务执行情况

## 项目特点

- 真实数据源：对接中国福利彩票官网接口
- 增量采集：每次只抓最近 `100` 期，但只新增数据库中没有的期号
- 长期积累：数据库中的开奖历史会持续增长，不会因为下一次只抓 100 期就丢失旧数据
- 全库分析：分析快照基于数据库里的全部历史开奖数据，不局限于最近 100 期
- 推荐留存：推荐结果库保留最近 `1000` 条
- 任务留存：任务执行记录保留最近 `100` 条，前端显示最近 `10` 条
- Docker 持久化：容器重启后数据库数据不会丢失
- 自动调度：支持双色球开奖日前后自动执行同步、分析、推荐、校验

## 官方数据源

双色球官网开奖接口：

`https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice`

项目中也保留了一个独立采集脚本，便于单独验证抓取逻辑：

[爬取双色球.py](./爬取双色球.py)

## 当前已实现功能

### 1. 开奖数据采集

- 从官网接口抓取双色球历史开奖数据
- 每次采集最多读取最近 `100` 期
- 使用 `issue_no` 作为唯一识别，重复期号不会重复写入
- 支持同步最近开奖结果

### 2. 数据库存储

- 使用 SQLite 作为主数据库
- 默认数据库文件：`data/ssq_app.db`
- 历史开奖数据采用增量累积方式保存
- 分析快照、推荐记录、核对结果、任务记录分别单独存表

### 3. 分析快照

- 基于数据库中全部历史开奖数据生成分析快照
- 支持频次、冷热号、遗漏、模式、跨度、和值、AC 值等特征统计
- 支持按窗口生成快照，默认可以直接用全库数据

### 4. 推荐号码

- 基于最新分析快照生成推荐号码
- 当前内置多种策略组合与评分逻辑
- 推荐结果会保存到数据库，供后续命中校验和看板展示使用

### 5. 命中核对

- 在开奖后自动同步最新开奖
- 将推荐号码与最新开奖号码比对
- 统计红球命中数、蓝球是否命中、奖级、中奖金额
- 支持策略维度的命中率统计

### 6. Web 后台

- 首页展示最近开奖、最近推荐、最近核对、最近任务
- 展示分析增强指标、策略回测表现、推荐评分卡
- 支持命中回报趋势图
- 支持按期号范围筛选看板数据
- 最近推荐评分卡、推荐明细按期号降序和评分降序展示

### 7. 定时任务

已按双色球开奖节奏配置调度：

- 每周二、周四、周日 `20:00`
  - 同步最近 100 期开奖数据
  - 生成分析快照
  - 生成推荐号码
  - 将推荐信息写入调度日志
- 每周二、周四、周日 `21:30`
  - 同步最新开奖结果
  - 核对推荐号码
  - 统计命中率与奖级结果
  - 将校验结果写入调度日志

调度日志默认保存到：

`logs/scheduled_jobs.log`

## 数据增长逻辑

这是项目里最重要的一条规则：

- 官网接口每次只取最近 `100` 期
- 本地数据库不会只保留 `100` 期
- 每次同步时，程序会把抓到的 100 期逐条和数据库比对
- 已存在的期号跳过
- 新出现的期号才插入数据库

例如：

- 第一次同步，抓到最近 `100` 期，其中数据库为空，则入库 `100` 条
- 一周后再次同步，官网最近 `100` 期里只有 `3` 条是新开奖，则只新增 `3` 条
- 这时数据库里总数就是 `103` 条

也就是说：

- “采集窗口”固定是最近 `100` 期
- “数据库总量”是持续增长的历史全量积累

分析快照和推荐逻辑使用的是数据库里的历史数据，因此随着时间增长，样本会越来越多。

## 数据保留策略

不同数据的保留规则不同：

- `draw_results` 开奖数据：长期累积，不主动裁剪
- `analysis_snapshots` 分析快照：按业务正常保存
- `recommendations` 推荐记录：仅保留最近 `1000` 条
- `job_runs` 任务记录：仅保留最近 `100` 条
- Web 前端最近任务：只显示最近 `10` 条

这样做的目的：

- 开奖历史和分析基础数据尽量完整
- 推荐和任务日志避免无限增长

## 技术栈

- Python 3
- Flask
- SQLite
- APScheduler
- Docker / Docker Compose
- Pytest

## 项目结构

```text
SSQ/
├─ app/
│  ├─ analyzer/        # 统计分析、特征提取、回测
│  ├─ checker/         # 开奖核对、奖级规则
│  ├─ collector/       # 官网数据采集与解析
│  ├─ models/          # DTO、实体、枚举
│  ├─ notifier/        # 推送抽象与格式化
│  ├─ recommender/     # 推荐号码生成
│  ├─ repository/      # SQLite 仓储层
│  ├─ strategy/        # 推荐策略实现
│  ├─ utils/           # 日期、校验、随机工具
│  ├─ bootstrap.py     # 服务装配与任务编排
│  ├─ config.py        # 配置加载
│  ├─ job_logger.py    # 定时任务日志
│  ├─ main.py          # CLI 入口
│  ├─ scheduler.py     # APScheduler 调度
│  └─ web.py           # Flask Web 后台
├─ data/
│  ├─ sample_draws.json
│  └─ ssq_app.db
├─ docs/
├─ logs/
├─ tests/
├─ config.json
├─ config.json.example
├─ docker-compose.yml
├─ Dockerfile
├─ run_web.py
└─ README.md
```

## 配置说明

示例配置文件：

[config.json.example](./config.json.example)

当前主要配置项：

```json
{
  "database": {
    "path": "data/ssq_app.db"
  },
  "crawler": {
    "source_type": "cwl_api",
    "source_name": "cwl_official",
    "source_url": "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice",
    "timeout_seconds": 20,
    "issue_count": 100
  },
  "analysis": {
    "rolling_window": 30
  },
  "recommendation": {
    "daily_count": 5
  },
  "notifier": {
    "enabled": false,
    "default_channel": "console"
  }
}
```

关键含义：

- `database.path`：SQLite 数据库文件路径
- `crawler.issue_count`：每次从官网抓取的期数，当前为 `100`
- `analysis.rolling_window`：滚动分析窗口默认值
- `recommendation.daily_count`：每次生成推荐组数
- `notifier.enabled`：是否启用推送，当前默认关闭

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python -m app init-db
```

### 3. 同步最近 100 期历史数据

```bash
python -m app sync-history --start 2000-01-01 --end 2099-12-31
```

说明：

- 命令支持传入起止日期
- 但当前官网采集器实际每次只会抓最近 `100` 期
- 程序会自动做增量入库

### 4. 生成分析快照

```bash
python -m app analyze
```

如果只想按固定窗口分析：

```bash
python -m app analyze --window 30
```

### 5. 生成推荐号码

```bash
python -m app recommend --count 5
```

### 6. 同步最新开奖

```bash
python -m app sync-latest
```

### 7. 核对某一期推荐结果

```bash
python -m app check --issue 2026050
```

### 8. 启动调度器

```bash
python -m app run-scheduler
```

### 9. 启动 Web 后台

```bash
python run_web.py
```

默认访问：

`http://localhost:8000`

## Docker 部署

### 1. 构建并启动

```bash
docker compose build
docker compose up -d
```

### 2. 初始化数据库

```bash
docker compose run --rm ssq python -m app init-db
```

### 3. 手动执行一次历史同步

```bash
docker compose run --rm ssq python -m app sync-history --start 2000-01-01 --end 2099-12-31
```

### 4. 执行分析与推荐

```bash
docker compose run --rm ssq python -m app analyze
docker compose run --rm ssq python -m app recommend --count 5
```

### 5. 运行测试

```bash
docker compose run --rm ssq pytest -q tests
```

### 6. 访问后台

默认端口映射：

`http://localhost:8000`

如果宿主机 `8000` 被占用，可以在启动前指定：

```bash
set SSQ_WEB_PORT=8001
docker compose up -d
```

然后访问：

`http://localhost:8001`

## Docker 持久化说明

`docker-compose.yml` 中做了两层持久化处理：

- 命名卷：`ssq_data:/app/data`
- 日志目录挂载：`./logs:/app/logs`

同时项目源码也挂载到容器内：

- `./:/app`

因此：

- 容器重启后数据库文件不会丢失
- 日志文件不会丢失
- 本地改代码后容器内可以直接使用最新代码

主数据库文件位于容器内：

`/app/data/ssq_app.db`

## Web 后台说明

后台首页主要包含：

- 概览指标
- 最近开奖
- 最近推荐明细
- 最近推荐评分卡
- 推荐策略得分分布
- 分析增强指标
- 策略回测
- 命中回报看板
- 按期号筛选趋势图
- 最近任务记录

支持的手动按钮：

- 同步最近 100 期数据
- 生成分析快照
- 生成推荐号码
- 同步最新开奖

## API 概览

当前提供的主要接口：

- `GET /api/draws/latest`
  - 获取最新一期开奖
- `GET /api/draws?limit=30`
  - 获取最近开奖列表
- `GET /api/dashboard/summary`
  - 获取首页摘要数据，可带期号筛选
- `GET /api/analysis/latest`
  - 获取最新分析快照
- `GET /api/recommendations?limit=20`
  - 获取最近推荐列表
- `POST /api/tasks/sync-history`
  - 手动触发历史同步
- `POST /api/tasks/sync-latest`
  - 手动触发最新开奖同步
- `POST /api/tasks/analyze`
  - 手动触发分析快照生成
- `POST /api/tasks/recommend`
  - 手动触发推荐号码生成
- `POST /api/tasks/check`
  - 手动触发开奖核对

## 测试

项目已包含基础自动化测试，覆盖部分核心逻辑：

- 推荐引擎
- 调度任务
- 首页摘要
- 校验规则
- 数据校验逻辑

运行方式：

```bash
pytest -q tests
```

## 文档

详细业务和开发说明见：

- [双色球数据分析与智能推送系统开发文档](./docs/双色球数据分析与智能推送系统开发文档.md)
- [双色球数据分析与智能推送系统接口设计与任务拆解](./docs/双色球数据分析与智能推送系统接口设计与任务拆解.md)

## 注意事项

- 当前推荐逻辑属于可持续优化版本，重点是先打通“采集 -> 分析 -> 推荐 -> 校验 -> 统计”的完整闭环
- 推送渠道代码已预留，但当前默认关闭，不作为现阶段主功能
- 数据越积累越多，分析快照的样本越丰富，后续可以继续优化推荐评分模型
- 如果你希望完全清空业务数据，可以直接清空 SQLite 对应表，或替换数据库文件

## 后续优化方向

- 优化推荐评分因子与权重
- 增加更多策略组合和策略回归分析
- 增强奖级统计、收益统计、命中趋势可视化
- 增加后台筛选维度和导出能力
- 增加推送渠道接入能力

