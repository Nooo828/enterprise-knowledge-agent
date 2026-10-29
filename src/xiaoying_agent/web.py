"""Loopback-only UI server, bounded in-memory jobs, same Agent as the CLI."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Event, Lock
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import Field
from .agent import Agent
from .evaluate import make_cases
from .knowledge import Document, KnowledgeBase
from .providers import LiveModel, OfflineMock
from .schemas import Contract, Message, Request

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).resolve().parent/'static'
SCENARIOS = {case['id']:case for case in make_cases()}
LABELS = dict(normal='明确答案',conflict='文档冲突',outside='资料外问题',paraphrase='相似问题改写',
              context='上下文追问',tool_failure='工具持续失败',tool_recovery='失败后恢复',
              mutated='文档改为45天',resolved='冲突已消除',product='产品格式问答',step_limit='执行上限')


class WebInput(Contract):
    question: str = Field(min_length=1,max_length=2000)
    history: list[Message] = Field(default_factory=list,max_length=10)
    mode: Literal['live','offline_mock'] = 'offline_mock'
    scenario: str = 'conflict'
    max_steps: int = Field(default=12,ge=1,le=30)
    fault: Literal['search_once','read_once','search_always','read_always'] | None = None
    documents: list[Document] | None = Field(default=None,min_length=1,max_length=50)


class JobStore:
    def __init__(self, provider_factory=None):
        self.lock = Lock()
        self.jobs = {}
        self.pool = ThreadPoolExecutor(max_workers=2,thread_name_prefix='qa-ui')
        self.provider_factory = provider_factory or (lambda mode: LiveModel() if mode=='live' else OfflineMock())

    def submit(self, payload):
        value = WebInput.model_validate(payload)
        if value.scenario not in SCENARIOS:
            raise ValueError('Unknown scenario')
        docs = [doc.model_dump(mode='json') for doc in value.documents] if value.documents is not None else SCENARIOS[value.scenario]['corpus']
        if sum(len(d['chunks']) for d in docs)>100:
            raise ValueError('Too many fragments')
        kb = KnowledgeBase(docs)
        # Resolve configuration before reserving a job; never silently fall back.
        provider = self.provider_factory(value.mode)
        request = Request(question=value.question,history=value.history).model_dump()
        job_id = uuid4().hex
        job = dict(id=job_id,status='running',created_at=datetime.now(timezone.utc).isoformat(),
                   request=request,mode=value.mode,scenario=value.scenario,events=[],run=None,error=None,
                   cancel=Event(),documents=docs,max_steps=value.max_steps,fault=value.fault)
        with self.lock:
            if sum(j['status'] in ('running','cancelling') for j in self.jobs.values())>=2:
                raise RuntimeError('busy')
            while len(self.jobs)>=20:
                removable = next((key for key,j in self.jobs.items() if j['status'] not in ('running','cancelling')),None)
                if removable is None:
                    raise RuntimeError('busy')
                del self.jobs[removable]
            self.jobs[job_id]=job
        self.pool.submit(self._execute,job,kb,provider)
        return job_id

    def _execute(self,job,kb,provider):
        def notify(event):
            with self.lock:
                job['events'].append(event)
        try:
            run=Agent(kb,provider,job['max_steps'],job['fault']).run(job['request'],notify,job['cancel'].is_set)
            with self.lock:
                job['run']=run
                job['status']='completed'
        except Exception as exc:
            with self.lock:
                job['status']='failed'
                job['error']='运行异常：'+type(exc).__name__

    def snapshot(self,job_id):
        with self.lock:
            job=self.jobs[job_id]
            # Serialize under lock to provide an immutable response snapshot.
            return json.loads(json.dumps({k:v for k,v in job.items() if k!='cancel'},ensure_ascii=False))

    def summaries(self):
        with self.lock:
            return [dict(id=j['id'],question=j['request']['question'],mode=j['mode'],status=j['status'],
                         result_status=j['run']['result']['status'] if j['run'] else None,created_at=j['created_at'])
                    for j in reversed(list(self.jobs.values()))]

    def cancel(self,job_id):
        with self.lock:
            job=self.jobs[job_id]
            if job['status']=='running':
                job['cancel'].set()
                job['status']='cancelling'

    def close(self):
        with self.lock:
            for job in self.jobs.values():
                job['cancel'].set()
        self.pool.shutdown(wait=True,cancel_futures=True)


def create_server(port=8765,store=None):
    jobs=store or JobStore()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Do not put questions, headers or secrets in HTTP access logs.

        def respond(self,status,value,content_type='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def permitted(self):
            host=self.headers.get('Host','')
            try:
                hostname=urlsplit('http://'+host).hostname
            except ValueError:
                hostname=None
            if hostname not in ('127.0.0.1','localhost','::1'):
                self.respond(403,dict(error='仅允许本机访问。'))
                return False
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+host:
                self.respond(403,dict(error='拒绝跨站请求。'))
                return False
            return True

        def do_GET(self):
            if not self.permitted():
                return
            path=urlsplit(self.path).path
            pages={'/':('index.html','text/html; charset=utf-8'),
                   '/app.js':('app.js','text/javascript; charset=utf-8'),
                   '/styles.css':('styles.css','text/css; charset=utf-8')}
            if path in pages:
                name,mime=pages[path]
                return self.respond(200,(STATIC/name).read_bytes(),mime)
            if path=='/api/config':
                return self.respond(200,dict(live_configured=bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL')),
                    model=os.getenv('OPENAI_MODEL','未配置'),scenarios=[dict(id=key,label=LABELS[key],
                        question=c['question'],history=c.get('history',[]),documents=c['corpus'],
                        max_steps=c.get('max_steps',12),fault=c.get('fault')) for key,c in SCENARIOS.items()]))
            if path=='/api/jobs':
                return self.respond(200,jobs.summaries())
            if path.startswith('/api/jobs/') and len(path.split('/'))==4:
                try:
                    return self.respond(200,jobs.snapshot(path.split('/')[-1]))
                except KeyError:
                    return self.respond(404,dict(error='运行记录不存在或已被清理。'))
            self.respond(404,dict(error='未找到页面。'))

        def do_POST(self):
            if not self.permitted():
                return
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.respond(415,dict(error='仅接收JSON请求。'))
            try:
                length=int(self.headers.get('Content-Length','0'))
            except ValueError:
                length=0
            if not 0<length<=131072:
                return self.respond(413,dict(error='请求为空或超过128KB。'))
            path=urlsplit(self.path).path
            try:
                payload=json.loads(self.rfile.read(length))
                if path=='/api/jobs':
                    job_id=jobs.submit(payload)
                    return self.respond(202,dict(id=job_id))
                parts=path.split('/')
                if len(parts)==5 and parts[1:3]==['api','jobs'] and parts[4]=='cancel':
                    jobs.cancel(parts[3])
                    return self.respond(200,dict(accepted=True))
            except KeyError:
                return self.respond(404,dict(error='运行记录不存在。'))
            except RuntimeError:
                return self.respond(429,dict(error='已有两项任务运行中，请等待或停止后重试。'))
            except (ValueError,TypeError,UnicodeError):
                return self.respond(400,dict(error='输入或模型配置无效；请检查问题、资料、历史和本机.env配置。'))
            except Exception:
                return self.respond(500,dict(error='服务暂时无法执行请求。'))
            self.respond(404,dict(error='未找到接口。'))

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.jobs=jobs
    return server


def main():
    parser=argparse.ArgumentParser(description='企业知识问答本地操作界面')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 0<=args.port<=65535:
        parser.error('port must be 0..65535')
    load_dotenv(ROOT/'.env',override=False,encoding='utf-8-sig')
    server=create_server(args.port)
    print(f'企业知识问答界面：http://127.0.0.1:{server.server_port}（Ctrl+C结束）',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.jobs.close()


if __name__=='__main__':
    main()
