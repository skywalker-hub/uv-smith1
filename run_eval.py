#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py — 主控程序：
负责整个本地验证流程的编排，依次调用以下模块：
  1. uv_env.py —— 环境准备
  2. ap.py     —— 补丁应用
  3. test.py   —— 测试运行与验证

脚本顶部通过常量配置相对路径，无需命令行参数。
"""
from pathlib import Path
import json
import sys
import subprocess

# 导入模块化脚本
from uv_env import setup_environment
from ap import apply_patch_to_repo
from test import run_tests_on_repo

# ------------------ 配置区域（相对项目根目录） ------------------
DATASET_PATH   = Path('data/swe-smith.jsonl')
REPOS_ROOT     = Path('repos')
INSTANCE_ID    = 'scanny__python-pptx.278b47b1.combine_file__00zilcc6'
FIX_PATCH_FILE = Path('fixes/your_fix.patch')
UV_ENV_NAME    = 'pptx'
# ----------------------------------------------------------------

def load_instance(dataset_path: Path, instance_id: str) -> dict:
    """从 JSONL 数据集中加载对应 instance_id 的记录"""
    if not dataset_path.exists():
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}")
    with dataset_path.open(encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if item.get('instance_id') == instance_id:
                return item
    raise KeyError(f'Instance {instance_id} not found')

def extract_base_commit(instance_id: str) -> str:
    """
    从 instance_id 中提取 base_commit 哈希部分
    格式为：repo_name.commit_hash，例如：'278b47b1'
    """
    return instance_id.split('.')[1]

def switch_to_commit(repo_dir: Path, base_commit: str) -> None:
    """
    切换到指定的 commit
    """
    print(f"切换到 base commit: {base_commit}")
    subprocess.run(["git", "reset", "--hard"], cwd=repo_dir, check=True)  # 重置当前工作区
    subprocess.run(["git", "checkout", base_commit], cwd=repo_dir, check=True)  # 切换到 commit

def main():
    try:
        # 1. 加载任务实例
        item = load_instance(DATASET_PATH, INSTANCE_ID)

        # 2. 提取 base_commit
        base_commit = extract_base_commit(INSTANCE_ID)
        print(f"提取的 base_commit: {base_commit}")

        # 3. 确定仓库路径并创建虚拟环境
        repo_path = item['repo'].removeprefix('swesmith/')
        repo_dir = REPOS_ROOT / repo_path
        env_dir = setup_environment(UV_ENV_NAME)

        # 4. 切换到指定的 commit
        switch_to_commit(repo_dir, base_commit)

        # 5. 注入错误补丁
        error_patch = item['patch']
        if not apply_patch_to_repo(repo_dir, error_patch, env_dir=env_dir, reverse=False):
            raise RuntimeError('注入错误补丁失败')

        # 6. 首次验证：FAIL_TO_PASS 应失败，PASS_TO_PASS 应通过
        fail_tests = item.get('FAIL_TO_PASS', [])
        pass_tests = item.get('PASS_TO_PASS', [])
        initial_fail = run_tests_on_repo(repo_dir, fail_tests, expect_fail=True, env_dir=env_dir)
        initial_pass = run_tests_on_repo(repo_dir, pass_tests, expect_fail=False, env_dir=env_dir)

        # 7. 应用用户修复补丁
        fix_patch = FIX_PATCH_FILE.read_text(encoding='utf-8')
        if not apply_patch_to_repo(repo_dir, fix_patch, env_dir=env_dir, reverse=False):
            raise RuntimeError('应用修复补丁失败')

        # 8. 复测 FAIL_TO_PASS
        repair_results = run_tests_on_repo(repo_dir, fail_tests, expect_fail=False, env_dir=env_dir)

        # 9. 汇总并输出
        summary = {
            'initial_fail': initial_fail,
            'initial_pass': initial_pass,
            'repair': repair_results
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        # 10. 退出码判断
        ok_initial = all(initial_fail[t] for t in fail_tests) and all(initial_pass[t] for t in pass_tests)
        ok_repair  = all(repair_results[t] for t in fail_tests)
        sys.exit(0 if (ok_initial and ok_repair) else 1)

        # 11. 恢复仓库到初始 commit
        subprocess.run(["git", "reset", "--hard", current_commit], cwd=repo_dir, check=True)

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
