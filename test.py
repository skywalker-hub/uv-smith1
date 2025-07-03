#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test.py —— 测试运行模块：
提供 run_tests_on_repo(repo_dir: Path, tests, expect_fail: bool, env_dir: Path) 函数，
在指定的本地仓库目录中调用 pytest 逐条运行完整 nodeid 测试，并根据 expect_fail 判断实际结果。

函数接口：
    run_tests_on_repo(repo_dir, tests, expect_fail, env_dir) -> dict[str, bool]

参数：
    repo_dir    (Path)      : 本地仓库根目录
    tests       (list[str] 或 str) : 完整 pytest nodeid 列表或逗号分隔字符串
    expect_fail (bool)      : True 时期待测试失败（returncode != 0）才算通过；
                              False 时期待测试通过（returncode == 0）才算通过
    env_dir     (Path)      : uv 虚拟环境的完整路径（由主控脚本传入）

返回：
    Dict[str,bool] — 每个测试用例是否符合预期的映射

功能：
    - 解析 tests 参数，支持字符串和列表两种格式
    - 激活虚拟环境
    - 对每个 nodeid 执行 pytest <nodeid>，保证精确运行
    - 打印中文提示，例如“测试 {nodeid} 符合预期”或“测试 {nodeid} 未达预期”
    - 返回包含所有测试结果的字典
"""
from pathlib import Path
import subprocess


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
    """
    repo_dir = Path(repo_dir)
    if not repo_dir.is_dir():
        raise FileNotFoundError(f"仓库目录未找到: {repo_dir}")

    if not env_dir.exists():
        raise FileNotFoundError(f"虚拟环境未找到: {env_dir}")

    results: dict[str, bool] = {}
    for nodeid in _normalize_tests(tests):
        cmd = f"source {env_dir}/bin/activate && pytest -q --disable-warnings --maxfail=1 {nodeid}"
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(repo_dir),
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        passed = (proc.returncode != 0) if expect_fail else (proc.returncode == 0)
        status = '失败' if expect_fail else '通过'
        if passed:
            print(f"测试 '{nodeid}' 符合预期（{status}）。")
        else:
            print(f"测试 '{nodeid}' 未达预期（未{status}）。")
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
    res = run_tests_on_repo(
        args.repo_dir,
        args.tests,
        expect_fail=args.expect_fail,
        env_dir=args.env_dir
    )
    print(res)
