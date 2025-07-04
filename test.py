#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test.py —— 测试运行模块（增强版）：
支持运行指定测试用例 nodeid，并结构化返回测试是否符合预期结果，
附带日志记录与详细失败信息输出。
"""
from pathlib import Path
import subprocess
import sys


def _normalize_tests(tests) -> list[str]:
    """
    将 tests 参数转换为 nodeid 列表。
    支持：
      - 列表 ['a::b', 'c::d']
      - 字符串 "[a::b,c::d]" 或 "a::b,c::d"
    """
    if isinstance(tests, str):
        s = tests.strip()
        if s.startswith('[') and s.endswith(']'):
            s = s[1:-1]
        return [t.strip() for t in s.split(',') if t.strip()]
    elif isinstance(tests, (list, tuple)):
        return list(tests)
    else:
        raise ValueError(f"无法识别的 tests 类型：{type(tests)}")


def run_tests_on_repo(
    repo_dir: Path,
    tests,
    expect_fail: bool,
    env_dir: Path
) -> dict[str, bool]:
    """
    在 repo_dir 中逐个执行完整 nodeid 测试。
    expect_fail=True 时 returncode != 0 视为通过（失败符合预期）；
    expect_fail=False 时 returncode == 0 视为通过（通过符合预期）。
    同时输出日志到 .test_logs/{nodeid}.log
    """
    repo_dir = Path(repo_dir)
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"❌ 仓库目录未找到: {repo_dir}")
    
    if not env_dir.exists():
        raise FileNotFoundError(f"❌ 虚拟环境未找到: {env_dir}")

    log_dir = repo_dir / ".test_logs"
    log_dir.mkdir(exist_ok=True)

    results: dict[str, bool] = {}
    for nodeid in _normalize_tests(tests):
        # 生成日志路径并确保目录存在
        log_file = log_dir / f"{nodeid.replace('::', '__').replace('[','_').replace(']','')}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)  # 创建日志目录（如果不存在）

        cmd = f"source ~/autodl-tmp/uv-smith1/{env_dir}/bin/activate && pytest -q --disable-warnings --maxfail=1 {nodeid}"
        print(f"🎯 执行命令：{cmd}")  # 显示当前运行的命令

        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(repo_dir),
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 如果测试期望失败时，返回码不为 0 时算通过
            passed = (proc.returncode != 0) if expect_fail else (proc.returncode == 0)
            status = '失败' if expect_fail else '通过'

            # 打印结果提示
            if passed:
                print(f"✅ 测试 '{nodeid}' 符合预期（{status}）。")
            else:
                print(f"❌ 测试 '{nodeid}' 未达预期（未{status}）。")
                print(f"   ↪ 错误码: {proc.returncode}")
                print(f"   ↪ stderr: {proc.stderr.strip()[:300]}{'...' if len(proc.stderr) > 300 else ''}")

            # 保存日志
            with log_file.open("w", encoding="utf-8") as f:
                f.write(f"=== COMMAND ===\n{cmd}\n\n")
                f.write(f"=== STDOUT ===\n{proc.stdout}\n\n")
                f.write(f"=== STDERR ===\n{proc.stderr}\n")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 命令执行失败：{e}")
            with log_file.open("w", encoding="utf-8") as f:
                f.write(f"=== ERROR ===\n{e}\n")
        
        # 如果没有出错，记录测试结果
        results[nodeid] = passed

    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='在本地仓库中运行指定测试')
    parser.add_argument('--repo_dir',    required=True, type=Path, help='本地仓库目录')
    parser.add_argument('--tests',       required=True, help='测试用例 nodeid 列表或逗号分隔字符串')
    parser.add_argument('--expect_fail', action='store_true', help='期待测试失败')
    parser.add_argument('--env_dir',     required=True, type=Path, help='虚拟环境路径')
    args = parser.parse_args()

    try:
        res = run_tests_on_repo(
            args.repo_dir,
            args.tests,
            expect_fail=args.expect_fail,
            env_dir=args.env_dir
        )
        print("\n🎯 测试结果：")
        print(res)
    except Exception as e:
        print(f"❌ 运行时发生错误: {e}", file=sys.stderr)
        sys.exit(1)
