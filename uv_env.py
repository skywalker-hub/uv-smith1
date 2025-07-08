#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uv_env.py —— 环境准备模块（健壮版）：
提供 setup_environment(uv_env_name: str) 函数，
在指定基础目录下创建并配置 uv 虚拟环境。
此版本包含健康检查与自我修复机制，确保 pip 一定被成功安装。

使用者需在脚本顶部定义以下配置：
    ENV_BASE_DIR   = Path('env/')
    REQ_FILE_PATH  = Path('requirements.txt')

接口：
    setup_environment(uv_env_name)
    - uv_env_name (str): 虚拟环境名称，将作为子目录创建在 ENV_BASE_DIR 下

返回：
    env_path (Path): 创建的虚拟环境完整路径

示例用法：
    env = setup_environment('myenv')
"""
from pathlib import Path
import subprocess
import sys

# -------- 用户可修改配置（使用项目内相对路径） --------
ENV_BASE_DIR  = Path('env')  # 虚拟环境所在目录
REQ_FILE_PATH = Path('requirements.txt')  # 项目内 requirements.txt 路径
# -------------------------------------------------------

def setup_environment(uv_env_name: str) -> Path:
    """
    在 ENV_BASE_DIR 下创建名为 uv_env_name 的 uv 虚拟环境，
    确保 pip 被正确安装，然后使用 REQ_FILE_PATH 安装依赖。
    """
    ENV_BASE_DIR.mkdir(parents=True, exist_ok=True)
    env_path = ENV_BASE_DIR / uv_env_name

    # 步骤 1: 创建或清理虚拟环境
    print(f"正在创建或清理虚拟环境: {env_path}")
    try:
        # 使用 --clear 选项确保环境是干净的
        subprocess.run(["uv", "venv", str(env_path), "--clear"], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"无法创建 uv 虚拟环境: {env_path}: {e}")

    # 步骤 2: 定位新环境的 Python 解释器
    target_python = env_path / "bin" / "python"
    if not target_python.is_file():
        raise FileNotFoundError(f"创建环境后，未找到 Python 解释器: {target_python}")

    # --- 核心改动：健康检查与自我修复机制 ---
    try:
        print("正在检查新环境中 pip 是否可用...")
        # 尝试用新环境的 python 运行 pip，如果失败，说明 pip 没被正确安装
        subprocess.run(
            [str(target_python), "-m", "pip", "--version"], 
            check=True, 
            capture_output=True  # 隐藏成功时的输出，保持日志整洁
        )
        print("✅ pip 已存在。")
    except subprocess.CalledProcessError:
        # 如果上面的命令失败 (pip 不存在), 则进入这个修复流程
        print(f"⚠️ 检测到环境 '{env_path.name}' 中缺少 pip，正在尝试手动修复...")
        try:
            # 使用标准的 ensurepip 模块来为这个环境强制安装 pip
            subprocess.run([str(target_python), "-m", "ensurepip", "--upgrade"], check=True)
            print("✅ 已成功手动安装 pip。")
        except subprocess.CalledProcessError as ensure_e:
            raise RuntimeError(f"在新环境中手动安装 pip 失败，环境已损坏，请检查系统配置: {ensure_e}")

    # 步骤 3: 在健康的环境中安装依赖
    try:
        # 确保 pytest 被安装
        print("正在安装 pytest...")
        subprocess.run([str(target_python), "-m", "pip", "install", "pytest"], check=True)

        if REQ_FILE_PATH.exists():
            print(f"正在从 {REQ_FILE_PATH} 安装依赖...")
            subprocess.run(
                [str(target_python), "-m", "pip", "install", "-r", str(REQ_FILE_PATH)],
                check=True
            )
            print("成功安装 requirements")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"在环境 '{env_path.name}' 中安装依赖失败: {e}")

    print(f"✅ 环境 '{env_path.name}' 已成功创建并配置完毕。")
    return env_path


# 测试脚本支持
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="创建并验证一个健壮的 uv 虚拟环境")
    parser.add_argument('--uv_env', default='my-robust-env', type=str,
                        help='要创建的虚拟环境名称')
    args = parser.parse_args()
    try:
        env_dir = setup_environment(args.uv_env)
        print(f"\nEnvironment ready at: {env_dir.resolve()}")
        print(f"To activate it, run: source {env_dir.resolve()}/bin/activate")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)