# 多周期股东回报统一重构方案（7D / 30D / 90D / 365D 同源）

> 状态：**阶段 0/1/2/3 均已实现（dev）**，validate 0/0 —— 待 Boss 验收后 cherry-pick `main`（2026-10-08）
> 目标分支：`dev` →（Boss 批准后）cherry-pick `main`
> 关联文档：`docs/tev-equity-upgrade-prd.md`、`docs/financial-snapshot-schema.md`、`docs/schema/financial-snapshot.schema.json`

---

## 0. 一句话目标

把「口径（哪些价值流算股东回报）」与「窗口（7/30/90/365 天）」**解耦**：
口径在每个协议的 adapter 里**只定义一次**，窗口只是同一口径的时间切片 →
四个 tab 读**同一份**快照派生数据，**结构上不可能再漂移**。

---

## 1. 问题定性（为什么是两套）

| | 365D（现状正确） | 7D/30D/90D（现状冻结） |
|---|---|---|
| 数据生产者 | `adapter.py` → `build-snapshot.py`（每日） | 旧 `sync-tev-data.js`（**已停用**，现为 `.stub` 假文件） |
| 落盘字段 | `snapshots/*.json` → `all-protocols.shareholder_yield_percent` | `all-protocols.metrics.shareholder_yield_{7,30,90}d_ann` 等 |
| 是否被 `daily-run.sh` 调用 | ✅ | ❌ |

**根因**：`docs/schema/financial-snapshot.schema.json` **全 schema 无任何周期维度**（每个字段都写死 `_365d`）。
M1–M3 重构把 365D 迁到新架构时，前端那排周期 tab 仍指向旧脚本 → 旧脚本停用即冻结。
**这是"半截迁移"，不是设计。**

---

## 2. 涉及面盘点（实测）

### 2.1 前端消费点（不动，但要保证供给）
- `equity/index.html`（主表）与 `equity/protocol.html`（详情页）的周期切换读：
  - `metrics.shareholder_yield_{7,30,90}d_ann`（股东回报率，年化）
  - `metrics.total_yield_{7,30,90}d_ann`（收入收益率 / Earning Yield，年化）
  - `metrics.dividend_yield_*_ann` / `metrics.buyback_yield_*_ann`
  - `payout_ratio_{7,30,90}d` + `payout_ratio_365d`（派息率）
  - 365D 走顶层 `shareholder_yield_percent` / `total_yield_percent` / `payout_ratio`

### 2.2 各协议"周期源数据"可用性（决定改造模板）

| 类别 | 协议 | 周期源数据 |
|---|---|---|
| **A. DefiLlama 序列** | aave, dydx, eigenlayer, fluid, gmx, jito, kamino, layerzero, lido, maple, morpho, pendle, sky, spark（14） | `dailyRevenue` / `dailyHoldersRevenue` 日频序列（`sync-holders-revenue.py` 已在拉） |
| **B. 链上序列** | aster, justlend, pancakeswap, uniswap（4） | `validation.burn/buy_{7,30,90,365}d_*` **已存在分窗口原始值** × 现价 |
| **C. 特殊口径** | curve（veCRV 加权）、bnb（平台币 `return_yield_*_percent`） | 自有分周期字段 |
| **D. 无序列** | bgb, compound, ethena, hype, mnt, okb（6） | 无日频源（快照展开或季度） → 只能同值或标注不可得 |

**关键结论**：**22/26 协议的周期原始数据其实是齐的**，只是从未被写进快照；真正"无源"的只有 6 个。
所以"禁止通用公式"指的是**口径**不能通用（Lido 算 0、Uniswap 算链上销毁…），但**聚合机制**（按窗口求和→年化）完全可以复用。

### 2.3 validate 约束（必须保持）
`scripts/validate.py::recompute_holder_summary` 从 `holder_returns.by_mechanism`（`type in destroy|buyback|yield`）**重算 summary**，
差异 >0.5% 报错。→ **by_period.365d 必须与 by_mechanism 求和严格一致**（沿用此闸门）。

---

## 3. 目标架构

```
每协议 adapter.py
   ├─ 口径定义（一次）：哪些价值流算股东回报、是否暂停/为 0
   └─ 按窗口聚合 → by_period { 7d, 30d, 90d, 365d }
                 ↓
        snapshots/<id>.json  (新增 by_period)
                 ↓  build-snapshot.py 派生每窗口 yield
                 ↓  sync-all-protocols-from-snapshots.py 写入
        all-protocols.json  metrics.*_ann + payout_ratio_*
                 ↓
        index.html / protocol.html 四个 tab 读同一批字段   ← 同源，不可能漂移
```

**分层原则**
1. **口径层（每协议独有）**：写在 adapter 里，一年只看一次；改动走 code review。
2. **聚合层（全站共用）**：抽成公共库 `scripts/lib/period_metrics.py`，避免 27 份重复代码。
3. **展示层**：前端不改逻辑，只保证字段供给正确。

---

## 4. Schema 变更（向后兼容，纯新增）

`schema/financial-snapshot.schema.json` 新增（**不删旧字段**）：

