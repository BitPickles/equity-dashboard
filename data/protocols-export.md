# TEV Dashboard 协议数据汇总
生成时间: 2026-02-07 14:28:34

用于二次核实验证。每个协议包含：TEV 状态、分配比例、机制描述、数据来源。

---

## aave

**名称**: Aave (AAVE)
**类别**: lending
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "$50M 年度回购预算",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "回购 - Aave DAO 每年拨出 $50M 预算用于回购 AAVE 代币"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "Aave Governance Forum",
      "type": "governance",
      "url": "https://governance.aave.com",
      "reliability": "high"
```

---

## aster

**名称**: Aster (AsterDEX) (ASTER)
**类别**: perpetual_dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "协议收入用于回购 ASTER",
    "buybacks": "ACTIVE",
    "buyback_details": "协议收入回购 + Foundation 稳定回购",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "协议收入 → ASTER 回购"
  },
  "market_data": {
    "price_usd": 0.54728,
    "circulating_market_cap": 1346353083,
    "total_supply": 8000000000,
    "tvl_usd": 1091092274,
    "volume_24h_usd": 236804925,
```

### 分析师备注（摘要）
【2026-02-07 调研更新】

## 项目背景
Aster 是 Astherus + APX Finance 于 2024 年底合并的产品。
- **YZi Labs (原 Binance Labs)** 支持
- **CZ 个人投资** $2.5M+ ASTER

## TEV 机制（已确认）

1. **协议收入回购** ✅ ACTIVE
   - 文档明确：\...

---

## bgb

**名称**: Bitget Token (BGB)
**类别**: cex_token
**置信度**: low

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "N/A",
    "fee_switch_details": "CEX 收入不直接链上分配",
    "buybacks": "ACTIVE",
    "dividends": "UNKNOWN",
    "burns": "ACTIVE",
    "burn_details": "季度回购销毁（具体比例待确认）",
    "primary_value_accrual": "回购销毁 - 季度用平台收入回购销毁 BGB"
  },
  "market_data": {
    "price_usd": 2.70,
    "circulating_market_cap": 1888393751,
    "total_supply": 2000000000,
    "snapshot_date": "2026-02-05",
    "data_source": "CoinGecko"
```

### 分析师备注（摘要）
【2026-02-05 初步调研】

## BGB TEV 评估

### 已知信息
1. **Bitget 平台币**：类似 BNB/OKB 的 CEX token
2. **季度回购销毁**：有此机制，但具体比例待确认
3. **合约支持销毁**：Etherscan 验证合约有 burn 功能

### 数据限制
1. ❌ Bitget 网站被 Cloudflare 拦截
2. ❌ 无法获取官方文档
3. ⚠️ 需要通过公告整理销毁数据

### 与同类对比
| 平台币 | 销毁机制 | 数据透明度 |
|--------|----------|...

---

## bnb

**名称**: BNB (BNB)
**类别**: cex_token
**置信度**: low

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "N/A",
    "fee_switch_details": "CEX 收入不直接链上分配",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "ACTIVE",
    "burn_details": "季度 Auto-Burn + 实时 BEP-95 销毁",
    "primary_value_accrual": "销毁 - 通过持续销毁减少总供应量，目标 100M BNB"
  },
  "market_data": {
    "price_usd": 610.09,
    "circulating_supply": 136359744,
    "circulating_market_cap": 85309283181,
    "target_supply": 100000000,
    "snapshot_date": "2026-02-05",
```

### 分析师备注（摘要）
【2026-02-05 初步调研】

## BNB TEV 评估挑战

BNB 作为 CEX 平台币，与 DeFi 协议有本质区别：

### 已知机制
1. **季度 Auto-Burn**：公式透明 (B = N × 1000 / P)
2. **实时 BEP-95 销毁**：链上可验证

### 数据限制
1. ❌ Binance 作为私营公司，不公开财务数据
2. ❌ 无法计算 holders revenue（销毁的 BNB 来源于 Binance 利润，但利润不公开）
3. ⚠️ 只能基于销毁价值来估算 TEV

### TEV Yield 估�...

---

## compound

**名称**: Compound (COMP)
**类别**: lending
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "Compound 协议费用开关未开启，收入保留在协议储备",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "纯治理代币 - COMP 仅用于治理投票，无收入分配"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "Compound Governance",
      "type": "governance",
      "url": "https://compound.finance/governance",
      "reliability": "high"
```

---

## curve

**名称**: Curve (CRV)
**类别**: dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "50% 交易手续费分配给 veCRV 持有者（以 3CRV 形式），每周分发",
    "buybacks": "NONE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "分红 - veCRV 持有者每周获得 3CRV 分红"
  },
  "ve_token": {
    "name": "veCRV",
    "lock_contract": "0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2",
    "max_lock_period": "4 years",
    "benefits": [
      "50% 协议手续费分成（3CRV）",
      "治理投票权",
```

### 分析师备注（摘要）
【2026-02-05 调研更新】

## Curve 双重激励模式说明

Curve 采用特殊的双重激励模式，需区分 TEV 和 LP 激励：

### 1. TEV 部分（计入 TEV yield）
- **50% 交易手续费** 分配给 **veCRV 持有者**
- 以 3CRV（稳定币 LP token）形式每周分发
- 分发合约: 0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc
- 过去30天分红: ~$97万，年化约 $1165万

### 2. LP 激励部分（不计入 TEV）
- **CRV 代币奖励** 分配给 **LP 提供�...

---

## dydx

**名称**: dYdX (DYDX)
**类别**: perpetuals
**置信度**: medium

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "75% 协议净收入用于 DYDX 回购（已从 staking rewards 模式转变）",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "回购 - 75% 协议净收入用于 DYDX 回购"
  },
  "market_data": {
    "price_usd": 0.11,
    "circulating_market_cap": 90016535,
    "total_supply": 1000000000,
    "snapshot_date": "2026-02-05",
    "data_source": "CoinGecko (dydx-chain)"
  },
