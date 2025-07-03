#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_eval.py — 主控程序：
负责整个本地验证流程的编排，依次调用以下模块：
  1. uv_env.py —— 环境准备
  2. ap.py     —— 补丁应用

脚本顶部通过常量配置相对路径，无需命令行参数。
"""
from pathlib import Path
import json
import sys

# 导入模块化脚本
from uv_env import setup_environment
from ap import apply_patch_to_repo

# ------------------ 配置区域（相对项目根目录） ------------------
DATASET_PATH   = Path('data/swe-smith.jsonl')
REPOS_ROOT     = Path('./repo')
INSTANCE_ID    = 'scanny__python-pptx.278b47b1.combine_file__00zilcc6'
UV_ENV_NAME    = 'pptx'
# ----------------------------------------------------------------

# 尝试从本地加载数据集，若不存在则从 Hugging Face 下载并保存为本地 JSONL
from datasets import load_dataset

def ensure_local_dataset(path: Path) -> None:
    if not path.exists():
        print(f"未找到本地数据集，正在从 Hugging Face 下载 SWE-smith 并保存到 {path}...")
        ds = load_dataset("SWE-bench/SWE-smith", split="train")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for item in ds:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print("✅ 数据集下载完成。")

def load_instance(dataset_path: Path, instance_id: str) -> dict:
    """从 JSONL 数据集中加载对应 instance_id 的记录"""
    ensure_local_dataset(dataset_path)
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
        env_dir = setup_environment(UV_ENV_NAME)

        # 3. 注入错误补丁
        error_patch = item['patch']
        if not apply_patch_to_repo(repo_dir, error_patch, env_dir=env_dir, reverse=False):
            raise RuntimeError('注入错误补丁失败')

        print("✅ 错误补丁已成功应用，测试部分暂未执行。")

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
