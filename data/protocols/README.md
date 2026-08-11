# DeFi TEV Protocol Research

Top 20 DeFi protocols by TVL, analyzed for Token Empowerment Value (TEV) mechanisms.

## Summary

| # | Protocol | Ticker | TVL | TEV Status | Primary Mechanism |
|---|----------|--------|-----|------------|-------------------|
| 1 | Aave V3 | AAVE | $29.6B | ✅ ACTIVE | $50M annual buyback + Safety Module |
| 2 | Lido | LDO | $22.7B | ❌ NONE | Governance only, fee switch OFF |
| 3 | EigenLayer | EIGEN | $10.8B | ❌ NONE | Governance only, fee switch OFF |
| 5 | Ethena | ENA | $6.5B | ⚠️ PARTIAL | sENA staking rewards |
| 6 | Morpho | MORPHO | $6.2B | ❌ NONE | Governance only, no protocol fees |
| 7 | Sky | MKR | $5.2B | ✅ ACTIVE | 70% surplus → MKR buyback/burn |
| 8 | JustLend | JST | $3.3B | ⚠️ PARTIAL | JST staking rewards |
| 9 | Spark | SPK | $2.9B | ❌ NONE | New token, revenue flows to Sky DAO |
| 10 | Maple | SYRUP | $2.5B | ✅ ACTIVE | SYRUP staking fee share |
| 11 | Kamino | KMNO | $2.1B | ⚠️ PARTIAL | KMNO staking rewards |
| 12 | PancakeSwap | CAKE | $2.3B | ✅ ACTIVE | Buyback/burn + veCAKE revenue share |
| 13 | Curve | CRV | $1.9B | ✅ ACTIVE | 50% fees → veCRV holders |
| 14 | Jito | JTO | $1.5B | ❌ NONE | MEV to JitoSOL, JTO is governance |
| 15 | Compound | COMP | $1.6B | ❌ NONE | Governance only, fee switch OFF |
| 16 | GMX | GMX | $0.5B | ✅ ACTIVE | 30% fees → staked GMX |
| 17 | dYdX | DYDX | $0.2B | ✅ ACTIVE | 100% fees → DYDX stakers |
| 18 | Pendle | PENDLE | $0.3B | ✅ ACTIVE | 80% fees → vePENDLE |
| 19 | Radiant | RDNT | $3.9M | ✅ ACTIVE | 60% fees → dLP lockers |
| 20 | Uniswap | UNI | $4.5B | ❌ NONE | Governance only, fee switch OFF |

## TEV Status Legend

- ✅ **ACTIVE**: Protocol has active TEV mechanisms distributing value to token holders
- ⚠️ **PARTIAL**: Some TEV mechanisms exist but limited or unclear implementation  
- ❌ **NONE**: Token is governance-only, no revenue distribution to holders

## Key Insights

### Top TEV Protocols

1. **dYdX V4** - 100% of trading fees distributed to stakers (strongest TEV)
2. **Pendle** - 80% of protocol revenue to vePENDLE holders
3. **Sky** - 70% surplus to MKR buyback via Smart Burn Engine
4. **Radiant** - 60% platform fees to dLP lockers in blue-chip assets
5. **Curve** - 50% trading fees to veCRV holders
6. **Aave** - $50M annual buyback budget

### High TVL, No TEV

These protocols have significant TVL but NO value accrual to token holders:
- **Lido** ($22.7B TVL) - ~$800M annual revenue, 0% to LDO holders
- **Uniswap** ($4.5B TVL) - ~$1B annual fees, 0% to UNI holders
- **EigenLayer** ($10.8B TVL) - Fee switch OFF
- **Compound** ($1.6B TVL) - COMP is pure governance

### Emerging TEV

Protocols with new or developing TEV mechanisms:
- **Ethena** - sENA staking for protocol rewards
- **Kamino** - KMNO staking on Solana

## Data Sources

- [DefiLlama](https://defillama.com) - TVL, fees, revenue data
- [CoinGecko](https://coingecko.com) - Token prices, market caps
- Protocol governance forums and documentation
- On-chain contract verification

## File Structure

```
protocols/
├── aave/
│   └── config.json      # Protocol TEV configuration
├── curve/
│   └── config.json
├── ... (20 protocols)
└── README.md            # This file
```

## Last Updated

2026-02-02