```jsonc
"holder_returns": {
  "by_mechanism": [ ... 保持不变 ... ],      // 365D 机制明细
  "summary":      { ... 保持不变 ... },      // = by_period.365d 的汇总视图
  "by_period": {                            // ★ 新增
    "7d":   { "shareholder_returns_usd": n|null, "shareholder_yield_percent": n|null,
              "destroy_usd": n|null, "yield_usd": n|null, "payout_ratio": n|null,
              "status": "active|paused|none", "source": "defillama|chain|none" },
    "30d":  { ... }, "90d": { ... }, "365d": { ... }
  }
},
"income_statement": {
  "revenue": {
    ...
    "by_period": {                          // ★ 新增（供各周期 Earning Yield / P/S）
      "7d": {"total_usd": n|null}, "30d": {...}, "90d": {...}, "365d": {...}
    }
  }
}
```

**硬约束（validate 强制）**
- `by_period` 四个窗口**必须齐全**（值可为 `null`，但键必须在）。
- `by_period.365d.shareholder_returns_usd == summary.shareholder_returns_usd_365d`（容差 0.5%）。
- `by_period[N].shareholder_yield_percent == shareholder_returns_usd / mcap × (365/N) × 100`（N=365 不年化）。
- `null` 表示"该窗口确实不可得"，**禁止编造 0**（沿用现有 null 语义）。

---

## 5. 公共库 `scripts/lib/period_metrics.py`

```python
WINDOWS = (7, 30, 90, 365)

def sum_window(daily_pairs, n, asof=None):
    """[[ts,val],...] → 最近 n 天合计。"""
def yield_ann(usd, mcap, n):
    """USD → 年化收益率 %（N=365 不年化）。"""
def build_by_period(rev_series=None, ret_series=None, mcap=None,
                    basis="holders_revenue"|"zero"|"same_as_365d",
                    ret_usd_by_window=None):
    """统一产出 by_period 结构。basis 决定口径；ret_usd_by_window 供链上模板直接喂分窗口值。"""
```

- **basis="holders_revenue"**：用 DefiLlama holdersRevenue 序列按窗口聚合（14 协议）。
- **basis="zero"**：全窗口 0（paused / none 协议，如 aave、lido）。
- **basis="same_as_365d"**：无日频源时四窗口同值（D 类，前端至少不显示假差异；source 标 `none`）。
- **链上模板**：adapter 传 `ret_usd_by_window={7:…,30:…,90:…,365:…}`（直接读 `validation.burn_*_N d` × 现价）。

---

## 6. Adapter 改造（三种模板）

**模板 A（DefiLlama，14 协议）**——adapter 里加：
```python
from scripts.lib.period_metrics import build_by_period
holder_returns["by_period"] = build_by_period(
    rev_series=dl_rev, ret_series=dl_hol, mcap=mcap,
    basis="zero" if paused_or_none else "holders_revenue")
```
（序列由 `sync-holders-revenue.py` 缓存到 `data/series/<id>.json`，避免 adapter 联网）

**模板 B（链上，4 协议）**——adapter 直接组装 `ret_usd_by_window`：
```python
holder_returns["by_period"] = build_by_period(
    ret_usd_by_window={n: (validation.get(f"burn_{n}d_uni") or 0)*uni_price for n in WINDOWS},
    rev_series=None, ... )
```

**模板 C（无源，6 协议）**——`basis="same_as_365d"`，`source="none"`，或按各自机制显式声明。

> 每个 adapter 的**口径决策仍逐协议 review**（这是本方案唯一不可自动化的部分，也是当初 opt-in 只覆盖 sky/aave 的原因）。

---

## 7. 上层脚本改造

| 脚本 | 改动 |
|---|---|
| `sync-holders-revenue.py` | 增加：把 DefiLlama 逐日序列缓存到 `data/series/<id>.json`；**删除**现 `period_return_basis` 临时 opt-in（由 adapter 接管） |
| `build-snapshot.py` | 新增 `derive_period_yields()`：从 `by_period` 的 USD + mcap 派生各窗口 yield，回填 `by_period[N].shareholder_yield_percent` 与 `payout_ratio` |
| `sync-all-protocols-from-snapshots.py` | 新增：读 `snapshot.holder_returns.by_period` → 写 `metrics.shareholder_yield_{7,30,90}d_ann` / `buyback/dividend_*_ann` / `payout_ratio_{7,30,90,365}d`；读 `revenue.by_period` → 写 `metrics.total_yield_{7,30,90}d_ann` |
| `validate.py` | 新增 §2 的 4 条硬约束 |
| `daily-run.sh` | 无需改（脚本链不变） |

---

## 8. 前端

**逻辑零改动**（继续读 `metrics.*_ann` / `payout_ratio_*`），字段改由快照统一供给后自动同源。
可选增强（择机）：详情页的 `calc_pipeline` 各 step 直接引用 `by_period`，让"计算口径"tab 也逐窗口可核。

---

## 9. 迁移与发布（分批，每批须 Boss 验收）

