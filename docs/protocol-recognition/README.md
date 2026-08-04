# 协议口径判定书（内部文档库）

> **内部资料，不对外展示**。这里每个协议一份「口径判定书」，是接管的 Agent 快速上手手册——
> 理解每个协议「收入 → 股东回报」如何判定、数据从哪来、口径边界在哪。
>
> 这些口径是**逐一人工抠出来的最有价值的信息**，必须保留，但不向用户展示。

## 文档列表（27 协议）

| 协议 | 文档 | 实体类型 | 股东回报率 | 核心机制 |
|---|---|---|---|---|
| BNB | [bnb.md](bnb.md) | 平台币 | 12.46% | 打新+质押+销毁 |
| MNT | [mnt.md](mnt.md) | 平台币 | 5.0% | 质押收益 |
| Aster | [aster.md](aster.md) | 应用型 | 1.46% | 99% 手续费→veASTER |
| BGB | [bgb.md](bgb.md) | 平台币 | 27.54% | 季度 20% 回购销毁 |
| OKB | [okb.md](okb.md) | 平台币 | 5.2% | OKX Earn 质押 |
| Aave | [aave.md](aave.md) | 应用型 | 1.67% | 年度回购 $30M |
| Sky | [sky.md](sky.md) | 应用型 | 4.30% | Elixir 真燃烧 |
| Uniswap | [uniswap.md](uniswap.md) | 应用型 | 0.72% | Firepit 销毁 |
| Hyperliquid | [hyperliquid.md](hyperliquid.md) | 应用型 | 10.39% | 手续费销毁 |
| Pendle | [pendle.md](pendle.md) | 应用型 | 7.92% | sPENDLE 80% 分发 |
| Curve | [curve.md](curve.md) | 应用型 | 4.84% | veCRV 分红（净利负） |
| dYdX | [dydx.md](dydx.md) | 应用型 | 1.36% | 回购质押非销毁 |
| GMX | [gmx.md](gmx.md) | 应用型 | 0% | 锁定至 $90 |
| PancakeSwap | [pancakeswap.md](pancakeswap.md) | 应用型 | 12.93% | 净通缩回购销毁 |
| Maple | [maple.md](maple.md) | 应用型 | 0.85% | MIP-021 阶梯 |
| ether.fi | [etherfi.md](etherfi.md) | 应用型 | 4.29% | 双引擎→sETHFI |
| Ethena | [ethena.md](ethena.md) | 应用型 | 0% | 费用开关前 |
| JustLend | [justlend.md](justlend.md) | 应用型 | 0% | 做账式销毁 |
| Lido | [lido.md](lido.md) | 治理代币 | 0% | 利润照算 |
| EigenLayer | [eigenlayer.md](eigenlayer.md) | 治理代币 | 0% | 利润照算 |
| Compound | [compound.md](compound.md) | 治理代币 | 0% | 利润照算 |
| Morpho | [morpho.md](morpho.md) | 治理代币 | 0% | 利润照算 |
| Spark | [spark.md](spark.md) | 治理代币 | 0% | 利润照算 |
| Kamino | [kamino.md](kamino.md) | 治理代币 | 0% | 利润照算 |
| Jito | [jito.md](jito.md) | 治理代币 | 0% | 利润照算 |
| Fluid | [fluid.md](fluid.md) | 应用型 | 5.15% | 35% 回购 reserve |
| LayerZero | [layerzero.md](layerzero.md) | 应用型 | 0.30% | Stargate 回购+稀释 |

## 文档结构（模板）

每份文档 7 节：协议档案 / 收入判定 / 股东回报拆分 / adapter 计算逻辑 / 数据管道 / 注意点 / 出处。
模板见 [_template.md](_template.md)。

## 维护约定

- **新增/修改协议**：先改判定书总表 `docs/protocol-revenue-recognition.md`，再同步本目录对应文档
- **口径变更**：由 Boss 拍板，文档头部记录「最近更新」日期
- **数据源铁律**：链上 > 官方治理 > 估算 > DefiLlama（每个协议机制独立，不可套通用公式）
