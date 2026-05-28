# BatteryFold Test Plan

## 1. 测试分层

| Layer | 范围 | 数量 | 耗时 |
|-------|------|------|------|
| L1 Rust Unit | HNSW, Memory, SONA, Config, Project | ~15 | <5s |
| L2 Rust CLI | batteryfold binary commands | ~8 | <10s |
| L3 Python Unit | backends, synthesis, cell_design, bms, experimental, integration | ~25 | <30s |
| L4 Python Workflow | screening_pipeline, precision_ladder, planetary_adapter | ~8 | <15s |
| L5 E2E | 完整流程: molecule → quantum → synthesis → cell → BMS → report | ~5 | <30s |

**总计 ~61个测试用例, 全自动化执行 < 2分钟**

## 2. 测试环境要求

- Rust toolchain (1.93+)
- Python 3.10+
- 无需ORCA/RDKit/PySCF (测试不依赖外部二进制)
- 所有外部调用均mock

## 3. 通过标准

- 0 failures
- 0 errors
- 覆盖率 > 70% 核心逻辑
- 所有public API至少1个测试

## 4. 执行命令

```bash
# 全量测试
bash scripts/run_tests.sh

# 分层测试
bash scripts/run_tests.sh rust          # L1+L2
bash scripts/run_tests.sh python        # L3+L4
bash scripts/run_tests.sh e2e           # L5
bash scripts/run_tests.sh report        # 生成报告
```

## 5. 报告格式

```
══════════════════════════════════════════════════
  BatteryFold Test Report — 2026-05-28
══════════════════════════════════════════════════

  Layer          Total  Pass  Fail  Skip  Time
  ──────────────────────────────────────────────
  L1 Rust Unit     15    15     0     0   2.1s
  L2 Rust CLI       8     8     0     0   3.4s
  L3 Python Unit   25    25     0     0  12.3s
  L4 Workflow       8     8     0     0   8.7s
  L5 E2E            5     5     0     0  15.2s
  ──────────────────────────────────────────────
  TOTAL           61    61     0     0  41.7s

  Result: ✓ ALL PASSED
══════════════════════════════════════════════════
```
