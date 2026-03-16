from datetime import datetime
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: int
    title: str
    excerpt: str = Field(default="", description="内容摘要")
    author: str | None = None
    url: str
    created_at: datetime | None = None


class Answer(BaseModel):
    id: int
    question_id: int
    content: str
    author_name: str
    vote_count: int = 0
    comment_count: int = 0
