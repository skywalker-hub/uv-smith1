#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uv_env.py —— 环境准备模块：
提供 setup_environment(repo_dir: Path, uv_env_name: str) 函数，
在指定基础目录下创建并配置 uv 虚拟环境，并从指定依赖文件安装。

请在脚本顶部定义以下配置：
    ENV_BASE_DIR   = Path('/path/to/envs')
    REQ_FILE_PATH  = Path('/path/to/requirements.txt')

接口：
    setup_environment(repo_dir, uv_env_name)
    - repo_dir    (Path): 目标仓库根目录（仅用于日志或将来扩展）
    - uv_env_name (str): 虚拟环境名称，将作为子目录创建在 ENV_BASE_DIR 下

返回：
    env_path (Path): 创建的虚拟环境完整路径

示例用法：
    # 修改顶部配置后：
    env = setup_environment(Path('/path/to/repo'), 'myenv')
"""
from pathlib import Path
import subprocess
import sys

# -------- 用户可修改配置 --------
ENV_BASE_DIR  = Path('/path/to/envs')
REQ_FILE_PATH = Path('/path/to/requirements.txt')
# ----------------------------------


def setup_environment(repo_dir: Path, uv_env_name: str) -> Path:
    """
    在 ENV_BASE_DIR 下创建名为 uv_env_name 的 uv 虚拟环境，
    并使用 REQ_FILE_PATH 安装依赖。如果依赖文件不存在，
    将至少安装 pytest。
    """
    # 确保基础路径存在
    ENV_BASE_DIR.mkdir(parents=True, exist_ok=True)

    # 虚拟环境路径
    env_path = ENV_BASE_DIR / uv_env_name

    # 1. 创建虚拟环境
    try:
        subprocess.run(["uv", "venv", str(env_path)], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create uv environment at {env_path}: {e}")

    # 2. 安装依赖
    try:
        if REQ_FILE_PATH.exists():
            subprocess.run(["uv", "pip", "install", "-r", str(REQ_FILE_PATH)], check=True)
        else:
            subprocess.run(["uv", "pip", "install", "pytest"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install dependencies from {REQ_FILE_PATH}: {e}")

    return env_path


# 脚本测试支持
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="创建 uv 虚拟环境并安装依赖")
    parser.add_argument('--repo_dir', required=True, type=Path,
                        help='本地仓库根目录（仅用于日志）')
    parser.add_argument('--uv_env', default='env', type=str,
                        help='虚拟环境名称')
    args = parser.parse_args()
    try:
        env_dir = setup_environment(args.repo_dir, args.uv_env)
        print(f"Environment created at: {env_dir}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
