from contextlib import contextmanager
from http.client import HTTPConnection
import json
from threading import Event, Thread
import time

import pytest

from xiaoying_agent.agent import Agent
from xiaoying_agent.evaluate import make_cases
from xiaoying_agent.knowledge import KnowledgeBase
from xiaoying_agent.providers import OfflineMock
from xiaoying_agent.web import JobStore, create_server


@pytest.fixture
def web_server():
    def factory(mode):
        if mode=='live':
            raise ValueError('Live configuration intentionally unavailable in offline tests')
        return OfflineMock()
    store=JobStore(factory)
    server=create_server(0,store)
    worker=Thread(target=server.serve_forever,daemon=True)
    worker.start()
    yield server
    server.shutdown()
    worker.join(timeout=3)
    server.server_close()
    store.close()


def request(server,path,body=None,headers=None):
    connection=HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    data=json.dumps(body).encode() if body is not None else None
    combined={'Content-Type':'application/json'} if data is not None else {}
    combined.update(headers or {})
    connection.request('POST' if data is not None else 'GET',path,data,combined)
    response=connection.getresponse()
    raw=response.read()
    status=response.status
    content_type=response.getheader('Content-Type')
    connection.close()
    return status,json.loads(raw) if content_type.startswith('application/json') else raw


def finished(server,job_id):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        _,job=request(server,'/api/jobs/'+job_id)
        if job['status'] not in ('running','cancelling'):
            return job
        time.sleep(.01)
    raise AssertionError('Local test job did not finish')


@pytest.mark.parametrize('case',make_cases(),ids=lambda c:c['id'])
def test_http_acceptance_uses_core_agent(web_server,case):
    code,response=request(web_server,'/api/jobs',dict(question=case['question'],history=case.get('history',[]),
        scenario=case['id'],fault=case.get('fault'),max_steps=case.get('max_steps',12),mode='offline_mock'))
    assert code==202
    job=finished(web_server,response['id'])
    assert job['run']['result']['status']==case['status']
    assert job['run']['meta']['mode']=='offline_mock'
    assert any(event['kind']=='model_start' for event in job['events'])
    assert [e['payload'] for e in job['events'] if e['kind']=='step']==job['run']['trace']
    assert job['events'][-1]['kind']=='completed'


def test_web_edit_changes_actual_evidence(web_server):
    docs=make_cases()[0]['corpus']
    docs[0]['chunks'][0]['text']='报销申请须在费用发生后60天内提交。'
    code,response=request(web_server,'/api/jobs',dict(question='报销期限多久？',scenario='normal',documents=docs))
    assert code==202
    job=finished(web_server,response['id'])
    assert '60天' in job['run']['result']['answer']
    assert '30天' not in job['run']['result']['answer']
    assert job['documents'][0]['chunks'][0]['text']==docs[0]['chunks'][0]['text']


def test_frontend_and_routes_cannot_expose_environment(web_server,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','UI_SECRET_SENTINEL')
    monkeypatch.setenv('OPENAI_MODEL','test-model')
    status,config=request(web_server,'/api/config')
    assert status==200 and config['live_configured']
    assert 'UI_SECRET_SENTINEL' not in json.dumps(config)
    for path in ['/.env','/.local-tools/gh-config/hosts.yml','/../.env','/src/xiaoying_agent/providers.py']:
        assert request(web_server,path)[0]==404
    for path in ['/','/app.js','/styles.css']:
        assert request(web_server,path)[0]==200


@pytest.mark.parametrize('headers',[{'Host':'attacker.example'},{'Origin':'https://attacker.example'}])
def test_cross_site_requests_rejected(web_server,headers):
    assert request(web_server,'/api/jobs',{'question':'报销期限'},headers)[0]==403


@pytest.mark.parametrize('payload',[
    {'question':'  '},{'question':'报销','scenario':'../../.env'},
    {'question':'报销','max_steps':31},{'question':'报销','api_key':'unwanted'},
    {'question':'报销','mode':'live'},{'question':'报销','documents':[]},
])
def test_invalid_web_requests_fail_without_starting_job(web_server,payload):
    assert request(web_server,'/api/jobs',payload)[0]==400
    assert request(web_server,'/api/jobs')[1]==[]


def test_observer_cannot_mutate_execution_or_break_cli_contract():
    def faulty_observer(event):
        event['payload'].clear()
        raise RuntimeError('Observer failed')
    case=make_cases()[0]
    run=Agent(KnowledgeBase(case['corpus']),OfflineMock()).run({'question':case['question']},faulty_observer)
    assert run['result']['status']=='answered'
    assert run['trace'][0]['action']['action']=='search'


def test_user_cancel_is_explicitly_incomplete():
    case=make_cases()[0]
    run=Agent(KnowledgeBase(case['corpus']),OfflineMock()).run({'question':case['question']},should_stop=lambda:True)
    assert run['result']['status']=='incomplete'
    assert run['result']['gaps']==['user_cancelled']
    assert run['meta']['model_calls']==0


def test_job_concurrency_and_cooperative_cancel():
    release,started=Event(),Event()
    class BlockingMock(OfflineMock):
        def decide(self,state):
            started.set()
            release.wait(3)
            return super().decide(state)
    store=JobStore(lambda mode:BlockingMock())
    try:
        payload={'question':'报销期限多久？'}
        first=store.submit(payload)
        assert started.wait(2)
        store.submit(payload)
        with pytest.raises(RuntimeError):
            store.submit(payload)
        store.cancel(first)
        assert store.snapshot(first)['status']=='cancelling'
        release.set()
        deadline=time.monotonic()+3
        while store.snapshot(first)['status']!='completed' and time.monotonic()<deadline:
            time.sleep(.01)
        assert store.snapshot(first)['run']['result']['gaps']==['user_cancelled']
    finally:
        release.set()
        store.close()
