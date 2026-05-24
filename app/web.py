from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template_string, request

from app.bootstrap import build_container, run_job
from app.models.dto import AnalysisSnapshotDTO, DrawResultDTO, RecommendationDTO
from app.scheduler import SchedulerService
from app.utils.validators import format_red_numbers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


HTML_TEMPLATE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>双色球数据后台</title>
  <style>
    :root { --bg:#efe8db; --panel:#fff9f0; --line:#dbcdb7; --text:#1f1c17; --muted:#6e665a; --accent:#a73329; --blue:#195c9f; --gold:#bc8b2d; --green:#4a7d44; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI","PingFang SC",sans-serif; background:radial-gradient(circle at top,#f8f0e0 0%,#efe7d8 44%,#ece5da 100%); color:var(--text); }
    .wrap { max-width:1320px; margin:0 auto; padding:24px; }
    .hero { display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:24px; }
    h1 { margin:0; font-size:38px; letter-spacing:.02em; }
    .sub { color:var(--muted); margin-top:8px; max-width:760px; }
    .actions { display:flex; gap:12px; flex-wrap:wrap; }
    button { border:0; padding:12px 16px; border-radius:12px; background:var(--text); color:#fff; cursor:pointer; font-weight:600; }
    button.secondary { background:var(--blue); }
    button.gold { background:var(--gold); }
    .grid { display:grid; grid-template-columns:repeat(12,1fr); gap:16px; }
    .card { grid-column:span 12; background:var(--panel); border:1px solid var(--line); border-radius:20px; padding:18px; box-shadow:0 10px 30px rgba(40,33,22,.06); }
    .half { grid-column:span 6; }
    .third { grid-column:span 4; }
    .wide { grid-column:span 8; }
    .narrow { grid-column:span 4; }
    .card h2 { margin:0 0 14px 0; font-size:20px; }
    .meta { color:var(--muted); font-size:14px; }
    .kpi { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
    .kpi .item { padding:14px; border-radius:14px; background:#f8f1e4; border:1px solid #eadfc9; }
    .kpi .value { font-size:24px; font-weight:700; }
    table { width:100%; border-collapse:collapse; font-size:14px; }
    th, td { text-align:left; padding:10px 8px; border-bottom:1px solid #ece3d3; vertical-align:top; }
    th { color:var(--muted); font-weight:600; }
    .balls { display:flex; gap:6px; flex-wrap:wrap; }
    .ball { width:28px; height:28px; line-height:28px; text-align:center; border-radius:999px; color:#fff; font-size:13px; font-weight:700; }
    .red { background:var(--accent); }
    .blue { background:var(--blue); }
    .badge { display:inline-block; padding:4px 8px; border-radius:999px; background:#efe4d0; color:#5f5546; font-size:12px; }
    .badge.score { background:#efe0c0; color:#7c5311; }
    .metric-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
    .metric { padding:12px; border-radius:14px; background:#faf3e6; border:1px solid #eadfc9; }
    .metric .label { color:var(--muted); font-size:13px; }
    .metric .value { margin-top:6px; font-size:20px; font-weight:700; }
    .score-cards { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }
    .score-card { padding:14px; border-radius:16px; border:1px solid #e6d8c1; background:#fffdf7; }
    .score-head { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:10px; }
    .tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
    .tag { font-size:12px; padding:4px 8px; border-radius:999px; background:#f1e5d2; color:#6f5f46; }
    .list-line { display:flex; justify-content:space-between; gap:12px; padding:10px 0; border-bottom:1px solid #ece3d3; }
    .list-line:last-child { border-bottom:0; padding-bottom:0; }
    pre { white-space:pre-wrap; word-break:break-word; margin:0; font-size:13px; color:#3a342b; }
    .mono { font-family:Consolas,monospace; font-size:13px; }
    .filter-bar { display:flex; flex-wrap:wrap; gap:12px; align-items:end; }
    .field { display:flex; flex-direction:column; gap:6px; min-width:160px; }
    .field label { color:var(--muted); font-size:13px; }
    .field input { padding:10px 12px; border-radius:12px; border:1px solid var(--line); background:#fffdf8; }
    .svg-wrap { margin-top:12px; border:1px solid #e7dcc8; border-radius:14px; padding:12px; background:#fffdf8; }
    .legend { display:flex; gap:14px; flex-wrap:wrap; margin-top:10px; font-size:12px; color:var(--muted); }
    .dot { display:inline-block; width:10px; height:10px; border-radius:999px; margin-right:6px; }
    .dot.red { background:var(--accent); }
    .dot.blue { background:var(--blue); }
    .dot.green { background:var(--green); }
    @media (max-width: 980px) {
      .half,.third,.wide,.narrow { grid-column:span 12; }
      .hero { flex-direction:column; align-items:flex-start; }
      .kpi { grid-template-columns:1fr 1fr; }
      .score-cards,.metric-grid { grid-template-columns:1fr; }
    }
    @media (max-width: 640px) {
      .kpi { grid-template-columns:1fr; }
      .filter-bar { flex-direction:column; align-items:stretch; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>双色球数据后台</h1>
        <div class="sub">100期真实数据增量采集、全库分析快照、推荐评分、策略回测和命中回报都在这里直接查看。</div>
      </div>
      <div class="actions">
        <button onclick="runTask('sync-history')">同步最近100期数据</button>
        <button class="secondary" onclick="runTask('analyze')">生成分析快照</button>
        <button class="gold" onclick="runTask('recommend')">生成推荐号码</button>
        <button class="secondary" onclick="runTask('sync-latest')">同步最新开奖</button>
      </div>
    </div>

    <div class="card">
      <h2>概览</h2>
      <div class="kpi">
        <div class="item"><div class="meta">最新开奖期号</div><div class="value">{{ latest_issue }}</div></div>
        <div class="item"><div class="meta">最新快照期号</div><div class="value">{{ snapshot_issue }}</div></div>
        <div class="item"><div class="meta">当前总期数</div><div class="value">{{ draw_count }}</div></div>
        <div class="item"><div class="meta">最近同步时间</div><div class="value" style="font-size:16px;">{{ latest_sync_time }}</div></div>
        <div class="item"><div class="meta">近30条推荐平均分</div><div class="value">{{ recommendation_stats.avg_score }}</div></div>
        <div class="item"><div class="meta">近30条推荐最高分</div><div class="value">{{ recommendation_stats.top_score }}</div></div>
        <div class="item"><div class="meta">核对命中率</div><div class="value">{{ check_stats.hit_rate }}</div></div>
        <div class="item"><div class="meta">蓝球命中率</div><div class="value">{{ check_stats.blue_hit_rate }}</div></div>
      </div>
      <div class="meta" style="margin-top:14px;">数据源：{{ data_source_name }} ｜ 来源地址：{{ data_source_url }}</div>
    </div>

    <div class="grid">
      <div class="card wide">
        <h2>分析增强指标</h2>
        <div class="metric-grid">
          <div class="metric"><div class="label">快照窗口</div><div class="value">{{ snapshot_window }}</div></div>
          <div class="metric"><div class="label">跨度均值</div><div class="value">{{ feature_stats.span_avg }}</div></div>
          <div class="metric"><div class="label">AC均值</div><div class="value">{{ feature_stats.ac_avg }}</div></div>
          <div class="metric"><div class="label">和值均值</div><div class="value">{{ feature_stats.sum_avg }}</div></div>
          <div class="metric"><div class="label">重号模式</div><div class="value">{{ feature_stats.repeat_mode }}</div></div>
          <div class="metric"><div class="label">尾号多样模式</div><div class="value">{{ feature_stats.tail_variety_mode }}</div></div>
          <div class="metric"><div class="label">热号</div><div class="value mono">{{ hot_numbers }}</div></div>
          <div class="metric"><div class="label">冷号</div><div class="value mono">{{ cold_numbers }}</div></div>
        </div>
      </div>

      <div class="card narrow">
        <h2>策略回测</h2>
        {% for row in strategy_metrics %}
        <div class="list-line">
          <div>
            <div><span class="badge">{{ row.strategy_name }}</span></div>
            <div class="meta">样本 {{ row.samples }} ｜ 平均红球 {{ row.avg_red_hits }}</div>
          </div>
          <div style="text-align:right;">
            <div class="badge score">评分 {{ row.recent_score }}</div>
            <div class="meta">蓝球 {{ row.blue_hit_rate }} ｜ 奖级 {{ row.prize_hit_rate }}</div>
          </div>
        </div>
        {% endfor %}
      </div>

      <div class="card half">
        <h2>最近推荐评分卡</h2>
        <div class="score-cards">
          {% for card in recommendation_stats.recent_score_cards %}
          <div class="score-card">
            <div class="score-head">
              <div>
                <div><span class="badge">{{ card.strategy_name }}</span></div>
                <div class="meta">目标期号 {{ card.issue_no or "-" }}</div>
              </div>
              <div style="text-align:right;">
                <div class="badge score">总分 {{ card.score }}</div>
                <div class="meta">对齐分 {{ card.alignment_score }}</div>
              </div>
            </div>
            <div class="balls">
              {% for num in card.numbers.reds %}<span class="ball red">{{ "%02d"|format(num) }}</span>{% endfor %}
              <span class="ball blue">{{ "%02d"|format(card.numbers.blue) }}</span>
            </div>
            <div class="tags">
              {% for tag in card.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
            </div>
          </div>
          {% endfor %}
        </div>
      </div>

      <div class="card half">
        <h2>推荐策略得分分布</h2>
        {% for row in recommendation_stats.strategy_breakdown %}
        <div class="list-line">
          <div>
            <div><span class="badge">{{ row.strategy_name }}</span></div>
            <div class="meta">推荐数 {{ row.count }}</div>
          </div>
          <div style="text-align:right;">
            <div class="meta">均分 {{ row.avg_score }}</div>
            <div class="meta">最高 {{ row.top_score }}</div>
          </div>
        </div>
        {% endfor %}
      </div>

      <div class="card half">
        <h2>命中回报看板</h2>
        <form method="get" class="filter-bar">
          <div class="field">
            <label for="issue_from">起始期号</label>
            <input id="issue_from" name="issue_from" value="{{ issue_filter.issue_from }}" placeholder="例如 2026001">
          </div>
          <div class="field">
            <label for="issue_to">结束期号</label>
            <input id="issue_to" name="issue_to" value="{{ issue_filter.issue_to }}" placeholder="例如 2026057">
          </div>
          <button type="submit">筛选</button>
        </form>
        <div class="meta" style="margin-top:12px;">当前筛选：{{ filter_label }}</div>
        <div class="metric-grid" style="margin-top:12px;">
          <div class="metric"><div class="label">已核对推荐数</div><div class="value">{{ check_stats.checked_count }}</div></div>
          <div class="metric"><div class="label">平均红球命中</div><div class="value">{{ check_stats.avg_red_hits }}</div></div>
          <div class="metric"><div class="label">命中率</div><div class="value">{{ check_stats.hit_rate }}</div></div>
          <div class="metric"><div class="label">蓝球命中率</div><div class="value">{{ check_stats.blue_hit_rate }}</div></div>
        </div>
        <div class="svg-wrap">
          {{ trend_svg|safe }}
          <div class="legend">
            <span><i class="dot red"></i>平均红球命中</span>
            <span><i class="dot blue"></i>蓝球命中率</span>
            <span><i class="dot green"></i>整体命中率</span>
          </div>
        </div>
      </div>

      <div class="card half">
        <h2>分策略命中表现</h2>
        {% for row in check_stats.strategy_hit_board %}
        <div class="list-line">
          <div>
            <div><span class="badge">{{ row.strategy_name }}</span></div>
            <div class="meta">核对数 {{ row.checked_count }}</div>
          </div>
          <div style="text-align:right;">
            <div class="meta">命中率 {{ row.hit_rate }}</div>
            <div class="meta">均红 {{ row.avg_red_hits }} ｜ 蓝球 {{ row.blue_hit_rate }}</div>
          </div>
        </div>
        {% endfor %}
      </div>

      <div class="card half">
        <h2>最近开奖</h2>
        <table>
          <thead><tr><th>期号</th><th>日期</th><th>号码</th></tr></thead>
          <tbody>
            {% for draw in recent_draws %}
            <tr>
              <td>{{ draw.issue_no }}</td>
              <td>{{ draw.draw_date }}</td>
              <td>
                <div class="balls">
                  {% for num in draw.red_numbers %}<span class="ball red">{{ "%02d"|format(num) }}</span>{% endfor %}
                  <span class="ball blue">{{ "%02d"|format(draw.blue_number) }}</span>
                </div>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <div class="card half">
        <h2>最近推荐明细</h2>
        <table>
          <thead><tr><th>目标期号</th><th>策略</th><th>评分</th><th>号码</th></tr></thead>
          <tbody>
            {% for item in recent_recommendations %}
            <tr>
              <td>{{ item.target_issue_no or "-" }}</td>
              <td><span class="badge">{{ item.strategy_name }}</span></td>
              <td>{{ item.feature_summary.get("score", "-") }}</td>
              <td>
                <div class="balls">
                  {% for num in item.red_numbers %}<span class="ball red">{{ "%02d"|format(num) }}</span>{% endfor %}
                  <span class="ball blue">{{ "%02d"|format(item.blue_number) }}</span>
                </div>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <div class="card third">
        <h2>最近核对</h2>
        <table>
          <thead><tr><th>期号</th><th>命中</th><th>奖级</th></tr></thead>
          <tbody>
            {% for row in recent_checks %}
            <tr>
              <td>{{ row.issue_no }}</td>
              <td>{{ row.red_hits }}红 + {{ row.blue_hit }}蓝</td>
              <td>{{ row.prize_level or "未中奖" }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <div class="card third">
        <h2>最近任务</h2>
        <table>
          <thead><tr><th>任务</th><th>状态</th></tr></thead>
          <tbody>
            {% for job in recent_jobs %}
            <tr>
              <td>{{ job.job_name }}</td>
              <td>{{ job.status }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>

      <div class="card third">
        <h2>多窗口频率观察</h2>
        <div class="meta">近30期红球Top</div>
        <pre>{{ recent_30_hot }}</pre>
        <div class="meta" style="margin-top:12px;">全库红球Top</div>
        <pre>{{ full_hot }}</pre>
        <div class="meta" style="margin-top:12px;">近30期蓝球Top</div>
        <pre>{{ recent_30_blue }}</pre>
      </div>
    </div>
  </div>

  <script>
    async function runTask(name) {
      const resp = await fetch('/api/tasks/' + name, { method: 'POST' });
      const data = await resp.json();
      alert(JSON.stringify(data, null, 2));
      location.reload();
    }
  </script>
</body>
</html>
"""


def create_app(config_path: str = "config.json") -> Flask:
    app = Flask(__name__)
    container = build_container(config_path)
    container.init_db()
    scheduler = SchedulerService(container)
    scheduler.start()
    app.extensions["scheduler_service"] = scheduler

    @app.get("/")
    def index():
        issue_from = request.args.get("issue_from") or None
        issue_to = request.args.get("issue_to") or None
        data = container.get_dashboard_data(issue_from, issue_to)
        snapshot: AnalysisSnapshotDTO | None = data["latest_snapshot"]
        latest_draw: DrawResultDTO | None = data["latest_draw"]
        feature_stats = snapshot.feature_stats if snapshot else {}
        strategy_metrics = _strategy_metrics_to_list(snapshot)
        check_stats = data["check_stats"]
        return render_template_string(
            HTML_TEMPLATE,
            latest_issue=latest_draw.issue_no if latest_draw else "-",
            snapshot_issue=snapshot.based_on_issue if snapshot else "-",
            snapshot_window=snapshot.window_size if snapshot else "-",
            recent_draws=data["recent_draws"],
            recent_recommendations=data["recent_recommendations"],
            recent_checks=data["recent_checks"],
            recent_jobs=data["recent_jobs"],
            draw_count=data["draw_count"],
            latest_sync_time=(data["latest_sync_job"]["run_at"] if data["latest_sync_job"] else "-"),
            data_source_name=data["data_source_name"],
            data_source_url=data["data_source_url"],
            hot_numbers=", ".join(f"{item:02d}" for item in (snapshot.hot_numbers if snapshot else [])),
            cold_numbers=", ".join(f"{item:02d}" for item in (snapshot.cold_numbers if snapshot else [])),
            feature_stats=feature_stats,
            strategy_metrics=strategy_metrics,
            recommendation_stats=data["recommendation_stats"],
            check_stats=check_stats,
            issue_filter=data["issue_filter"],
            filter_label=_filter_label(issue_from, issue_to),
            recent_30_hot=_top_frequency_text(snapshot.layered_red_frequency.get("recent_30", {}) if snapshot else {}, 8),
            full_hot=_top_frequency_text(snapshot.layered_red_frequency.get("full", {}) if snapshot else {}, 8),
            recent_30_blue=_top_frequency_text(snapshot.layered_blue_frequency.get("recent_30", {}) if snapshot else {}, 6),
            trend_svg=_build_trend_svg(check_stats.get("issue_trend", [])),
        )

    @app.get("/api/draws/latest")
    def api_latest_draw():
        draw = container.draw_repository.get_latest()
        if not draw:
            return jsonify({"status": "error", "message": "no draw data"}), 404
        return jsonify(_draw_to_dict(draw))

    @app.get("/api/draws")
    def api_draws():
        limit = int(request.args.get("limit", 30))
        draws = container.draw_repository.list_recent(limit)
        return jsonify([_draw_to_dict(draw) for draw in draws])

    @app.get("/api/dashboard/summary")
    def api_dashboard_summary():
        issue_from = request.args.get("issue_from") or None
        issue_to = request.args.get("issue_to") or None
        data = container.get_dashboard_data(issue_from, issue_to)
        snapshot = data["latest_snapshot"]
        return jsonify(
            {
                "issue_filter": data["issue_filter"],
                "recommendation_stats": data["recommendation_stats"],
                "check_stats": data["check_stats"],
                "strategy_metrics": snapshot.strategy_metrics if snapshot else {},
                "feature_stats": snapshot.feature_stats if snapshot else {},
            }
        )

    @app.get("/api/analysis/latest")
    def api_latest_analysis():
        snapshot = container.analysis_repository.get_latest_snapshot()
        if not snapshot:
            return jsonify({"status": "error", "message": "no analysis data"}), 404
        return jsonify(
            {
                "based_on_issue": snapshot.based_on_issue,
                "snapshot_date": snapshot.snapshot_date,
                "window_size": snapshot.window_size,
                "hot_numbers": snapshot.hot_numbers,
                "cold_numbers": snapshot.cold_numbers,
                "weighted_red_frequency": snapshot.weighted_red_frequency,
                "weighted_blue_frequency": snapshot.weighted_blue_frequency,
                "layered_red_frequency": snapshot.layered_red_frequency,
                "layered_blue_frequency": snapshot.layered_blue_frequency,
                "pattern_stats": snapshot.pattern_stats,
                "feature_stats": snapshot.feature_stats,
                "strategy_metrics": snapshot.strategy_metrics,
            }
        )

    @app.get("/api/recommendations")
    def api_recommendations():
        limit = int(request.args.get("limit", 20))
        items = container.recommendation_repository.list_recent(limit)
        return jsonify([_recommendation_to_dict(item) for item in items])

    @app.post("/api/tasks/sync-history")
    def api_sync_history():
        payload = request.get_json(silent=True) or {}
        start_date = payload.get("start", "2000-01-01")
        end_date = payload.get("end", "2099-12-31")
        result = run_job(container.job_repository, "sync_history", lambda: container.sync_history(start_date, end_date))
        return jsonify({"status": "success", "inserted": result, "start": start_date, "end": end_date})

    @app.post("/api/tasks/sync-latest")
    def api_sync_latest():
        inserted = run_job(container.job_repository, "sync_latest", container.sync_latest)
        latest = container.draw_repository.get_latest()
        check_items = []
        if latest:
            check_items = run_job(container.job_repository, "check", lambda: container.check_service.check_issue(latest.issue_no))
        return jsonify({"status": "success", "inserted": inserted, "checked": len(check_items)})

    @app.post("/api/tasks/analyze")
    def api_analyze():
        payload = request.get_json(silent=True) or {}
        window = payload.get("window")
        snapshot = run_job(container.job_repository, "analyze", lambda: container.analysis_service.build_snapshot(window))
        return jsonify({"status": "success", "snapshot_id": snapshot.snapshot_id, "based_on_issue": snapshot.based_on_issue})

    @app.post("/api/tasks/recommend")
    def api_recommend():
        fixed_count = int(container.config["recommendation"]["daily_count"])
        items = run_job(container.job_repository, "recommend", lambda: container.recommendation_service.generate_daily(fixed_count))
        return jsonify({"status": "success", "count": len(items), "items": [_recommendation_to_dict(item) for item in items]})

    @app.post("/api/tasks/check")
    def api_check():
        payload = request.get_json(silent=True) or {}
        issue_no = payload.get("issue")
        if not issue_no:
            latest = container.draw_repository.get_latest()
            if not latest:
                return jsonify({"status": "error", "message": "no draw data"}), 400
            issue_no = latest.issue_no
        items = run_job(container.job_repository, "check", lambda: container.check_service.check_issue(issue_no))
        return jsonify({"status": "success", "count": len(items), "items": [item.__dict__ for item in items]})

    return app


def _draw_to_dict(draw: DrawResultDTO) -> dict:
    return {
        "issue_no": draw.issue_no,
        "draw_date": draw.draw_date,
        "red_numbers": draw.red_numbers,
        "blue_number": draw.blue_number,
        "red_numbers_text": format_red_numbers(draw.red_numbers),
    }


def _recommendation_to_dict(item: RecommendationDTO) -> dict:
    return {
        "id": item.recommendation_id,
        "batch_no": item.batch_no,
        "recommend_date": item.recommend_date,
        "target_issue_no": item.target_issue_no,
        "strategy_name": item.strategy_name,
        "red_numbers": item.red_numbers,
        "blue_number": item.blue_number,
        "feature_summary": item.feature_summary,
    }


def _strategy_metrics_to_list(snapshot: AnalysisSnapshotDTO | None) -> list[dict]:
    if not snapshot or not snapshot.strategy_metrics:
        return []
    items = [{"strategy_name": strategy_name, **payload} for strategy_name, payload in snapshot.strategy_metrics.items()]
    items.sort(key=lambda row: float(row.get("recent_score", 0)), reverse=True)
    return items


def _top_frequency_text(values: dict[int, float], limit: int) -> str:
    if not values:
        return "-"
    ranked = sorted(values.items(), key=lambda item: (item[1], item[0]), reverse=True)[:limit]
    return ", ".join(f"{int(number):02d}({score:.3f})" for number, score in ranked)


def _filter_label(issue_from: str | None, issue_to: str | None) -> str:
    if issue_from and issue_to:
        return f"{issue_from} - {issue_to}"
    if issue_from:
        return f"从 {issue_from} 开始"
    if issue_to:
        return f"截至 {issue_to}"
    return "全部期号"


def _build_trend_svg(points: list[dict]) -> str:
    if not points:
        return '<div class="meta">当前筛选范围内还没有核对数据，趋势图将在有命中记录后自动显示。</div>'

    width = 640
    height = 220
    padding_left = 44
    padding_right = 18
    padding_top = 16
    padding_bottom = 36
    plot_width = width - padding_left - padding_right
    plot_height = height - padding_top - padding_bottom
    count = len(points)

    def x_pos(index: int) -> float:
        if count == 1:
            return padding_left + plot_width / 2
        return padding_left + (plot_width * index / (count - 1))

    def y_pos(value: float, max_value: float) -> float:
        normalized = 0 if max_value <= 0 else min(max(value / max_value, 0), 1)
        return padding_top + plot_height - normalized * plot_height

    max_red_hits = max(max(float(item.get("avg_red_hits", 0)), 1.0) for item in points)
    max_rate = 1.0

    red_path = []
    blue_path = []
    hit_path = []
    labels = []
    for index, item in enumerate(points):
        x = x_pos(index)
        red_y = y_pos(float(item.get("avg_red_hits", 0)), max_red_hits)
        blue_y = y_pos(float(item.get("blue_hit_rate", 0)), max_rate)
        hit_y = y_pos(float(item.get("hit_rate", 0)), max_rate)
        red_path.append(f"{'M' if index == 0 else 'L'} {x:.2f} {red_y:.2f}")
        blue_path.append(f"{'M' if index == 0 else 'L'} {x:.2f} {blue_y:.2f}")
        hit_path.append(f"{'M' if index == 0 else 'L'} {x:.2f} {hit_y:.2f}")
        labels.append(
            f'<text x="{x:.2f}" y="{height - 12}" font-size="11" text-anchor="middle" fill="#6e665a">{item["issue_no"][-3:]}</text>'
        )

    grid = []
    for tick in range(5):
        y = padding_top + plot_height * tick / 4
        grid.append(f'<line x1="{padding_left}" y1="{y:.2f}" x2="{width - padding_right}" y2="{y:.2f}" stroke="#eadfc9" stroke-width="1"/>')

    return f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="220" role="img" aria-label="命中趋势图">
      <rect x="0" y="0" width="{width}" height="{height}" rx="12" fill="#fffdf8"/>
      {''.join(grid)}
      <line x1="{padding_left}" y1="{padding_top + plot_height:.2f}" x2="{width - padding_right}" y2="{padding_top + plot_height:.2f}" stroke="#cdbda5" stroke-width="1.2"/>
      <path d="{' '.join(red_path)}" fill="none" stroke="#a73329" stroke-width="3" stroke-linecap="round"/>
      <path d="{' '.join(blue_path)}" fill="none" stroke="#195c9f" stroke-width="3" stroke-linecap="round"/>
      <path d="{' '.join(hit_path)}" fill="none" stroke="#4a7d44" stroke-width="3" stroke-linecap="round"/>
      {''.join(labels)}
    </svg>
    """