```

### 分析师备注（摘要）
【2026-02-05 调研修正 - 重要】

## 数据错误修正

### 问题 1：流通供应量错误
- ❌ 旧数据：29.6M DYDX (以太坊上的旧代币)
- ✅ 正确：大部分代币已迁移到 dYdX Chain
- ✅ 正确市值：~$90M（从 CoinGecko dydx-chain 获取）

### 问题 2：TEV 机制已变更
- ❌ 旧机制：100% 交易费用分配给 stakers
- ✅ 新机制：**75% 协议净收入用于 DYDX 回购**
- 来源：DefiLlama tokenRights 数据

### 正确 TEV Yield �...

---

## eigenlayer

**名称**: EigenLayer (EIGEN)
**类别**: restaking
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "协议费用开关未开启",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "纯治理代币 - EIGEN 目前仅用于治理，无收入分配机制"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "DefiLlama TokenRights",
      "type": "api",
      "url": "https://api.llama.fi/protocols",
      "reliability": "high",
```

---

## ethena

**名称**: Ethena (ENA)
**类别**: basis_trading
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ACTIVE",
    "fee_switch_details": "Fee switch ON，100% 协议收入分配给 sENA 质押者",
    "buybacks": "ACTIVE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "分红 + 回购 — 100% 协议收入→sENA 质押者，加 $310M 大规模 ENA 回购"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "DefiLlama tokenRights",
      "type": "api",
      "url": "https://api.llama.fi/protocol/ethena",
      "description": "tokenRights 数据确认 fee switch ON, dividends ACTIVE",
```

---

## gmx

**名称**: GMX (GMX)
**类别**: perp_dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "30% 平台费用分配给质押 GMX 持有者",
    "buybacks": "NONE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "分红 - 质押 GMX 获得 ETH/AVAX 分红"
  },
  "market_data": {
    "price_usd": 5.93,
    "circulating_supply": 10386388,
    "circulating_market_cap": 61633069,
    "total_supply": 10685596,
    "holders": 300830,
    "snapshot_date": "2026-02-05"
```

