"""Validated contracts shared by real and offline decision providers."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Message(Contract):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)


class Request(Contract):
    question: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=10)


class Citation(Contract):
    doc_id: str
    chunk_id: str
    quote: str = Field(min_length=1)


Status = Literal['answered', 'conflict', 'needs_clarification', 'not_found', 'tool_error', 'incomplete']


class Action(Contract):
    action: Literal['search', 'read', 'finish']
    reason: str = Field(min_length=1, max_length=300, description='一句可公开的动作依据，不要内部思维过程')
    query: str = ''
    offset: int = Field(default=0, ge=0)
    doc_id: str = ''
    chunk_id: str = ''
    status: Status = 'incomplete'
    citations: list[Citation] = Field(default_factory=list, max_length=20)
    gaps: list[str] = Field(default_factory=list, max_length=10)
    clarification: str = ''
