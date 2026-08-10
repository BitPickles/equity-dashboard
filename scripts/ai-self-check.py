#!/usr/bin/env python3
"""
ai-self-check.py — AI 自检哨兵（PRD v2.1 第 5.5.3 节）

无人值守 AI 审计：GLM API 每日自检协议口径与数据质量。

5 套审计任务（模板见 scripts/prompts/audit-templates.json）:
  ① mechanism-change   机制变更检测（读官方公告抓取缓存 vs config 口径判定书）
  ② data-plausibility  数据合理性（时间序列突变/负值/Null 异常）
  ③ cross-validation   交叉验证（链上 vs DefiLlama 差异）
  ④ freshness          新鲜度（纯脚本，>26h 告警，不消耗 GLM）
  ⑤ regression         口径回归（新协议接入后既有协议数值不变）

告警分级:
  alert  → Telegram 通知 Boss（未配置 TG 时输出到 stderr）
  review → 日志 + 日报
  ok     → 静默

审计痕迹: 每次自检结果落 data/ai-audit/<date>.json

用法:
  python3 scripts/ai-self-check.py                # 跑全部任务
  python3 scripts/ai-self-check.py --task freshness  # 只跑新鲜度
  python3 scripts/ai-self-check.py --no-llm       # 跳过 LLM 任务（无 GLM key 时）
  python3 scripts/ai-self-check.py --date 2026-08-02  # 指定审计日期（重跑）
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "ai-sentinel.json"
TEMPLATES_FILE = BASE_DIR / "scripts" / "prompts" / "audit-templates.json"
SNAPSHOTS_DIR = BASE_DIR / "data" / "snapshots"
AUDIT_DIR = BASE_DIR / "data" / "ai-audit"
ALL_PROTOCOLS_FILE = BASE_DIR / "data" / "all-protocols.json"

FRESHNESS_HOURS = 26


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ── GLM API 封装（OpenAI 兼容） ──────────────────────────────────────

def _load_dotenv():
    """从仓库根 .env 读取密钥（Mac Mini 部署：放置 .env 即可）。
    .env 已被 .gitignore 忽略，严禁提交到 GitHub。"""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


class GLMClient:
    def __init__(self, config):
        self.config = config
        _load_dotenv()
        self.api_key = os.environ.get(config.get("api_key_env", "GLM_API_KEY"))
        self.available = bool(self.api_key)

    def chat(self, system, user, timeout=None, retries=None):
        """调用 GLM。返回解析后的 JSON dict；失败抛异常。"""
        if not self.available:
            raise RuntimeError(f"缺少环境变量 {self.config['api_key_env']}，无法调用 GLM")
        timeout = timeout or self.config.get("timeout_sec", 60)
        retries = retries if retries is not None else self.config.get("max_retries", 2)

        payload = {
            "model": self.config["model"],
            "temperature": self.config.get("temperature", 0),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.config["endpoint"], data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        last_err = None
        for attempt in range(retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                return self._parse_json(content)
            except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < retries:
                    continue
        raise RuntimeError(f"GLM 调用失败: {last_err}")

    @staticmethod
    def _parse_json(content):
        """GLM 输出可能带 ```json 围栏，容错提取。"""
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        # 提取第一个 { ... } 块（防止多余文字）
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start:end + 1]
        return json.loads(content)


# ── 各任务实现 ───────────────────────────────────────────────────────

def build_context_for(proto):
    """组装某协议的自检上下文（config 判定书 + snapshot + 官方缓存）。"""
    config = load_json(BASE_DIR / "data" / "protocols" / proto / "config.json") or {}
    snapshot = load_json(SNAPSHOTS_DIR / f"{proto}.json") or {}
    rr = config.get("revenue_recognition", {})
    return {
        "config_revenue_recognition": json.dumps(rr, ensure_ascii=False, indent=1) if rr else "（无判定书）",
        "official_feed": _load_official_feed(proto),
        "series_json": json.dumps(snapshot.get("income_statement", {}), ensure_ascii=False, indent=1),
        "chain_data": json.dumps(snapshot.get("holder_returns", {}), ensure_ascii=False, indent=1),
        "third_party_data": json.dumps(
            (load_json(ALL_PROTOCOLS_FILE) or {}).get("protocols", {}).get(proto, {}),
            ensure_ascii=False, indent=1)[:4000],
        "fields": "shareholder_yield_percent / revenue_usd_365d / net_income_usd_365d",
        "threshold_percent": 20,
    }


def _load_official_feed(proto):
    """读官方公告抓取缓存（ai-watch-official.py 产出，M1 实现）；
    当前无缓存时返回占位提示。"""
    cache = BASE_DIR / "data" / "official-feeds" / f"{proto}.json"
    if cache.exists():
        return Path(cache).read_text(encoding="utf-8")[:4000]
    return "（暂无官方抓取缓存；ai-watch-official.py 实现后接入）"


def run_freshness_check():
    """新鲜度：纯脚本检查，不消耗 GLM。遍历 snapshot + daily。"""
    alerts = []
    for f in sorted(SNAPSHOTS_DIR.glob("*.json")):
        snap = load_json(f)
        if not snap:
            alerts.append({"protocol": f.stem, "issue": "snapshot JSON 解析失败", "severity": "high"})
            continue
        try:
            as_of = datetime.strptime(snap["as_of"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            hours = (datetime.now(timezone.utc) - as_of).total_seconds() / 3600
            if hours > FRESHNESS_HOURS:
                alerts.append({"protocol": f.stem, "issue": f"snapshot 停更 {hours:.0f}h", "severity": "high"})
        except ValueError:
            alerts.append({"protocol": f.stem, "issue": "as_of 格式非法", "severity": "medium"})
    return {"alerts": alerts, "verdict": "alert" if alerts else "ok",
            "summary_zh": f"新鲜度检查：{len(alerts)} 个快照过期" if alerts else "全部快照新鲜"}


def run_regression_check(before_file=None):
    """口径回归：对比接入前后的既有协议数值（before 快照由接入流程保留）。"""
    before = load_json(before_file) if before_file else None
    if not before:
        return {"regressed": [], "verdict": "ok",
                "summary_zh": "无 before 基线（首次运行），跳过回归检查"}
    regressed = []
    for proto, pre in before.get("protocols", {}).items():
        cur = load_json(SNAPSHOTS_DIR / f"{proto}.json")
        if not cur:
            continue
        for field in ("shareholder_yield_percent", "revenue_usd_365d"):
            a = pre.get(field)
            b = cur.get("holder_returns", {}).get("summary", {}).get(field) if field == "shareholder_yield_percent" else None
            if field == "shareholder_yield_percent" and a is not None and b is not None and abs(a - b) > 0.01:
                regressed.append({"protocol": proto, "field": field, "before": a, "after": b})
    return {"regressed": regressed, "verdict": "regression" if regressed else "ok",
            "summary_zh": f"回归检查：{len(regressed)} 个字段变化" if regressed else "无回归"}


def run_llm_task(client, task, proto, templates):
    """跑单个 LLM 审计任务，返回 (result, err) 或抛 AI_ERR 标定。"""
    tpl = templates.get(task)
    if not tpl:
        return {"error": f"未知任务 {task}"}, "AI_ERR"
    ctx = build_context_for(proto)
    try:
        user_prompt = tpl["user_template"]
        for k, v in ctx.items():
            user_prompt = user_prompt.replace("{" + k + "}", str(v))
        result = client.chat(tpl["system"], user_prompt)
        return result, None
    except (RuntimeError, json.JSONDecodeError, KeyError, TypeError) as e:
        return {"error": str(e)}, "AI_ERR"


# ── 主流程 ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Crypto3D AI 自检哨兵")
    parser.add_argument("--task", choices=["mechanism-change", "data-plausibility",
                                           "cross-validation", "freshness", "regression"],
                        help="只跑指定任务；默认全部")
    parser.add_argument("--protocols", nargs="*", help="指定协议；默认全部有 snapshot 的")
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 任务（仅 freshness/regression）")
    parser.add_argument("--date", default=date.today().isoformat(), help="审计日期（默认今天）")
    parser.add_argument("--regression-before", help="回归基线 JSON 路径")
    args = parser.parse_args()

    sentinel = load_json(CONFIG_FILE) or {}
    templates = load_json(TEMPLATES_FILE) or {}
    AUDIT_DIR.mkdir(exist_ok=True)

    protos = args.protocols or sorted(f.stem for f in SNAPSHOTS_DIR.glob("*.json"))
    if args.protocols:
        protos = [p for p in args.protocols if (SNAPSHOTS_DIR / f"{p}.json").exists()]

    client = GLMClient(sentinel)
    if not client.available and not args.no_llm:
        print(f"⚠ 未检测到 {sentinel.get('api_key_env', 'GLM_API_KEY')}，LLM 任务将标 AI_ERR（--no-llm 跳过）")

    tasks = [args.task] if args.task else sentinel.get("tasks", [])
    results = {}
    alerts = {"alert": [], "review": [], "ok": []}

    for task in tasks:
        if task == "freshness":
            results["freshness"] = run_freshness_check()
        elif task == "regression":
            results["regression"] = run_regression_check(args.regression_before)
        elif args.no_llm:
            results[task] = {"skipped": "no-llm"}
            continue
        else:
            task_results = {}
            for proto in protos:
                res, err = run_llm_task(client, task, proto, templates)
                task_results[proto] = res
                if err:
                    alerts["alert"].append({"task": task, "protocol": proto, "issue": err})
            results[task] = task_results

        # 告警分级汇总
        if task == "freshness":
            for a in results["freshness"].get("alerts", []):
                alerts["alert"].append({"task": "freshness", **a})
        elif task == "regression":
            if results["regression"].get("verdict") == "regression":
                alerts["alert"].append({"task": "regression", "issue": "存在回归！"})

    # 审计痕迹（同一天多次运行合并，不覆盖已有任务结果）
    out_file = AUDIT_DIR / f"{args.date}.json"
    existing = load_json(out_file) if out_file.exists() else {}
    merged_results = dict(existing.get("results", {}))
    merged_alerts = {k: list(existing.get("alerts", {}).get(k, [])) for k in ("alert", "review", "ok")}
    for task in tasks:
        if task in results:
            merged_results[task] = results[task]
    for k in ("alert", "review", "ok"):
        merged_alerts[k].extend(alerts[k])
    # 去重（同一条告警只留一次）
    merged_alerts = {k: list({json.dumps(x, ensure_ascii=False): x for x in v}.values())
                     for k, v in merged_alerts.items()}
    audit = {
        "date": args.date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocols": protos,
        "tasks": sorted(set(existing.get("tasks", [])) | set(tasks)),
        "results": merged_results,
        "alerts": merged_alerts,
    }
    out_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

    # 输出汇总（基于合并后数据）
    n_alert = len(merged_alerts["alert"])
    n_review = len(merged_alerts["review"])
    print(f"审计完成: {args.date} | {len(merged_results)} 任务 | {len(protos)} 协议")
    print(f"  告警: {n_alert} alert, {n_review} review")
    if n_alert:
        for a in merged_alerts["alert"]:
            print(f"  [ALERT] {a.get('task')}/{a.get('protocol', '')}: {a.get('issue')}")
        # TG 通知（未配置则 stderr 提示）
        tg_token = os.environ.get("TG_BOT_TOKEN")
        tg_chat = os.environ.get("TG_CHAT_ID")
        if tg_token and tg_chat:
            _notify_telegram(tg_token, tg_chat, json.dumps(merged_alerts["alert"], ensure_ascii=False))
        else:
            print("  （未配置 TG_BOT_TOKEN/TG_CHAT_ID，告警仅记录到 data/ai-audit/）", file=sys.stderr)
    print(f"审计痕迹: {out_file}")
    return 1 if n_alert else 0


def _notify_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": f"[Crypto3D AI审计] {text}"}).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())
