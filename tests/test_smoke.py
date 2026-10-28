"""Check dependency imports, isolation, and the actual CLI contract."""

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from xiaoying_agent.cli import build_report


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module", ["openai", "pydantic", "dotenv", "pytest", "rich"])
def test_base_dependency_imports(module):
    importlib.import_module(module)


def test_virtual_environment_is_isolated():
    assert sys.prefix != sys.base_prefix


def test_report_validates_and_trims_message():
    assert build_report("  hello  ").message == "hello"


def test_cli_runs_offline_without_api_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Any unexpected network connection fails this subprocess immediately.
    script = '''
import socket
def deny_network(*args, **kwargs):
    raise AssertionError("Offline smoke entry must not access the network")
socket.socket.connect = deny_network
socket.create_connection = deny_network
from src.xiaoying_agent.cli import main
raise SystemExit(main(["--message", "测试输入"]))
'''
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "status": "ready", "mode": "offline", "message": "测试输入",
        "stage": "environment_only",
    }


def test_cli_rejects_blank_input():
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "src.xiaoying_agent", "--message", "   "],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    assert result.returncode == 2
    assert "--message" in result.stderr
    assert result.stdout == ""
