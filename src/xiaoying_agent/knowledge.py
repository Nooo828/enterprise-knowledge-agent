"""Local retrieval and immutable per-run document snapshot; no model answers here."""
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

from pydantic import Field
from .schemas import Contract


class Chunk(Contract):
    chunk_id: str
    rule_key: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)


class Document(Contract):
    doc_id: str
    title: str
    version_date: date
    chunks: list[Chunk] = Field(min_length=1)


SYNONYMS = {
    '报销': ['报账', '费用申请', '费用核销', '报销'],
    '期限': ['多久', '几天', '多长时间', '最晚', '截止', '时限', '期限'],
    '年假': ['带薪休假', '年休假', '年假'],
    '导出': ['输出格式', '下载格式', '导出'],
    '远程办公': ['居家上班', '在家办公', '远程办公'],
}


def expand(text):
    text = text.lower()
    for canonical, words in SYNONYMS.items():
        if any(word in text for word in words):
            text += ' ' + canonical
    return text


def tokens(text, improved=True):
    text = expand(text) if improved else text.lower()
    result = re.findall(r'[a-z0-9_]+', text)
    for run in re.findall(r'[\u4e00-\u9fff]+', text):
        result.extend(run[i:i+2] for i in range(len(run)-1))
    return Counter(result)


class KnowledgeBase:
    def __init__(self, documents):
        self.documents = [Document.model_validate(d) for d in documents]
        self.entries = {}
        for doc in self.documents:
            for chunk in doc.chunks:
                key = (doc.doc_id, chunk.chunk_id)
                if key in self.entries:
                    raise ValueError('Duplicate document/chunk identifier')
                self.entries[key] = dict(doc_id=doc.doc_id, title=doc.title,
                    version_date=doc.version_date.isoformat(), **chunk.model_dump())
        ids = [d.doc_id for d in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate document identifier')
        self.digest = hashlib.sha256(json.dumps(documents, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8-sig')))

    def search(self, query, offset=0, improved=True):
        if not query.strip() or len(query) > 500:
            raise ValueError('Search query must contain 1..500 characters')
        query_tokens = tokens(query, improved)
        entries = list(self.entries.values())
        bags = [tokens(e['title'] + ' ' + e['rule_key'] + ' ' + e['text'], improved) for e in entries]
        frequency = Counter(t for bag in bags for t in bag)
        scored = []
        for entry, bag in zip(entries, bags):
            score = sum(math.log(1 + len(entries)/(1 + frequency[t])) * min(bag[t], 2)
                        for t in query_tokens if t in bag)
            if score > 0:
                scored.append((round(score, 4), entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1]['doc_id'], pair[1]['chunk_id']))
        # Co-retrieve versions of the same atomic rule to reduce hidden conflicts.
        if improved and scored:
            keys = {entry['rule_key'] for _, entry in scored}
            seen = {(e['doc_id'], e['chunk_id']) for _, e in scored}
            scored += [(0.0, e) for e in entries if e['rule_key'] in keys and (e['doc_id'], e['chunk_id']) not in seen]
        page = scored[offset:offset+5]
        return dict(query=query, offset=offset, total=len(scored),
                    next_offset=offset+5 if offset+5 < len(scored) else None,
                    hits=[{k: e[k] for k in ('doc_id','chunk_id','title','version_date','rule_key')} |
                          {'score': score, 'preview': e['text'][:24]} for score,e in page])

    def read(self, doc_id, chunk_id):
        try:
            return self.entries[(doc_id, chunk_id)].copy()
        except KeyError:
            raise ValueError('Document fragment not found') from None


def conflicts(fragments):
    groups = {}
    for fragment in fragments:
        groups.setdefault(fragment['rule_key'], set()).add(re.sub(r'\s+', '', fragment['text']))
    return {key for key, texts in groups.items() if len(texts) > 1}
