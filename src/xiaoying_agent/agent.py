"""Bounded action -> tool -> observation -> model loop with citation gates."""
import time
from .knowledge import conflicts
from .schemas import Action, Request


class Agent:
    def __init__(self, kb, provider, max_steps=12, fault=None):
        if not 1 <= max_steps <= 30:
            raise ValueError('max_steps must be 1..30')
        self.kb, self.provider, self.max_steps = kb, provider, max_steps
        if fault not in (None, 'search_once', 'read_once', 'search_always', 'read_always'):
            raise ValueError('Unknown fault injection')
        self.fault, self.fault_used = fault, False

    def _finish(self, action, observations):
        reads = {(e['observation']['doc_id'], e['observation']['chunk_id']):e['observation']
                 for e in observations if e['action']['action']=='read' and not e['observation'].get('error')}
        citations = []
        for citation in action.citations:
            evidence = reads.get((citation.doc_id, citation.chunk_id))
            if not evidence or citation.quote != evidence['text']:
                raise ValueError('Citation rejected: quote must equal an actually read full fragment')
            citations.append(citation.model_dump() | {'version_date':evidence['version_date']})
        if action.status in ('answered','conflict'):
            if not citations:
                raise ValueError('Evidence required for an answer or conflict')
            keys = {reads[(c['doc_id'],c['chunk_id'])]['rule_key'] for c in citations}
            searches = [e['observation'] for e in observations if e['action']['action']=='search' and not e['observation'].get('error')]
            for s in searches:
                if s['next_offset'] is not None and not any(t['query']==s['query'] and t['offset']==s['next_offset'] for t in searches):
                    raise ValueError('Read remaining search pages before answering')
                for h in s['hits']:
                    if h['rule_key'] in keys and (h['doc_id'],h['chunk_id']) not in reads:
                        raise ValueError('Read all discovered versions of cited rules before answering')
            relevant = [e for e in reads.values() if e['rule_key'] in keys]
            differing = conflicts(relevant)
            if differing:
                if action.status != 'conflict':
                    raise ValueError('Different texts for the same rule: report conflict, do not pick a version')
                cited_pairs = {(c['doc_id'],c['chunk_id']) for c in citations}
                if any((e['doc_id'],e['chunk_id']) not in cited_pairs for e in relevant if e['rule_key'] in differing):
                    raise ValueError('Cite every observed side of the conflict')
            if action.status=='conflict' and (len(citations)<2 or not action.gaps or not action.clarification):
                raise ValueError('Conflict needs both sources, a gap and a clarification question')
        if action.status=='needs_clarification' and not action.clarification:
            raise ValueError('Clarification question required')
        if action.status in ('not_found','tool_error','incomplete') and not action.gaps:
            raise ValueError('An explicit information gap is required')
        if action.status=='not_found' and not any(e['action']['action']=='search' and
                not e['observation'].get('error') for e in observations):
            raise ValueError('Cannot claim missing data before a successful search')
        if action.status=='tool_error' and not any(e['observation'].get('error') for e in observations):
            raise ValueError('Cannot claim tool failure without an observed error')
        prefix = {'answered':'根据已读取的资料：', 'conflict':'资料存在冲突，无法确定唯一答案：',
                  'not_found':'现有资料不足，无法回答。', 'tool_error':'工具失败，任务未完成。',
                  'needs_clarification':'需要补充信息。', 'incomplete':'任务未完成。'}[action.status]
        answer = prefix + '\n' + '\n'.join(f"[{c['doc_id']}/{c['chunk_id']}] {c['quote']}" for c in citations)
        return dict(status=action.status, answer=answer.strip(), citations=citations,
                    gaps=action.gaps, clarification=action.clarification)

    def run(self, request):
        request = Request.model_validate(request)
        started = time.monotonic()
        observations, result = [], None
        model_calls, tool_calls = 0, 0
        for step in range(1, self.max_steps+1):
            state = dict(request=request.model_dump(), observations=observations,
                         remaining_steps=self.max_steps-step+1)
            model_calls += 1
            try:
                action = Action.model_validate(self.provider.decide(state))
            except Exception as exc:
                # Never persist raw SDK exception bodies, headers, credentials or reasoning.
                result = dict(status='incomplete', answer='模型调用或动作解析失败，任务未完成。',
                              citations=[], gaps=[f'ModelError:{type(exc).__name__}'], clarification='')
                break
            try:
                if action.action=='finish':
                    result = self._finish(action, observations)
                    observation = dict(accepted=True, status=result['status'])
                else:
                    tool_calls += 1
                    fail = self.fault and self.fault.startswith(action.action) and (not self.fault_used or self.fault.endswith('always'))
                    if fail:
                        self.fault_used = True
                        raise ValueError('Injected tool outage')
                    observation = self.kb.search(action.query, action.offset) if action.action=='search' else self.kb.read(action.doc_id, action.chunk_id)
            except ValueError as exc:
                observation = dict(error=str(exc), retryable=action.action!='finish')
            observations.append(dict(step=step, action=action.model_dump(), observation=observation))
            if result is not None:
                break
        if result is None:
            result = dict(status='incomplete', answer='达到执行步数上限，任务未完成。', citations=[],
                          gaps=['step_limit_reached'], clarification='')
        return dict(request=request.model_dump(), result=result, trace=observations,
                    meta=dict(mode=self.provider.mode, model=self.provider.name,
                        corpus_sha256=self.kb.digest, max_steps=self.max_steps,
                        model_calls=model_calls, tool_calls=tool_calls,
                        duration_seconds=round(time.monotonic()-started,3),
                        usage=getattr(self.provider,'usage',{}),
                        discarded_parallel_calls=getattr(self.provider,'discarded_parallel_calls',0),
                        mock_boundary='仅验证流程，不证明真实模型决策效果。' if self.provider.mode=='offline_mock' else None))