| 阶段 | 内容 | 产出 | 验收 |
|---|---|---|---|
| **0** | schema 新增字段 + 公共库 + validate 新规则（`by_period` 暂设为"可选"） | 无数据变化 | validate 仍 0 error |
| **1** | 试点 **4 协议**：sky、aave、uniswap、bnb（覆盖 A/B/C 模板） | 4 份快照含 by_period | 四窗口与 365D 交叉核对 + 截图 |
| **2** | 批量迁移剩余 22 协议（按模板分组，A 类最多） | 全站 by_period | validate 0 error + 抽样比对 |
| **3** ✅ | `by_period` 转**必需**；删除遗留字段与 opt-in hack；`metrics.*_ann` 只由快照驱动 | 旧链彻底退役 | 全站 validate strict 通过 |

**发布纪律**：全程 dev；每阶段验证通过 → 汇报 → **Boss 批准** → cherry-pick main（禁 merge dev）。

---

## 10. 风险与回滚

| 风险 | 缓解 |
|---|---|
| 口径误判（把该为 0 的算成非 0） | 逐协议 review + validate 交叉核 + 与现有 365D 比对 |
| 旧消费者被破坏 | **纯新增字段**，365D 旧字段全部保留 |
| 数据量膨胀（快照多 4 窗口） | 每协议约 +1KB，可忽略 |
| 无源协议（D 类）语义模糊 | 显式 `source:"none"` + `null`，前端不显示假差异 |
| 回滚 | 新增字段独立 → 单 commit revert 即可，不影响存量 |

---

## 11. 待 Boss 确认 → 已定案

1. **口径基线**：A 类默认 `revenue_scaled`（退回 `holders_revenue` 口径已由 adapter 内联接管）；`none/paused` 走 `zero` —— ✅ 已按此实现。
2. **D 类 6 协议**：✅ 采用**显式不可得（`source=none` + 四窗口 `null`）** → 前端周期 tab 显示 `—`（Boss 2026-10-08 决定）。
3. **试点选型**：✅ sky / aave / uniswap / bnb（阶段 1）。
4. **阶段 0 先行**：✅ 已先行，零回归。

---

## 附：工作量预估

- 阶段 0：schema + `period_metrics.py` + validate 规则 ≈ 1 个工作单元
- 阶段 1：4 个 adapter 改造 + 验证 ≈ 1
- 阶段 2：22 个 adapter（A 类 13 个几乎是同模板复制 + 参数）≈ 1.5
- 阶段 3：清理 + 强制化 ≈ 0.5

---

## 12. 实现记录（2026-10-08，dev）

| 阶段 | commit | 内容 |
|---|---|---|
| 0 | `d8a8b488` | schema 新增 `by_period` + `period_metrics.py` + validate §2.5/§2.6（可选） |
| 1 | `8c6da3e9` | 试点 4 协议（sky/aave/uniswap/bnb）adapter 内联产出 `by_period` |
| 2 | `588aa444` | 22 协议 **config 驱动**（`derive_by_period` 四类口径）+ 前端 `none` 组显示「—」；`309a173f` i18n/正则随手修复 |
| 3 | （本提交） | `by_period` 转**必需**（validate strict，镜像豁免）+ 退役 opt-in/遗留字段 |

**阶段 3 具体改动**
1. **`validate.py` §2.5/§2.6**：`holder_returns.by_period` 与 `income_statement.revenue.by_period` 对**展示协议**（`all-protocols.protocols` 的 26 个 key）强制要求；镜像目录（`hyperliquid`）豁免（与 `sync-all`「跳过镜像」一致）。
2. **`sync-holders-revenue.py`**：删除 P1 的 `apply_period_metrics()` + `_annualize_factor()` 及其调用（该函数输出每次都被 `sync-all` 覆盖，已成死代码）；仅保留日频序列刷新职责。
3. **`aave/sky config.json`**：删除 `period_return_basis`（P1 opt-in 临时键）。二者 adapter 内联产出 `by_period`，不依赖该键。
4. **`sync-all-protocols-from-snapshots.py`**：新增幂等 legacy-strip，移除 `validation.period_source/period_caveat/period_fee_rate`（旧 `sync-tev-data.js` 痕迹；前端不消费）。
5. **单一生产者确定**：周期字段（`metrics.*_{n}d_ann` / `payout_ratio_*`）现仅由 `sync-all` 从 `snapshot.holder_returns.by_period` 派生 —— 旧链彻底退役。

**验证**：全量重建 27 snapshot（0 fail）→ sync-all → history 三步 → validate **0 errors / 0 warnings**；反向测试 `tmp/test_p3_required.py` 证明「必需」规则生效且镜像豁免。

**镜像目录**：`data/protocols/hyperliquid`（hype 的数据源，不展示，`data/snapshots/hyperliquid.json` 无 `by_period`）——与 `rebuild-daily.py::EXCLUDED_DIRS={"curve-dex","hyperliquid"}` 一致。

**惰性文件**：`scripts/sync-tev-data.js`（+`.bak`/`.stub`）已无任何脚本/workflow 引用，旧链代码路径彻底退役；文件本体保留（可能被 Mac Mini 侧外部调用，不贸然删除）。如需清理，单独确认后删除。
