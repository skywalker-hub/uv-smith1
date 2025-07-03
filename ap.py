#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ap.py —— 补丁应用模块：
提供 apply_patch_to_repo(repo_dir: Path, patch_content: str, uv_env_name: str, reverse: bool=False) 函数，
在指定的本地仓库目录 repo_dir 中依次尝试应用给定的补丁内容，并在函数内部打印中文提示。

函数接口：
    apply_patch_to_repo(repo_dir, patch_content, uv_env_name, reverse=False) -> bool

参数：
    repo_dir (Path)      : 本地仓库根目录
    patch_content (str)   : 补丁文本内容
    uv_env_name (str)     : 虚拟环境名称（对应 uv_env.py 中 ENV_BASE_DIR 下的子目录）
    reverse (bool)        : 是否反向应用补丁（用于还原或撤销）

功能：
    - 将 patch_content 写入临时文件
    - 依次尝试多种补丁应用命令
    - 成功时打印“补丁应用成功”或“补丁还原成功”，并返回 True
    - 全部失败后打印“补丁应用失败”，并返回 False

使用示例：
    success = apply_patch_to_repo(Path('/path/repo'), patch_str, 'myenv')

注意：该函数会在临时文件中写入 patch_content，并调用 shell 执行 git apply 或 patch。
"""
from pathlib import Path
import subprocess
import tempfile

# 从 uv_env.py 调用 ENV_BASE_DIR
try:
    from uv_env import ENV_BASE_DIR
except ImportError:
    ENV_BASE_DIR = Path.home() / '.uv_envs'

# 可尝试的命令列表
GIT_APPLY_COMMANDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i"
]


def apply_patch_to_repo(
    repo_dir: Path,
    patch_content: str,
    uv_env_name: str,
    reverse: bool = False
) -> bool:
    """
    在 repo_dir 中依次尝试使用多种命令应用补丁。
    成功则打印中文提示并返回 True，否则打印失败提示并返回 False。
    """
    repo_dir = Path(repo_dir)
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"仓库目录未找到: {repo_dir}")

    # 虚拟环境路径
    env_dir = Path(ENV_BASE_DIR) / uv_env_name
    if not env_dir.exists():
        raise FileNotFoundError(f"虚拟环境未找到: {env_dir}")

    # 写入临时补丁文件
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.diff') as tf:
        tf.write(patch_content)
        temp_file = Path(tf.name)

    try:
        # 依次尝试应用
        for cmd in GIT_APPLY_COMMANDS:
            full_cmd = f"source {env_dir}/bin/activate && {cmd} {temp_file}"
            if reverse:
                full_cmd += " --reverse"
            result = subprocess.run(
                full_cmd,
                shell=True,
                cwd=str(repo_dir),
                executable='/bin/bash',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                action = '还原' if reverse else '应用'
                print(f"补丁{action}成功：{cmd}")
                return True
        # 全部命令尝试结束，判断为失败
        print("补丁应用失败：所有尝试均未成功。")
        return False
    finally:
        # 清理临时文件
        try:
            temp_file.unlink()
        except Exception:
            pass


# 脚本独立调用支持
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='应用或还原补丁到本地仓库')
    parser.add_argument('--repo_dir',   required=True, type=Path, help='本地仓库目录')
    parser.add_argument('--patch_file', required=True, type=Path, help='补丁文件路径')
    parser.add_argument('--uv_env',     required=True, type=str, help='虚拟环境名称')
    parser.add_argument('--reverse',    action='store_true', help='是否反向应用')
    args = parser.parse_args()
    patch_text = args.patch_file.read_text(encoding='utf-8')
    ok = apply_patch_to_repo(args.repo_dir, patch_text, args.uv_env, reverse=args.reverse)
    exit(0 if ok else 1)
