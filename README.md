# 双色球数据分析与智能推送系统

## 当前策略

- 采集端每次只从中国福利彩票官网接口获取最近 `100` 期双色球数据。
- 数据库按 `issue_no` 做唯一约束，重复同步时只会增量补入新期号。
- 分析快照默认基于数据库中的全部历史数据计算。
- 推荐号码始终基于最新一条分析快照生成。

官网接口：

`https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice`

参考实现：

[爬取双色球.py](D:\Workspace\code\claude\SSQ\爬取双色球.py)

## 本地运行

```bash
python -m app init-db
python -m app sync-history --start 2000-01-01 --end 2099-12-31
python -m app analyze
python -m app recommend --count 5
```

说明：

- `sync-history` 每次实际只抓官网最近 100 期，但会按期号增量写入数据库。
- `analyze` 不传 `--window` 时，会基于数据库全部数据生成快照。
- 如果显式传入 `--window 30`，则只按最近 30 期生成快照。

## Docker 运行

```bash
docker compose build
docker compose up -d
docker compose run --rm ssq python -m app init-db
docker compose run --rm ssq python -m app sync-history --start 2000-01-01 --end 2099-12-31
docker compose run --rm ssq python -m app analyze
docker compose run --rm ssq pytest -q tests
```

启动后访问：

`http://localhost:8000`

## 持久化

- 数据库文件路径是容器内的 `/app/data/ssq_app.db`
- `docker-compose.yml` 使用 Docker 命名卷 `ssq_data`
- 因此容器重启、重建后，数据库中的历史开奖数据不会丢失

## 当前已验证

- 最近 100 期真实数据采集
- 按期号增量入库
- 分析快照默认按数据库全部数据生成
- 推荐号码生成
- Docker 持久化
- Web 后台访问与接口返回
