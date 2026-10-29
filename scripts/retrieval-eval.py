"""Run as: python scripts/retrieval-eval.py from the repository root."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from xiaoying_agent.knowledge import KnowledgeBase

root = Path(__file__).resolve().parents[1]
kb = KnowledgeBase.load(root/'data/knowledge.json')
queries = [('报销期限',{'D01','D02'}),('报账时限',{'D01','D02'}),('居家上班',{'D06'}),('输出格式',{'D04'})]
rows = []
for query, expected in queries:
    item = {'query':query,'expected_doc_ids':sorted(expected)}
    for name, enabled in [('baseline_bigrams',False),('synonym_rule_group',True)]:
        retrieved = {h['doc_id'] for h in kb.search(query,improved=enabled)['hits']}
        item[name] = {'retrieved':sorted(retrieved),'recall_at_5':len(expected & retrieved)/len(expected)}
    rows.append(item)
report = {'corpus_sha256':kb.digest,'cases':rows,'macro_recall_at_5':{
    name:sum(r[name]['recall_at_5'] for r in rows)/len(rows)
    for name in ['baseline_bigrams','synonym_rule_group']},
    'limitation':'四条人工合成查询的小样本回归，不代表通用语义检索质量。'}
(root/'examples/retrieval-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
