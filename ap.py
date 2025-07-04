#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ap.py —— 补丁应用模块：
提供 apply_patch_to_repo(repo_dir: Path, patch_content: str, env_dir: Path, reverse: bool=False) 函数，
在指定的本地仓库目录 repo_dir 中依次尝试应用给定的补丁内容，并在函数内部打印中文提示。

函数接口：
    apply_patch_to_repo(repo_dir, patch_content, env_dir, reverse=False) -> bool

参数：
    repo_dir (Path)      : 本地仓库根目录
    patch_content (str)  : 补丁文本内容
    env_dir (Path)       : 虚拟环境路径（由 uv_env 返回的完整路径）
    reverse (bool)       : 是否反向应用补丁（用于还原或撤销）

功能：
    - 将 patch_content 写入临时文件
    - 依次尝试多种补丁应用命令
    - 成功时打印“补丁应用成功”或“补丁还原成功”，并返回 True
    - 全部失败后打印“补丁应用失败”，并返回 False

使用示例：
    success = apply_patch_to_repo(Path('/path/repo'), patch_str, Path('env/myenv'))

注意：该函数会在临时文件中写入 patch_content，并调用 shell 执行 git apply 或 patch。
"""
from pathlib import Path
import subprocess
import tempfile

# 可尝试的命令列表
GIT_APPLY_COMMANDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i"
]

def apply_patch_to_repo(repo_dir: Path, patch_content: str, env_dir: Path, reverse: bool = False) -> bool:
    """
    在 repo_dir 中依次尝试使用多种命令应用补丁。
    成功则打印中文提示并返回 True，否则打印失败提示并返回 False。
    
    :param repo_dir: 仓库路径
    :param patch_content: 补丁内容
    :param env_dir: 虚拟环境路径
    :param reverse: 是否反向应用补丁（默认 False）
    :return: 是否成功应用补丁
    """
    print(f"正在应用补丁：{patch_content[:50]}...")  # 打印补丁的前50个字符以便调试
    repo_dir = Path(repo_dir)
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"仓库目录未找到: {repo_dir}")

    # 确保虚拟环境的 activate 脚本存在
    activate_script = env_dir / "bin" / "activate"
    if not activate_script.exists():
        raise FileNotFoundError(f"虚拟环境的激活脚本未找到: {activate_script}")

    # 写入临时补丁文件
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.diff') as tf:
        tf.write(patch_content)
        temp_file = Path(tf.name)

    try:
        # 依次尝试应用补丁
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
            else:
                # 打印错误信息
                print(f"补丁应用失败，错误信息：\n{result.stderr}")
                print(f"补丁应用失败：{result.stdout}")

    finally:
        # 清理临时文件
        try:
            temp_file.unlink()
        except Exception:
            pass

    print("补丁应用失败：所有尝试均未成功。")
    return False



# 脚本独立调用支持
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='应用或还原补丁到本地仓库')
    parser.add_argument('--repo_dir',   required=True, type=Path, help='本地仓库目录')
    parser.add_argument('--patch_file', required=True, type=Path, help='补丁文件路径')
    parser.add_argument('--env_dir',    required=True, type=Path, help='虚拟环境路径')
    parser.add_argument('--reverse',    action='store_true', help='是否反向应用')
    args = parser.parse_args()
    patch_text = args.patch_file.read_text(encoding='utf-8')
    ok = apply_patch_to_repo(args.repo_dir, patch_text, args.env_dir, reverse=args.reverse)
    exit(0 if ok else 1)
