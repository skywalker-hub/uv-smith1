#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py — 主控程序：
负责整个本地验证流程的编排，依次调用以下模块：
  1. uv_env.py —— 环境准备
  2. ap.py     —— 补丁应用
  3. test.py   —— 测试运行与验证

直接在脚本顶部通过常量配置 paths，无需命令行参数。
"""
from pathlib import Path
import json
import sys

# 导入模块化脚本
from uv_env import setup_environment
from ap import apply_patch_to_repo
from test import run_tests_on_repo

# 配置区域：请根据本地环境修改
DATASET_PATH   = Path('/path/to/swe-smith.jsonl')
REPOS_ROOT     = Path('/path/to/repos')
INSTANCE_ID    = 'owner__repo.bugtype.hash'
FIX_PATCH_FILE = Path('/path/to/your_fix.patch')
UV_ENV_NAME    = 'myenv'
# ---------------------------------------------

def load_instance(dataset_path: Path, instance_id: str) -> dict:
    """从 JSONL 数据集中加载对应 instance_id 的记录"""
    with dataset_path.open(encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if item.get('instance_id') == instance_id:
                return item
    raise KeyError(f'Instance {instance_id} not found')


def main():
    try:
        # 1. 加载任务实例
        item = load_instance(DATASET_PATH, INSTANCE_ID)

        # 2. 确定仓库路径并创建虚拟环境
        repo_dir = REPOS_ROOT / item['repo'].replace('/', '__')
        env_dir = setup_environment(repo_dir, UV_ENV_NAME)

        # 3. 注入错误补丁，使原本通过的测试失败
        error_patch = item['patch']
        if not apply_patch_to_repo(repo_dir, error_patch, uv_env=UV_ENV_NAME, reverse=False):
            raise RuntimeError('Error patch apply failed')

        # 4. 首次验证：FAIL_TO_PASS 应失败，PASS_TO_PASS 应通过
        fail_tests = item.get('FAIL_TO_PASS', [])
        pass_tests = item.get('PASS_TO_PASS', [])
        initial_fail = run_tests_on_repo(repo_dir, fail_tests, expect_fail=True, uv_env=UV_ENV_NAME)
        initial_pass = run_tests_on_repo(repo_dir, pass_tests, expect_fail=False, uv_env=UV_ENV_NAME)

        # 5. 应用用户修复补丁（修复即会还原错误）
        fix_patch = FIX_PATCH_FILE.read_text(encoding='utf-8')
        if not apply_patch_to_repo(repo_dir, fix_patch, uv_env=UV_ENV_NAME, reverse=False):
            raise RuntimeError('Fix patch apply failed')

        # 6. 复测 FAIL_TO_PASS，期待全部恢复通过
        repair_results = run_tests_on_repo(repo_dir, fail_tests, expect_fail=False, uv_env=UV_ENV_NAME)

        # 7. 汇总并输出
        summary = {
            'initial_fail': initial_fail,
            'initial_pass': initial_pass,
            'repair': repair_results
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        # 8. 退出码判断
        ok_initial = all(initial_fail[t] for t in fail_tests) and all(initial_pass[t] for t in pass_tests)
        ok_repair  = all(repair_results[t] for t in fail_tests)
        sys.exit(0 if (ok_initial and ok_repair) else 1)

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
