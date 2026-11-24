#!/usr/bin/env python3
"""回归：AHR999 3D 公式与治理状态映射。不访问网络。"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ahr999_3d_known_row():
    ind = load("fetch_indicators", "fetch-indicators.py")
    # 2026-03-28 已有行：close 66082, cost 91531.66, fitted_v2 116470.5, ahr999_3d 0.4096
    fitted = ind.fitted_price_v2("2026-03-28")
    assert fitted == 116470.5, fitted
    got = ind.ahr999_3d_of(66082, 91531.66, fitted)
    assert got == 0.4096, got


def test_snapshot_closed_is_not_passed():
    gov = load("update_governance_status", "update-governance-status.py")
    assert gov.map_snapshot_status("active") == "active"
    assert gov.map_snapshot_status("pending") == "active"
    assert gov.map_snapshot_status("closed") == "closed"


if __name__ == "__main__":
    test_ahr999_3d_known_row()
    test_snapshot_closed_is_not_passed()
    print("ok")
