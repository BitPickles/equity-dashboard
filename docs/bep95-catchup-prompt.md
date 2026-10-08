# 提示词：补齐 BNB BEP-95 日销毁序列（交给「数据更新机」执行）

> 用法：把下面 `---` 之间的整段内容粘贴给那台 Mac Mini 上的 AI 代理。

---

## 任务
补齐 BNB 的 BEP-95 每日销毁序列：`data/protocols/bnb/bep95-history.json` 的 `daily[]` 目前只到 **2026-08-10**（515 条），此后停更，导致 BNB 的 BEP-95 收入与历史图缺约 2 个月。请回填到**今天**，并把这件事做成可复用脚本，以后能自动续更。

## 0. 准备工作（分支铁律，先读再动手）
- 仓库：`BitPickles/equity-dashboard`（本机工作目录可能仍叫 `tev-dashboard`）。
- 先 `git fetch origin`，然后在 **dev 分支**上作业：
  ```
  git checkout dev && git pull --ff-only origin dev
  ```
- **必须确认 dev 已包含这两个提交**：`0ee3af01`（BNB asBNB 口径修正 6.87%→1.71%）与 `9bd725f2`（删除遗留数据文件）。缺则先 `git fetch` 再 `git pull`。
- ⚠️ **不要在 main 上做本次补数。** 原因：本补数会重建 BNB 快照；main 上的 asBNB 仍是旧的 6.87%，且 dev→main 尚未发布——若在 main 上补，后续发布 dev 会用旧文件覆盖掉补数结果。
- 全部完成、推送 dev 之后，**切回 main**（本机日更脚本 `scripts/daily-run.sh` 要求当前分支必须是 main）：
  ```
  git checkout main
  ```

## 1. 交付物
1. **新脚本 `scripts/fetch-bep95-daily.py`**：幂等、可反复运行，自动补齐 `bep95-history.json` 缺失的每一天。
2. 回填后的 `data/protocols/bnb/bep95-history.json`（`daily[]` 续到当天）。
3. 更新后的 `data/protocols/bnb/dead-balance-snapshot.json`。
4. 重跑数据链后 `scripts/validate.py` 输出 **0 errors / 0 warnings**。
5. 提交并 `git push origin dev`。

## 2. 数据结构（严格照写，禁止改键名 / 改已有行）
`data/protocols/bnb/bep95-history.json`
```json
{
  "source": "Dune Analytics (bnb.traces, dead address incoming, value < 100k BNB)",
  "seeded_at": "2026-04-18T18:10:25.802380Z",
  "seed_range": { "start": "2025-03-14", "end": "2026-04-18", "days": 401 },
  "daily": [
    { "date": "2025-03-14", "bnb": 10.422107, "tx_count": 7512 },
    { "date": "2026-08-10", "bnb": 34.002021, "tx_count": null, "source": "rpc_delta" }
  ],
  "updated_at": "<ISO8601 UTC，本次运行时间>"
}
```
- `date`：`YYYY-MM-DD`（UTC），**必须严格递增、无重复、无缺口**。
- `bnb`：当日 BEP-95 销毁量（BNB，浮点）。
- `tx_count`：RPC 补齐的行写 `null`。
- 本次新补的行，一律加 `"source": "rpc_delta"`。播种期（≤2026-04-18）的历史行**原样保留**，不要动。

`data/protocols/bnb/dead-balance-snapshot.json`（当前值：`{"date":"2026-08-10","balance_bnb":16493774.214717573}`）
```json
{ "date": "YYYY-MM-DD", "balance_bnb": <float> }
```

## 3. 算法：黑洞地址余额差分法
1. 用 BSC RPC 读黑洞地址余额：
   `eth_getBalance("0x000000000000000000000000000000000000dEaD", "latest")` → wei，除以 `1e18` 得 BNB。
   公共节点（按序 fallback，任一可用即止）：
   `https://bsc-dataseed.binance.org` · `https://bsc-dataseed1.binance.org` · `https://bsc-dataseed1.defibit.io` · `https://bsc-dataseed1.ninicoin.io` · `https://bsc-rpc.publicnode.com`