### 分析师备注（摘要）
【2026-02-05 调研核对】

## TEV Yield 核对结果

**TEV Yield ≈ 23.5% 是正确的**

### 计算过程
- 30天 holders revenue: $1,208,117
- 年化: ~$14.5M
- 流通市值: ~$61.6M
- TEV Yield = $14.5M / $61.6M = 23.5%

### 为什么 GMX TEV Yield 如此高？

1. **市值较小**: GMX 流通市值仅 $61.6M，远低于其他 DeFi 协议
2. **收入较高**: 永续合约交易所收入模式成熟，年化平台收入约 $48M（GMX stakers 获得 30% = $14.5M）
3. **�...

---

## hype

**名称**: Hyperliquid (HYPE)
**类别**: perp_dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "99% 永续交易费用用于回购 HYPE",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "UNKNOWN",
    "primary_value_accrual": "回购 - 99% 永续交易费用流入 Assistance Fund 回购 HYPE"
  },
  "market_data": {
    "price_usd": 32.56,
    "circulating_market_cap": 7762595982,
    "snapshot_date": "2026-02-05",
    "data_source": "CoinGecko"
  },
  "calculated_tev": {
```

### 分析师备注（摘要）
【2026-02-05 调研】

## HYPE TEV 机制 - 非常强

### 核心机制
**99% 永续交易费用 → Assistance Fund → 回购 HYPE**

这是 DeFi 中最强的 TEV 机制之一！

### 费用分配
| 来源 | 分配 |
|------|------|
| 永续交易费 99% | Assistance Fund（回购 HYPE） |
| 永续交易费 1% | HLP Vault 供应者 |
| Builder 费用 | 全部给 Builder |

### 与 GMX 对比
| 协议 | 持有者分成 | 机制 |
|------|------------|------|
| Hyperliquid ...

---

## jito

**名称**: Jito (JTO)
**类别**: liquid_staking
**置信度**: medium

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "JTO 目前主要用于治理，MEV 收益流向 JitoSOL 持有者",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "治理代币 - MEV 收益流向 JitoSOL，JTO 用于治理"
  },
  "confidence": "medium",
  "data_sources": [
    {
      "name": "Jito Docs",
      "type": "documentation",
      "url": "https://docs.jito.network",
      "reliability": "high"
```

---

## justlend

**名称**: JustLend (JST)
**类别**: lending
**置信度**: low

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "PARTIAL",
    "fee_switch_details": "声称有协议收入分配给 JST stakers，但缺乏可验证数据",
    "buybacks": "NONE",
    "dividends": "PARTIAL",
    "burns": "NONE",
    "primary_value_accrual": "未确认 — 声称有 staking 分红但透明度极低"
  },
  "confidence": "low",
  "data_sources": [
    {
      "name": "JustLend Official",
      "type": "documentation",
      "url": "https://justlend.org",
      "description": "官方网站，JS 渲染的 SPA 难以爬取详细内容",
```

---

## kamino

**名称**: Kamino Finance (KMNO)
**类别**: lending
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "NONE",
    "fee_switch_details": "无协议收入直接分配给 KMNO 持有者。所谓 'staking' 实为 farming 奖励加成机制",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "无 TEV — KMNO staking 仅提供 farming 奖励加成（boost），非协议收入分配。Season 奖励来自代币国库排放（激励），不是 fee distribution"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "Kamino Season 5 公告",
      "type": "governance",
      "url": "https://gov.kamino.finance/t/introducing-kamino-season-5/854",
      "description": "详细说明了 KMNO staking boost 机制：起始 3% 加成，每天 +0.1%，每 1 KMNO 质押对 $1 仓位施加加成",
```

---

## lido

**名称**: Lido (LDO)
**类别**: liquid_staking
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "所有收入归 DAO 国库，无分配给 LDO 持有者",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "无 - LDO 仅为治理代币，不分享协议收入"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "DefiLlama tokenRights",
      "type": "api",
      "url": "https://api.llama.fi/protocol/lido",
      "reliability": "high"
```

---

## maple

**名称**: Maple Finance (SYRUP)
**类别**: lending
**置信度**: medium

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "协议费用分配给 SYRUP stakers",
    "buybacks": "NONE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "Staking 奖励 - 质押 SYRUP 获得协议借贷费用分成"
  },
  "confidence": "medium",
  "data_sources": [
    {
      "name": "Maple Finance Blog",
      "type": "report",
      "url": "https://maple.finance/news",
      "reliability": "high"
```

---

## mnt

**名称**: Mantle (MNT)
**类别**: l2_token
**置信度**: low

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "N/A",
    "fee_switch_details": "L2 gas 费用机制，非传统 fee switch",
    "buybacks": "UNKNOWN",
    "dividends": "UNKNOWN",
    "burns": "UNKNOWN",
    "primary_value_accrual": "待确认 - Gas 消耗 + 潜在的质押奖励"
  },
  "market_data": {
    "price_usd": 0.61,
    "circulating_supply": 3252944056,
    "circulating_market_cap": 1981231322,
    "total_supply": 6219316794,
    "snapshot_date": "2026-02-05",
    "data_source": "CoinGecko / Etherscan"
```

### 分析师备注（摘要）
【2026-02-05 初步调研】

## MNT 特殊情况说明

MNT 与 BNB/OKB 不同，它不是传统意义上的 CEX 平台币：

### 背景
1. **前身 BitDAO**：由 Bybit 支持创立
2. **2023 年转型**：BitDAO → Mantle
3. **定位变化**：从 DAO 治理代币 → L2 原生代币

### TEV 评估挑战
1. ⚠️ 不是直接的 Bybit 平台币
2. ⚠️ TEV 机制不如 BNB/OKB 明确
3. ⚠️ 主要价值来自 L2 生态而非交易所收入

### 需要向 Boss 确认\...

---

## morpho

**名称**: Morpho (MORPHO)
**类别**: lending
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "Morpho 当前无协议费用，由 vault curators 自行设定",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "纯治理代币 - MORPHO 目前仅用于治理投票"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "Morpho Docs",
      "type": "documentation",
      "url": "https://docs.morpho.org",
      "reliability": "high"
```

---

## okb

**名称**: OKB (OKB)
**类别**: cex_token
**置信度**: low

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "N/A",
    "fee_switch_details": "CEX 收入不直接链上分配",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "ACTIVE",
    "burn_details": "30% 平台收入用于季度回购销毁",
    "primary_value_accrual": "回购销毁 - 季度用 30% 收入回购销毁 OKB"
  },
  "market_data": {
    "price_usd": 71.07,
    "circulating_supply": 21000000,
    "circulating_market_cap": 1503276222,
    "snapshot_date": "2026-02-05",
    "data_source": "CoinGecko / Etherscan"
```

### 分析师备注（摘要）
【2026-02-05 初步调研】

## OKB TEV 评估

### 已知机制
1. **季度回购销毁**：OKX 用 30% 平台收入回购销毁 OKB
2. **X Layer Gas**：作为 L2 原生 token，gas 费用创造额外需求

### 数据限制
1. ❌ OKX 不公开财务数据
2. ❌ 季度销毁金额需要从公告整理
3. ⚠️ 无法精确计算 TEV yield

### 供应量特点
- 流通供应量固定在 ~21M OKB
- 总供应量 ~300M，大部分锁定/未流通

### 与 BNB 的区别
- BNB...

---

## pancakeswap

**名称**: PancakeSwap (CAKE)
**类别**: dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "veCAKE 已于 2025-04-23 结束，现全部回购销毁",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "ACTIVE",
    "primary_value_accrual": "回购销毁 - 协议收入 15% 用于 CAKE 回购销毁（veCAKE 分红已结束）"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "PancakeSwap Docs",
      "type": "documentation",
      "url": "https://docs.pancakeswap.finance",
      "reliability": "high"
```

---

## pendle

**名称**: Pendle (PENDLE)
**类别**: yield
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "80% 协议收入回购并分配给 sPENDLE 持有者（原 vePENDLE 升级）",
    "buybacks": "ACTIVE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "回购+分红 - 80% 协议收入转化为 PENDLE 回购，分配给 sPENDLE 持有者"
  },
  "ve_token": {
    "name": "vePENDLE",
    "lock_contract": "0x4f30A9D41B80ecC5B94306AB4364951AE3170210",
    "max_lock_period": "2 years",
    "benefits": ["协议收入分成", "投票权", "LP 加速"]
  },
  "confidence": "high",
```

---

## radiant

**名称**: Radiant Capital (RDNT)
**类别**: lending
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "60% 平台费用分配给 dLP lockers，以蓝筹资产支付",
    "buybacks": "NONE",
    "dividends": "ACTIVE",
    "burns": "NONE",
    "primary_value_accrual": "Fee Sharing - 锁定 dLP 获得 60% 平台收入，以 BTC/ETH/USDC 等支付"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "Radiant Documentation",
      "type": "documentation",
      "url": "https://docs.radiant.capital",
      "reliability": "high"
```

---

## sky

**名称**: Sky (MakerDAO) (MKR)
**类别**: cdp
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "70% 协议盈余用于 MKR 回购销毁",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "ACTIVE",
    "primary_value_accrual": "回购销毁 - Smart Burn Engine 自动使用协议盈余回购并销毁 MKR"
  },
  "confidence": "high",
  "data_sources": [
    {
      "name": "MakerDAO Forum",
      "type": "governance",
      "url": "https://forum.makerdao.com",
      "reliability": "high"
```

---

## spark

**名称**: Spark (SPK)
**类别**: lending
**置信度**: medium

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "OFF",
    "fee_switch_details": "SPK 代币刚启动，收入流向 Sky DAO",
    "buybacks": "NONE",
    "dividends": "NONE",
    "burns": "NONE",
    "primary_value_accrual": "治理代币 - SPK 用于 Spark SubDAO 治理，收入目前流向 Sky 主 DAO"
  },
  "confidence": "medium",
  "data_sources": [
    {
      "name": "Spark Finance",
      "type": "documentation",
      "url": "https://spark.fi",
      "reliability": "high"
```

---

## uniswap

**名称**: Uniswap (UNI)
**类别**: dex
**置信度**: high

### TEV 摘要
```json
  "tev_summary": {
    "fee_switch": "ON",
    "fee_switch_details": "2025-12-28 通过 UNIfication 提案开启",
    "buybacks": "ACTIVE",
    "dividends": "NONE",
    "burns": "ACTIVE",
    "burn_mechanism": "Firepit 合约 → 0xdead 地址",
    "primary_value_accrual": "多源 UNI 销毁 - 协议费 + Sequencer 收入 + PFDA + Aggregator hooks"
  },
  "market_data": {
    "price_usd": 3.61,
    "circulating_supply": 634247278,
    "circulating_market_cap": 2292835462,
    "total_supply": 1000000000,
    "holders": 387973,
```

### 分析师备注（摘要）
【2026-02-05 调研更新】

1. UNIfication 提案已通过执行，fee switch 于 2025-12-28 开启

2. 销毁机制：
   - TokenJar 收集所有链上的协议费用
   - Firepit 合约执行销毁（发送至 0xdead）
   - Mainnet Firepit: 0x0D5Cd355e2aBEB8fb1552F56c965B867346d6721
   - 阈值：每次 release 需 2000 UNI

3. 收入来源（已启用）:
   - v2 协议费: 0.05%（已启用）
   - v3 协议费: 1/4~1/6 of LP fee（部分池已启用）
   - Unichain sequenc...

---

