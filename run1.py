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
REPOS_ROOT     = Path('repo')
INSTANCE_ID    = 'scanny__python-pptx.278b47b1.combine_file__00zilcc6'
#FIX_PATCH_FILE = Path('fixes/your_fix.patch')
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

def extract_repo(instance_id: str) -> str:
    """
    从 instance_id 中提取 repo 名称
    格式为：repo_name.commit_hash，例如：'python-pptx'
    """
    repo_full = instance_id.split('.')[0]
    return repo_full.split("__")[-1]

def switch_to_commit(repo_dir: Path, base_commit: str) -> None:
    """
    切换到指定的 commit，并暂存当前更改以防丢失
    """
    print(f"切换到 base commit: {base_commit}")

    # 1. 暂存当前工作区的更改，包括未追踪的文件
    subprocess.run(["git", "stash", "--include-untracked"], cwd=repo_dir, check=False)

    # 2. 重置当前工作区
    subprocess.run(["git", "reset", "--hard", base_commit], cwd=repo_dir, check=True)

    # 3. 切换到指定的 commit
    subprocess.run(["git", "checkout", base_commit], cwd=repo_dir, check=True)

    print(f"仓库已切换到 commit: {base_commit}")

    # 4. 恢复暂存的更改
    subprocess.run(["git", "stash", "pop"], cwd=repo_dir, check=False)


def main():
    try:
        # 1. 加载任务实例
        item = load_instance(DATASET_PATH, INSTANCE_ID)

        # 2. 提取 repo 和 base_commit
        repo_name = extract_repo(INSTANCE_ID)
        base_commit = extract_base_commit(INSTANCE_ID)
        print(f"提取的 repo: {repo_name}")
        print(f"提取的 base_commit: {base_commit}")

        # 3. 确定仓库路径
        repo_dir = REPOS_ROOT / repo_name

        # 4. 切换到指定的 commit（确保是基于正确代码版本）
        switch_to_commit(repo_dir, base_commit)

        # 5. 创建虚拟环境
        env_dir = setup_environment(UV_ENV_NAME)

        # 6. 注入错误补丁
        error_patch = item['patch']
        if not apply_patch_to_repo(repo_dir, error_patch, env_dir=env_dir, reverse=False):
            raise RuntimeError('注入错误补丁失败')

        print("错误补丁已成功应用，测试部分暂未执行。")

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
