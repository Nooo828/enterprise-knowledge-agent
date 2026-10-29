"""Executable acceptance suite: saved inputs, actual outputs, traces, objective checks."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

from dotenv import load_dotenv
from .agent import Agent
from .knowledge import KnowledgeBase
from .providers import LiveModel, OfflineMock

ROOT = Path(__file__).resolve().parents[2]


def make_cases():
    full = json.loads((ROOT/'data/knowledge.json').read_text(encoding='utf-8'))
    normal = [d for d in full if d['doc_id']!='D02']
    changed = copy.deepcopy(normal)
    changed[0]['chunks'][0]['text'] = '报销申请须在费用发生后45天内提交。'
    changed[0]['version_date'] = '2026-10-29'
    aligned = copy.deepcopy(full)
    aligned[1]['chunks'][0]['text'] = aligned[0]['chunks'][0]['text']
    return [
        dict(id='normal',question='报销期限多久？',corpus=normal,status='answered',quotes=['30天']),
        dict(id='conflict',question='报销期限多久？',corpus=full,status='conflict',quotes=['30天','15天']),
        dict(id='outside',question='火星上有多少只独角兽？',corpus=full,status='not_found',quotes=[]),
        dict(id='paraphrase',question='报账最晚能隔多长时间提交？',corpus=normal,status='answered',quotes=['30天']),
        dict(id='context',question='那最晚什么时候交？',history=[{'role':'user','content':'我想了解报销制度'},
             {'role':'assistant','content':'我们来核实相关制度。'}],corpus=normal,status='answered',quotes=['30天']),
        dict(id='tool_failure',question='报销期限多久？',corpus=full,fault='search_always',status='tool_error',quotes=[]),
        dict(id='tool_recovery',question='报销期限多久？',corpus=normal,fault='read_once',status='answered',quotes=['30天']),
        dict(id='mutated',question='报销期限多久？',corpus=changed,status='answered',quotes=['45天']),
        dict(id='resolved',question='报销期限多久？',corpus=aligned,status='answered',quotes=['30天']),
        dict(id='product',question='CloudNote 支持什么导出格式？',corpus=full,status='answered',quotes=['PDF','Markdown']),
        dict(id='step_limit',question='报销期限多久？',corpus=full,max_steps=1,status='incomplete',quotes=[]),
    ]


def check(run, case):
    result = run['result']
    kb = KnowledgeBase(case['corpus'])
    checks = {'expected_status':result['status']==case['status'],
              'expected_evidence':all(q in result['answer'] for q in case['quotes']),
              'citations_exact':all(c['quote']==kb.read(c['doc_id'],c['chunk_id'])['text'] for c in result['citations']),
              'bounded':run['meta']['model_calls']<=run['meta']['max_steps']}
    if case['status']=='conflict':
        checks['both_conflict_documents'] = {'D01','D02'} <= {c['doc_id'] for c in result['citations']}
        checks['asks_applicability'] = bool(result['clarification'] and result['gaps'])
    if case['id']=='mutated':
        checks['no_stale_value'] = '30天' not in result['answer']
    if case['id']=='outside':
        checks['no_unfounded_citations'] = not result['citations']
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['live','offline_mock'],default='offline_mock')
    parser.add_argument('--out',type=Path,default=ROOT/'examples/offline')
    parser.add_argument('--case',action='append',help='可重复，默认运行全部用例')
    args = parser.parse_args()
    load_dotenv(ROOT/'.env',encoding='utf-8-sig',override=False)
    args.out.mkdir(parents=True,exist_ok=True)
    summary = {'mode':args.mode,'recorded_at':datetime.now(timezone.utc).isoformat(),'cases':[]}
    for case in make_cases():
        if args.case and case['id'] not in args.case:
            continue
        request = dict(question=case['question'],history=case.get('history',[]))
        provider = LiveModel() if args.mode=='live' else OfflineMock()
        run = Agent(KnowledgeBase(case['corpus']),provider,case.get('max_steps',12),case.get('fault')).run(request)
        directory = args.out/case['id']
        directory.mkdir(parents=True,exist_ok=True)
        artifacts = {'input.json':{'request':request,'fault':case.get('fault'),'max_steps':case.get('max_steps',12)},
                     'corpus.json':case['corpus'],'output.json':run['result'],
                     'trace.json':{'meta':run['meta'],'steps':run['trace']}}
        for name, content in artifacts.items():
            (directory/name).write_text(json.dumps(content,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        checks = check(run,case)
        row = dict(id=case['id'],expected=case['status'],actual=run['result']['status'],checks=checks,
                   passed=all(checks.values()),steps=len(run['trace']),mode=run['meta']['mode'])
        summary['cases'].append(row)
        print(json.dumps(row,ensure_ascii=False),flush=True)
        (args.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not summary['cases']:
        raise SystemExit('No matching evaluation cases')
    raise SystemExit(0 if all(row['passed'] for row in summary['cases']) else 1)


if __name__=='__main__':
    main()
