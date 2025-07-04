#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py — 主控程序（运行 FAIL_TO_PASS + PASS_TO_PASS 测试）
"""
from pathlib import Path
import json
import sys
import subprocess

from uv_env import setup_environment
from ap import apply_patch_to_repo
from test import run_tests_on_repo

# ------------------ 配置区域 ------------------
DATASET_PATH   = Path('data/swe-smith.jsonl')
REPOS_ROOT     = Path('repo')
INSTANCE_ID    = 'scanny__python-pptx.278b47b1.combine_file__00zilcc6'
UV_ENV_NAME    = 'pptx'
# ------------------------------------------------

def load_instance(dataset_path: Path, instance_id: str) -> dict:
    if not dataset_path.exists():
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}")
    with dataset_path.open(encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            if item.get('instance_id') == instance_id:
                return item
    raise KeyError(f'Instance {instance_id} not found')

def extract_base_commit(instance_id: str) -> str:
    return instance_id.split('.')[1]

def extract_repo(instance_id: str) -> str:
    repo_full = instance_id.split('.')[0]
    return repo_full.split("__")[-1]

def switch_to_commit(repo_dir: Path, base_commit: str) -> None:
    print(f"切换到 base commit: {base_commit}")
    subprocess.run(["git", "stash", "--include-untracked"], cwd=repo_dir, check=False)
    subprocess.run(["git", "reset", "--hard", base_commit], cwd=repo_dir, check=True)
    subprocess.run(["git", "checkout", base_commit], cwd=repo_dir, check=True)
    print(f"仓库已切换到 commit: {base_commit}")
    subprocess.run(["git", "stash", "pop"], cwd=repo_dir, check=False)

def get_current_commit(repo_dir: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def restore_to_commit(repo_dir: Path, commit: str) -> None:
    print(f"恢复仓库到初始 commit: {commit}")
    subprocess.run(["git", "reset", "--hard", commit], cwd=repo_dir, check=True)
    subprocess.run(["git", "checkout", commit], cwd=repo_dir, check=True)

def parse_test_list(raw) -> list[str]:
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith('[') and s.endswith(']'):
            s = s[1:-1]
        return [t.strip() for t in s.split(',') if t.strip()]
    elif isinstance(raw, (list, tuple)):
        return list(raw)
    return []

def main():
    repo_dir = None
    try:
        # 1. 加载任务实例
        item = load_instance(DATASET_PATH, INSTANCE_ID)

        # 2. 提取 repo 和 base_commit
        repo_name = extract_repo(INSTANCE_ID)
        base_commit = extract_base_commit(INSTANCE_ID)
        print(f"提取的 repo: {repo_name}")
        print(f"提取的 base_commit: {base_commit}")

        # 3. 仓库路径
        repo_dir = REPOS_ROOT / repo_name

        # 4. 记录当前 HEAD
        original_commit = get_current_commit(repo_dir)

        # 5. 切换到 base commit
        switch_to_commit(repo_dir, base_commit)

        # 6. 创建虚拟环境
        env_dir = setup_environment(UV_ENV_NAME)

        # 7. 注入错误补丁
        error_patch = item['patch']
        if not apply_patch_to_repo(repo_dir, error_patch, env_dir, reverse=False):
            raise RuntimeError('注入错误补丁失败')
        print("✅ 错误补丁已成功应用。")

        # 8. 运行 FAIL_TO_PASS（应失败）
        fail_tests = parse_test_list(item.get('FAIL_TO_PASS', []))
        fail_results = run_tests_on_repo(repo_dir, fail_tests, expect_fail=True, env_dir=env_dir)

        # 9. 运行 PASS_TO_PASS（应通过）
        pass_tests = parse_test_list(item.get('PASS_TO_PASS', []))
        pass_tests = pass_tests[:10]  # ✅ 只取前 10 个
        pass_results = run_tests_on_repo(repo_dir, pass_tests, expect_fail=False, env_dir=env_dir)

        # 10. 输出结果
        summary = {
            "instance_id": INSTANCE_ID,
            "initial_fail": fail_results,
            "initial_pass": pass_results
        }

        print("\n🎯 测试结果汇总如下：")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        # 判断：fail 全部失败、pass 全部通过
        ok_fail = all(fail_results.get(t, False) for t in fail_tests)
        ok_pass = all(pass_results.get(t, False) for t in pass_tests)
        sys.exit(0 if (ok_fail and ok_pass) else 1)

    except Exception as e:
        print(f'❌ Error: {e}', file=sys.stderr)
        sys.exit(1)

    finally:
        if repo_dir is not None:
            try:
                restore_to_commit(repo_dir, original_commit)
                print("🧹 仓库恢复完成。")
            except Exception as e:
                print(f"⚠️ 仓库恢复失败：{e}", file=sys.stderr)

if __name__ == '__main__':
    main()