2. `delta = 今日余额 − dead-balance-snapshot.balance_bnb`
3. 从 `data/protocols/bnb/burn-history.json → quarterly_burns[]` 取出落在该区间内、**已记录**的季度 Auto-Burn 数量合计，从 `delta` 中扣除 → 得到纯 BEP-95 增量。
   ⚠️ **`quarterly_burns` 是只读**：那是人工核对过的官方销毁公告，**绝对不要新增/修改/删除**。
4. 按区间 `(daily 最后一条的 date, 今天]` 的**实际天数均摊**，缺一天就写一条。
5. 异常保护：`delta <= 0`，或按天数摊出来的日均值离群（例如 > 2000 BNB/天）→ **告警并停止写入**，打印余额、区间、天数供人工判断。
6. 写完后更新 `dead-balance-snapshot.json`（`date`=今天，`balance_bnb`=本次读到的余额）与 `bep95-history.json.updated_at`。

## 4. 口径陷阱（务必遵守）
- **阈值 1000 BNB**：下游 `data/protocols/bnb/adapter.py` 会把 `daily[]` 中 **>1000 BNB 的行视为 Auto-Burn 执行日并剔除**（`and float(row.get("bnb") or 0) < 1000`）。所以季度 Auto-Burn 的大额**绝不能**被记成某一天的 BEP-95 值——这正是第 3 步要先扣除它的原因。
- 黑洞地址同时会收到**非销毁**转账（垃圾空投等）。Dune 播种口径是「dead address incoming, value < 100k BNB」；RPC 侧只用**余额差分**，不要按单笔交易 `value` 累加。
- 合理量级参考：平时 **40–60 BNB/天**，链上活跃期可到 **500+ BNB/天**。若算出上万 BNB/天，一定是哪里错了。
- 幂等：同一天重复运行应**跳过**（检测 `dead-balance-snapshot.date == 今天` 即跳过累积，只允许重读）。

## 5. 补数完成后必跑（顺序不能变）
```bash
python3 scripts/build-snapshot.py bnb        # 重建 bnb 快照（会重写 history 末条，清掉 daily_value）
python3 scripts/fetch-bnb-history.py         # 必须紧随其后，重写 data/history/bnb.json
python3 scripts/sync-all-protocols-from-snapshots.py
python3 scripts/validate.py                  # 必须 0 errors / 0 warnings
```

## 6. 验收标准（三条全中才算完成）
1. `data/history/bnb.json` 最后一条 `as_of` = 今天，且 **`daily_value` 非空**（说明 BEP-95 源已覆盖到当天；若为 `null` 说明没补全）。
2. `data/snapshots/bnb.json → holder_returns.by_period` 的 **7d/30d/90d/365d 四窗口齐全**，且 `365d.shareholder_yield_percent` 与 `holder_returns.summary.shareholder_yield_percent` 一致。
3. `python3 scripts/validate.py` 打印 `结果: 0 errors, 0 warnings`。

## 7. 提交
```bash
git add data/protocols/bnb/bep95-history.json \
        data/protocols/bnb/dead-balance-snapshot.json \
        data/snapshots/bnb.json data/history/bnb.json data/all-protocols.json \
        scripts/fetch-bep95-daily.py
git commit -m "data(bnb): 补齐 BEP-95 日序列 2026-08-11 → <YYYY-MM-DD>（新增 scripts/fetch-bep95-daily.py）"
git push origin dev
git checkout main
```

## 8. 顺手完成（可选但建议）
把 `python3 scripts/fetch-bep95-daily.py` 接进 `scripts/daily-run.sh`，放在 `build-snapshot.py` **之前**（与 BNB 相关步骤同段），从此该序列自动续更，不会再断。

## 9. 完成后回报
请回报：补了多少天（起止日期）、今日黑洞地址余额、`daily[]` 总条数、validate 结果、以及 `data/history/bnb.json` 末条的 `daily_value`。

---
