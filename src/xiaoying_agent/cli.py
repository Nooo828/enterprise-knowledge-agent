"""Enterprise QA CLI, with a retained environment smoke entry point."""

import argparse
import json
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
    parser = argparse.ArgumentParser(description="企业知识问答 Agent；--question 启动问答，未提供时运行环境冒烟检查")
    parser.add_argument("--message", default="Hello, Knowledge Agent!", help="非空冒烟输入")
    parser.add_argument('--question', help='企业制度或产品问题')
    parser.add_argument('--history', type=Path, help='JSON 数组，每项为 role/content')
    parser.add_argument('--corpus', type=Path, default=PROJECT_ROOT/'data/knowledge.json')
    parser.add_argument('--mode', choices=['live','offline_mock'], default='live')
    parser.add_argument('--max-steps', type=int, default=12)
    parser.add_argument('--fault', choices=['search_once','read_once','search_always','read_always'])
    parser.add_argument('--output', type=Path, help='将结果和 Trace 保存为 JSON')
    args = parser.parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env", override=False, encoding='utf-8-sig')
    if args.question is not None:
        from .agent import Agent
        from .knowledge import KnowledgeBase
        from .providers import LiveModel, OfflineMock
        try:
            history = json.loads(args.history.read_text(encoding='utf-8-sig')) if args.history else []
            provider = LiveModel() if args.mode=='live' else OfflineMock()
            run = Agent(KnowledgeBase.load(args.corpus), provider, args.max_steps, args.fault).run(
                dict(question=args.question, history=history))
        except (ValueError, OSError) as exc:
            Console(stderr=True, color_system=None).print('配置或输入错误：' + type(exc).__name__)
            return 2
        rendered = json.dumps(run, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered+'\n', encoding='utf-8')
        print(rendered)
        return 0 if run['result']['status'] in ('answered','conflict','not_found','needs_clarification') else 3
    try:
        report = build_report(args.message)
    except ValidationError:
        Console(stderr=True, color_system=None).print("输入错误：--message 不能为空或仅包含空白。")
        return 2
    Console(color_system=None).print_json(data=report.model_dump())
    return 0
