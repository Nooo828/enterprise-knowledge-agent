"""Offline environment smoke entry point. No model or network calls."""

import argparse
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from rich.console import Console


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ReadinessReport(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: Literal["ready"] = "ready"
    mode: Literal["offline"] = "offline"
    message: str = Field(min_length=1)
    stage: Literal["environment_only"] = "environment_only"


def build_report(message: str) -> ReadinessReport:
    return ReadinessReport(message=message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="小影 AI Agent Python 基础环境检查（离线）")
    parser.add_argument("--message", default="Hello, Xiaoying Agent!", help="非空冒烟输入")
    args = parser.parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        report = build_report(args.message)
    except ValidationError:
        Console(stderr=True, color_system=None).print("输入错误：--message 不能为空或仅包含空白。")
        return 2
    Console(color_system=None).print_json(data=report.model_dump())
    return 0
