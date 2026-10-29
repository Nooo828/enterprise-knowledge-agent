from pathlib import Path
import pytest
from xiaoying_agent.knowledge import KnowledgeBase

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('query,expected',[
    ('报销期限',{'D01','D02'}), ('报账时限',{'D01','D02'}),
    ('居家上班',{'D06'}), ('输出格式',{'D04'})])
def test_retrieval_aliases_and_conflict_recall(query,expected):
    hits = KnowledgeBase.load(ROOT/'data/knowledge.json').search(query)['hits']
    assert expected <= {h['doc_id'] for h in hits}


def test_search_is_paginated_and_deterministic():
    data = [{'doc_id':f'X{i}', 'title':'报销期限', 'version_date':'2026-01-01',
             'chunks':[{'chunk_id':'a','rule_key':'报销期限','text':f'报销期限{i}天。'}]} for i in range(8)]
    kb = KnowledgeBase(data)
    first = kb.search('报销')
    second = kb.search('报销',first['next_offset'])
    assert first['total']==8
    assert first['next_offset']==5
    assert second['next_offset'] is None
    assert len(first['hits'])+len(second['hits'])==8


def test_duplicate_document_id_rejected():
    kb = KnowledgeBase.load(ROOT/'data/knowledge.json')
    doc = kb.documents[0].model_dump(mode='json')
    with pytest.raises(ValueError):
        KnowledgeBase([doc,doc])
