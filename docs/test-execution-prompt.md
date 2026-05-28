# BatteryFold 全量开放测试 — Claude 执行 Prompt

## 执行指令

```
你是BatteryFold项目的QA工程师。执行全量自动化测试，修复所有失败，生成测试报告。

## 步骤

### 1. 环境准备
```bash
cd /path/to/Aphrodite-builder2
git pull origin main
```

### 2. Rust 测试 (L1)
```bash
cd src-rs
cargo test --release 2>&1
cd ..
```
- 记录 passed/failed/total
- 如有失败：读错误信息 → 修复源码 → 重新测试 → 直到0 failures

### 3. Rust CLI 验证 (L2)
```bash
cd src-rs && cargo build --release && cd ..
./src-rs/target/release/batteryfold --version   # 应输出 BatteryFold v1.0.0
./src-rs/target/release/batteryfold help         # 应输出完整帮助
./src-rs/target/release/batteryfold projects    # 应输出项目列表（可能为空）
```

### 4. Python 单元测试 (L3)
```bash
python3 test/test_python.py 2>&1
```
- 目标：24/24 passed
- 如有失败：分析错误 → 修复测试或源码 → 重新运行 → 直到全部通过

### 5. Python 工作流测试 (L4)
```bash
python3 test/test_workflows.py 2>&1
```
- 目标：9/9 passed
- 如有 yaml 导入失败：在 workflow 模块头部加 try/except
- 如有 quantum 导入失败：在 workflow 模块头部加 try/except

### 6. Python E2E 测试 (L5)
```bash
python3 test/test_e2e.py 2>&1
```
- 目标：5/5 passed

### 7. 生成测试报告

用以下格式输出最终报告：

```
══════════════════════════════════════════════════
  BatteryFold Test Report — [日期]
══════════════════════════════════════════════════

  Layer          Total  Pass  Fail  Skip  Time
  ──────────────────────────────────────────────
  L1 Rust Unit     X     X     0     0   Xs
  L2 Rust CLI      X     X     0     0   Xs
  L3 Python Unit   X     X     0     0   Xs
  L4 Workflow      X     X     0     0   Xs
  L5 E2E           X     X     0     0   Xs
  ──────────────────────────────────────────────
  TOTAL           XX    XX     0     0   Xs

  Result: ✓ ALL PASSED / ✗ N FAILURES
══════════════════════════════════════════════════
```

### 8. 如有修复
- 每个修复单独commit: `fix: [描述]`
- 所有修复完成后重新跑全量测试确认
- 最终commit: `test: all 42 tests passing`

### 9. 不可修复的问题
如果某个测试因环境问题无法通过（如缺ORCA二进制、缺PyTorch）：
- 标记为 SKIP 并说明原因
- 不算 FAIL

## 规则
- 修改源码而非跳过测试
- 每次 fix 后立即验证
- 全量通过后才输出最终报告
- 0 failures 是唯一可接受的输出
```

## 使用方法

1. 打开Claude Code
2. 进入项目目录: `cd /path/to/Aphrodite-builder2`
3. 粘贴上面的prompt
4. 等待Claude执行完毕
5. 检查最终报告
