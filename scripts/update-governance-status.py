#!/usr/bin/env python3
"""用公开源核对治理提案状态，并补 Snapshot 上 2026-08-10 之后的新提案。

不调用翻译接口。新提案的 summary_zh 等于原文标题，并标 translation=source。
拉不到的来源保持原状态，失败打印后继续，不改其它协议的数据文件。
"""
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "governance.json"
UA = {"User-Agent": "crypto3d-governance/1.0", "Accept": "application/json"}
SNAPSHOT = "https://hub.snapshot.org/graphql"
# 只补这一天之后的新提案，避免把旧历史再灌一遍
NEW_AFTER = 1786320000  # 2026-08-10T00:00:00Z
SPACES = {
    "aavedao.eth": "Aave",
    "uniswapgovernance.eth": "Uniswap",
    "curve.eth": "Curve",
    "gmx.eth": "GMX",
    "cakevote.eth": "PancakeSwap",
    "lido-snapshot.eth": "Lido",
    "morpho.eth": "Morpho",
    "comp-vote.eth": "Compound",
    "ethenagovernance.eth": "Ethena",
    "maple.eth": "Maple Finance",
    "sparkfi.eth": "Spark",
    "sdpendle.eth": "Pendle",
    "eigenlayer1.eth": "EigenLayer",
    "fluiddao.eth": "Fluid",
}


def log(*a):
    print(*a, flush=True)


def get_json(url, data=None, headers=None, timeout=25):
    h = dict(UA)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def prop_id(link):
    if not link:
        return ""
    return str(link).rstrip("/").split("/")[-1]


def snapshot_state(pid):
    q = json.dumps({
        "query": "query($id:String!){proposal(id:$id){id state end title}}",
        "variables": {"id": pid},
    }).encode()
    data = get_json(SNAPSHOT, data=q, headers={"Content-Type": "application/json"})
    return (data.get("data") or {}).get("proposal")


def snapshot_recent(space):
    q = json.dumps({
        "query": """query($space:String!){
          proposals(first:20, where:{space_in:[$space]}, orderBy:"created", orderDirection:desc){
            id title state start end created link
          }
        }""",
        "variables": {"space": space},
    }).encode()
    data = get_json(SNAPSHOT, data=q, headers={"Content-Type": "application/json"})
    return (data.get("data") or {}).get("proposals") or []


def map_snapshot_status(state):
    if state in ("active", "pending"):
        return "active"
    return "closed"


def refresh_existing(props):
    changed = 0
    for p in props:
        if p.get("status") != "active":
            continue
        link = p.get("link") or ""
        try:
            if p.get("source") == "Snapshot" and prop_id(link).startswith("0x"):
                remote = snapshot_state(prop_id(link))
                time.sleep(0.2)
                if not remote:
                    log(f"  ⚠️ Snapshot 无此提案 {prop_id(link)[:10]}…")
                    continue
                new = map_snapshot_status(remote.get("state"))
                if p.get("status") != new:
                    p["status"] = new
                    changed += 1
                    log(f"  Snapshot {p.get('protocol')} → {new}: {(p.get('title') or '')[:48]}")
                if remote.get("end"):
                    p["end"] = remote["end"]
            elif "github.com/" in link and "/pull/" in link:
                m = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", link)
                if not m:
                    continue
                api = f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}/pulls/{m.group(3)}"
                pr = get_json(api)
                time.sleep(0.3)
                if pr.get("merged"):
                    new = "passed"
                elif pr.get("state") == "open":
                    new = "active"
                else:
                    new = "closed"
                if p.get("status") != new:
                    p["status"] = new
                    changed += 1
                    log(f"  GitHub {m.group(3)} → {new}: {(p.get('title') or '')[:48]}")
            elif "/t/" in link and link.startswith("http"):
                m = re.search(r"(https://[^/]+)/t/(?:[^/]+/)?(\d+)", link)
                if not m:
                    continue
                topic = get_json(f"{m.group(1)}/t/{m.group(2)}.json")
                time.sleep(0.25)
                new = "closed" if topic.get("closed") or topic.get("archived") else "active"
                if p.get("status") != new:
                    p["status"] = new
                    changed += 1
                    log(f"  Forum {m.group(2)} → {new}: {(p.get('title') or '')[:48]}")
        except Exception as e:
            log(f"  ⚠️ {p.get('protocol')} {(p.get('title') or '')[:32]}: {e}")
    return changed


def add_snapshot_new(props):
    known = {prop_id(p.get("link")) for p in props}
    added = 0
    for space, protocol in SPACES.items():
        try:
            rows = snapshot_recent(space)
        except Exception as e:
            log(f"  ⚠️ Snapshot {space}: {e}")
            continue
        time.sleep(0.25)
        for row in rows:
            if (row.get("created") or 0) < NEW_AFTER:
                continue
            if row.get("id") in known:
                continue
            title = (row.get("title") or "").strip()
            if not title:
                continue
            props.append({
                "source": "Snapshot",
                "protocol": protocol,
                "title": title,
                "status": map_snapshot_status(row.get("state")),
                "link": row.get("link") or f"https://snapshot.org/#/{space}/proposal/{row.get('id')}",
                "created": row.get("created"),
                "end": row.get("end"),
                "tev_related": False,
                "tev_keywords": [],
                "summary_en": title,
                "summary_zh": title,
                "analysis_zh": "",
                "translation": "source",
            })
            known.add(row.get("id"))
            added += 1
            log(f"  + {protocol} {row.get('state')}: {title[:56]}")
    return added


def recompute(doc, props):
    doc["proposals"] = props
    doc["total"] = len(props)
    doc["active_count"] = sum(1 for p in props if p.get("status") == "active")
    doc["passed_count"] = sum(1 for p in props if p.get("status") == "passed")
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()


def main():
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    props = doc.get("proposals") or []
    log(f"=== 治理状态核对 {datetime.now(timezone.utc).isoformat()} 现有 {len(props)} ===")
    changed = refresh_existing(props)
    added = add_snapshot_new(props)
    if changed or added:
        recompute(doc, props)
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"写回 {OUT.name}: 状态变更 {changed}，新提案 {added}，active {doc['active_count']}")
    else:
        log("无状态变化，不改写 governance.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
