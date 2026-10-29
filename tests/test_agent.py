import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from xiaoying_agent.agent import Agent
from xiaoying_agent.evaluate import make_cases, check
from xiaoying_agent.knowledge import KnowledgeBase
from xiaoying_agent.providers import OfflineMock
from xiaoying_agent.providers import LiveModel
from xiaoying_agent.schemas import Action


@pytest.mark.parametrize('case', make_cases(), ids=lambda case: case['id'])
def test_acceptance_offline(case):
    run = Agent(KnowledgeBase(case['corpus']), OfflineMock(), case.get('max_steps',12),case.get('fault')).run(
        dict(question=case['question'], history=case.get('history',[])))
    assert all(check(run,case).values())
    assert run['meta']['mode']=='offline_mock'


class Scripted:
    mode, name = 'test_stub', 'adversarial-script'
    def __init__(self, actions):
        self.actions = iter(actions)
    def decide(self, state):
        return Action.model_validate(next(self.actions))


def test_false_quote_rejected_then_step_limit():
    case = make_cases()[0]
    actions = [dict(action='read',doc_id='D01',chunk_id='deadline',reason='test'),
               dict(action='finish',status='answered',reason='test',citations=[
                   dict(doc_id='D01',chunk_id='deadline',quote='报销期限是999天。')])]
    run = Agent(KnowledgeBase(case['corpus']),Scripted(actions),2).run({'question':'报销期限多久？'})
    assert run['result']['status']=='incomplete'
    assert 'Citation rejected' in run['trace'][-1]['observation']['error']
    assert '999' not in run['result']['answer']


def test_cannot_answer_newer_document_without_reading_other_version():
    case = make_cases()[1]
    actions = [dict(action='search',query='报销期限',reason='test'),
               dict(action='read',doc_id='D02',chunk_id='deadline',reason='test'),
               dict(action='finish',status='answered',reason='test',citations=[
                   dict(doc_id='D02',chunk_id='deadline',quote='报销申请须在费用发生后15天内提交。')])]
    run = Agent(KnowledgeBase(case['corpus']),Scripted(actions),3).run({'question':'报销期限多久？'})
    assert run['result']['status']=='incomplete'
    assert 'all discovered versions' in run['trace'][-1]['observation']['error']


def test_cannot_pick_one_side_after_reading_both():
    case = make_cases()[1]
    actions = [dict(action='read',doc_id=doc,chunk_id='deadline',reason='test') for doc in ['D01','D02']]
    actions += [dict(action='finish',status='answered',reason='test',citations=[
        dict(doc_id='D02',chunk_id='deadline',quote='报销申请须在费用发生后15天内提交。')])]
    run = Agent(KnowledgeBase(case['corpus']),Scripted(actions),3).run({'question':'报销期限多久？'})
    assert run['result']['status']=='incomplete'
    assert 'report conflict' in run['trace'][-1]['observation']['error']


def test_changed_content_changes_evidence_without_changing_doc_id():
    a, b = make_cases()[0], make_cases()[7]
    first = Agent(KnowledgeBase(a['corpus']),OfflineMock()).run({'question':a['question']})
    second = Agent(KnowledgeBase(b['corpus']),OfflineMock()).run({'question':b['question']})
    assert first['meta']['corpus_sha256'] != second['meta']['corpus_sha256']
    assert '30天' in first['result']['answer']
    assert '45天' in second['result']['answer']


def test_unknown_document_becomes_observed_tool_error():
    actions = [dict(action='read',doc_id='does-not-exist',chunk_id='x',reason='test')]
    run = Agent(KnowledgeBase(make_cases()[0]['corpus']),Scripted(actions),1).run({'question':'报销？'})
    assert run['trace'][0]['observation']['error']=='Document fragment not found'
    assert run['result']['status']=='incomplete'


def test_provider_error_does_not_persist_exception_secret():
    class Broken:
        mode, name = 'test_stub', 'broken'
        def decide(self,state):
            raise RuntimeError('SENSITIVE_SENTINEL_NOT_FOR_LOGS')
    run = Agent(KnowledgeBase(make_cases()[0]['corpus']),Broken()).run({'question':'报销？'})
    assert run['result']['status']=='incomplete'
    assert 'SENSITIVE_SENTINEL' not in json.dumps(run)


def test_nonempty_request_and_step_limits_are_validated():
    kb = KnowledgeBase(make_cases()[0]['corpus'])
    with pytest.raises(ValueError):
        Agent(kb,OfflineMock(),0)
    with pytest.raises(ValueError):
        Agent(kb,OfflineMock()).run({'question':'  '})


def test_compatible_provider_batch_executes_only_first_proposal():
    first = SimpleNamespace(function=SimpleNamespace(name='select_action',arguments=json.dumps(
        dict(action='search',query='报销',reason='test'))))
    second = SimpleNamespace(function=SimpleNamespace(name='select_action',arguments=json.dumps(
        dict(action='read',doc_id='D01',chunk_id='deadline',reason='test'))))
    response = SimpleNamespace(usage=None,choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[first,second]))])
    model = LiveModel.__new__(LiveModel)
    model.name, model.usage, model.discarded_parallel_calls = 'adapter-test', {}, 0
    model.client = SimpleNamespace(base_url='https://api.deepseek.com',chat=SimpleNamespace(
        completions=SimpleNamespace(create=lambda **kwargs:response)))
    selected = model.decide({'request':{},'observations':[]})
    assert selected.action=='search'
    assert model.discarded_parallel_calls==1


def test_no_search_cannot_be_reported_as_not_found():
    model = Scripted([dict(action='finish',status='not_found',gaps=['无资料'],reason='test')])
    run = Agent(KnowledgeBase(make_cases()[0]['corpus']),model,1).run({'question':'测试'})
    assert run['result']['status']=='incomplete'
    assert 'before a successful search' in run['trace'][0]['observation']['error']


def test_unread_search_page_cannot_be_ignored():
    corpus = [{'doc_id':f'P{i}', 'title':'报销期限','version_date':'2026-01-01',
               'chunks':[{'chunk_id':'a','rule_key':'报销期限','text':'报销期限30天。'}]} for i in range(6)]
    actions = [dict(action='search',query='报销',reason='test'),
               dict(action='read',doc_id='P0',chunk_id='a',reason='test'),
               dict(action='finish',status='answered',reason='test',citations=[
                   dict(doc_id='P0',chunk_id='a',quote='报销期限30天。')])]
    run = Agent(KnowledgeBase(corpus),Scripted(actions),3).run({'question':'报销期限'})
    assert run['result']['status']=='incomplete'
    assert 'remaining search pages' in run['trace'][-1]['observation']['error']
