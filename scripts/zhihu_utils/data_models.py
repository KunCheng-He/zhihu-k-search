from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SearchType(str, Enum):
    ALL = "all"
    QUESTION = "question"
    ANSWER = "answer"
    ARTICLE = "article"
    USER = "people"


class SearchResult(BaseModel):
    id: str
    type: str = Field(description="内容类型: answer, article, question, people")
    title: str
    excerpt: str = Field(default="", description="内容摘要")
    author: str | None = None
    url: str
    vote_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None


class Answer(BaseModel):
    id: int
    question_id: int
    question_title: str = ""
    content: str
    excerpt: str = ""
    author_name: str
    author_url_token: str | None = None
    vote_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None
    url: str = ""


class Question(BaseModel):
    id: int
    title: str
    detail: str = ""
    answer_count: int = 0
    follower_count: int = 0
    created_at: datetime | None = None
    url: str = ""


class Article(BaseModel):
    id: str
    title: str
    content: str = ""
    excerpt: str = ""
    author_name: str
    author_url_token: str | None = None
    vote_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None
    url: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult] = []
    total: int = 0
    has_more: bool = False
    next_offset: int | None = None
