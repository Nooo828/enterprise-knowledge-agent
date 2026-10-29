"""Offline evidence audit. Reads saved live runs; never calls a model or GitHub."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from xiaoying_agent.agent import Agent
from xiaoying_agent.evaluate import make_cases, check
from xiaoying_agent.knowledge import KnowledgeBase
from xiaoying_agent.providers import OfflineMock
from xiaoying_agent.schemas import Action, Request

DEST = ROOT/'examples/audit'
DEST.mkdir(exist_ok=True)
report = {'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
          'network_calls':False,'live_evidence_policy':'Validate existing saved live records; no new live inference.',
          'required_files':{},'evidence':[],'links':{},'pending':['数字题号未提供','候选人亲自复核与个人学习陈述'],
          'github_verification':'Outside this offline audit; independently compare remote main with local HEAD.'}
report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for directory in ['src','tests'] for p in (ROOT/directory).rglob('*.py')}
for name in ['README.md','requirements.txt','.env.example','.gitignore',
             *[f'docs/{n}' for n in ['01-requirements.md','02-solution.md','03-evaluation.md','04-ai-usage.md','05-retrospective.md']]]:
    report['required_files'][name]=(ROOT/name).is_file() and bool((ROOT/name).read_bytes())
for directory in ['src','tests','examples','data','docs']:
    report['required_files'][directory+'/']=(ROOT/directory).is_dir()

paths=['# 真实模型决策路径摘录','',
       '由已有 live/*/trace.json 自动生成。下一动作来自真实下一条记录；未重新调用模型，也未补造步骤。','']

def display(action):
    if action['action']=='search':
        return f"search(query={action['query']}, offset={action['offset']})"
    if action['action']=='read':
        return f"read({action['doc_id']}/{action['chunk_id']})"
    return 'finish('+action['status']+')'

def cell(text):
    return str(text).replace('|','/').replace('\n',' ')

for mode in ['live','offline']:
    summary=json.loads((ROOT/f'examples/{mode}/summary.json').read_text(encoding='utf-8'))
    expected_cases={case['id']:case for case in make_cases()}
    assert {row['id'] for row in summary['cases']}==set(expected_cases)
    for row in summary['cases']:
        directory=ROOT/f'examples/{mode}'/row['id']
        artifacts={name:json.loads((directory/(name+'.json')).read_text(encoding='utf-8'))
                   for name in ['input','corpus','output','trace']}
        kb=KnowledgeBase(artifacts['corpus'])
        request=Request.model_validate(artifacts['input']['request']).model_dump()
        trace, result=artifacts['trace'],artifacts['output']
        assert trace['meta']['corpus_sha256']==kb.digest
        assert trace['meta']['mode']==('live' if mode=='live' else 'offline_mock')
        assert len(trace['steps'])<=trace['meta']['model_calls']<=trace['meta']['max_steps']
        assert trace['meta']['tool_calls']==sum(e['action']['action']!='finish' for e in trace['steps'])
        seen={}
        for number,event in enumerate(trace['steps'],1):
            assert event['step']==number
            action=Action.model_validate(event['action'])
            observation=event['observation']
            if action.action=='read' and not observation.get('error'):
                assert observation==kb.read(action.doc_id,action.chunk_id)
                seen[(action.doc_id,action.chunk_id)]=observation
            if action.action=='search' and not observation.get('error'):
                assert observation==kb.search(action.query,action.offset)
        for citation in result['citations']:
            fragment=seen[(citation['doc_id'],citation['chunk_id'])]
            assert citation['quote']==fragment['text']
            assert citation['version_date']==fragment['version_date']
        if trace['steps'][-1]['observation'].get('accepted'):
            finish=Action.model_validate(trace['steps'][-1]['action'])
            assert Agent(kb,OfflineMock())._finish(finish,trace['steps'][:-1])==result
        run={'request':request,'result':result,'trace':trace['steps'],'meta':trace['meta']}
        checks=check(run,expected_cases[row['id']])
        assert all(checks.values()), row['id']
        report['evidence'].append({'mode':mode,'case':row['id'],'status':result['status'],
            'steps':len(trace['steps']),'citations_read_and_exact':True,'passed':True})
        if mode=='live':
            paths += [f"## {row['id']} → {result['status']}",'',f"问题：{request['question']}",'',
                      '| 步骤 | 模型动作与参数 | 工具结果摘要 | 下一动作 | 公开依据 |',
                      '|---|---|---|---|---|']
            for index,event in enumerate(trace['steps']):
                observation=event['observation']
                if observation.get('error'):
                    brief=observation['error']
                elif event['action']['action']=='search':
                    brief='命中'+str(observation['total'])+'项：'+','.join(h['doc_id']+'/'+h['chunk_id'] for h in observation['hits'])
                elif event['action']['action']=='read':
                    brief=observation['text']
                else:
                    brief='结束：'+observation['status']
                following=display(trace['steps'][index+1]['action']) if index+1<len(trace['steps']) else '结束：'+result['status']
                paths.append('| '+' | '.join(map(cell,[event['step'],display(event['action']),brief,following,event['action']['reason']]))+' |')
            paths.append('')
(DEST/'decision-paths.md').write_text('\n'.join(paths).rstrip()+'\n',encoding='utf-8')

for document in [ROOT/'README.md',*(ROOT/'docs').glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)',document.read_text(encoding='utf-8')):
        if re.match(r'(https?://|#)',target):
            continue
        target=target.split('#',1)[0]
        report['links'][str(document.relative_to(ROOT))+' -> '+target]=(document.parent/target).exists()

tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
local_only=[name for name in filter(None,tracked) if any(part in {'.env','.venv','.local-tools','__pycache__'} for part in Path(name).parts)]
report['local_only_paths_tracked']=local_only
patterns=[rb'sk-[A-Za-z0-9_-]{20,}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'github_pat_[A-Za-z0-9_]{20,}',
          rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
hits=[]
for path in ROOT.rglob('*'):
    rel=path.relative_to(ROOT)
    if not path.is_file() or any(part in {'.env','.venv','.local-tools','.git','__pycache__','.pytest_cache'} for part in rel.parts):
        continue
    if any(re.search(pattern,path.read_bytes()) for pattern in patterns):
        hits.append(str(rel))
report['credential_pattern_file_matches']=hits
report['all_passed']=all(report['required_files'].values()) and all(report['links'].values()) and not local_only and not hits
(DEST/'evidence-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['all_passed'],'validated_cases':len(report['evidence']),
    'broken_links':[k for k,v in report['links'].items() if not v],
    'missing_files':[k for k,v in report['required_files'].items() if not v]},ensure_ascii=False))
raise SystemExit(0 if report['all_passed'] else 1)
