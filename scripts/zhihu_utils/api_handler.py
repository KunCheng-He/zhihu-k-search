import json
import urllib.parse
from typing import Any
from playwright.async_api import Page, Request, Response
from zhihu_utils.data_models import (
    SearchResult,
    Answer,
    Question,
    Article,
    SearchResponse,
    SearchType,
)


SEARCH_API_URL = "https://www.zhihu.com/api/v4/search_v3"
GRAPHQL_URL = "https://www.zhihu.com/graphql"


class APIHandler:
    def __init__(self, page: Page):
        self.page = page
        self.captured_responses: list[dict[str, Any]] = []
        self._setup_interceptor()

    def _setup_interceptor(self) -> None:
        self.page.on("response", self._on_response)

    async def _on_response(self, response: Response) -> None:
        url = response.url
        if "api/v4/search" in url or "graphql" in url:
            try:
                if response.ok:
                    data = await response.json()
                    self.captured_responses.append(
                        {"url": url, "data": data, "status": response.status}
                    )
            except Exception:
                pass

    def clear_captured(self) -> None:
        self.captured_responses.clear()

    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.ALL,
        offset: int = 0,
        limit: int = 20,
    ) -> SearchResponse:
        self.clear_captured()

        encoded_query = urllib.parse.quote(query)
        type_param = search_type.value if search_type != SearchType.ALL else ""

        search_url = f"{SEARCH_API_URL}?t=general&q={encoded_query}&correction=1&offset={offset}&limit={limit}"
        if type_param:
            search_url += f"&type={type_param}"

        await self.page.goto(search_url, wait_until="networkidle")

        if self.captured_responses:
            return self._parse_search_response(
                query, self.captured_responses[0]["data"]
            )

        return await self._extract_from_dom(query)

    def _parse_search_response(
        self, query: str, data: dict[str, Any]
    ) -> SearchResponse:
        results: list[SearchResult] = []

        items = data.get("data", [])
        for item in items:
            result = self._parse_search_item(item)
            if result:
                results.append(result)

        paging = data.get("paging", {})
        is_end = paging.get("is_end", True)
        next_url = paging.get("next", "")

        next_offset = None
        if not is_end and next_url:
            parsed = urllib.parse.urlparse(next_url)
            params = urllib.parse.parse_qs(parsed.query)
            if "offset" in params:
                next_offset = int(params["offset"][0])

        return SearchResponse(
            query=query,
            results=results,
            total=len(results),
            has_more=not is_end,
            next_offset=next_offset,
        )

    def _parse_search_item(self, item: dict[str, Any]) -> SearchResult | None:
        item_type = item.get("type", "")
        obj = item.get("object", item)
        highlight = item.get("highlight", {})

        if item_type == "search_result":
            obj = item.get("object", {})
            item_type = obj.get("type", item.get("type", ""))

        if item_type in ("answer", "article", "question", "people"):
            return self._create_search_result(obj, item_type, highlight)

        return None

    def _create_search_result(
        self,
        obj: dict[str, Any],
        item_type: str,
        highlight: dict[str, Any] | None = None,
    ) -> SearchResult:
        highlight = highlight or {}
        item_id = obj.get("id", "")

        title = highlight.get("title", "")
        if not title:
            if item_type == "answer":
                question = obj.get("question", {}) or {}
                title = question.get("title", "") or obj.get("title", "")
            elif item_type == "question":
                title = obj.get("title", "")
            elif item_type == "article":
                title = obj.get("title", "")
            elif item_type == "people":
                title = obj.get("name", "")

        title = self._strip_html_tags(title)

        excerpt = (
            highlight.get("description", "")
            or obj.get("excerpt", "")
            or obj.get("headline", "")
        )
        excerpt = self._strip_html_tags(excerpt)

        author = None
        if item_type in ("answer", "article"):
            author_info = obj.get("author", {})
            author = author_info.get("name", "")
        elif item_type == "people":
            author = obj.get("name", "")

        url = obj.get("url", "")
        if url and url.startswith("https://api.zhihu.com/"):
            url = ""
        if not url:
            if item_type == "answer":
                question_id = obj.get("question", {}).get("id", "")
                url = f"https://www.zhihu.com/question/{question_id}/answer/{item_id}"
            elif item_type == "question":
                url = f"https://www.zhihu.com/question/{item_id}"
            elif item_type == "article":
                url = f"https://zhuanlan.zhihu.com/p/{item_id}"
            elif item_type == "people":
                url_token = obj.get("url_token", "")
                url = f"https://www.zhihu.com/people/{url_token}"

        vote_count = obj.get("voteup_count", 0) or 0
        comment_count = obj.get("comment_count", 0) or 0

        return SearchResult(
            id=str(item_id),
            type=item_type,
            title=title,
            excerpt=excerpt,
            author=author,
            url=url,
            vote_count=vote_count,
            comment_count=comment_count,
        )

    @staticmethod
    def _strip_html_tags(text: str) -> str:
        import re

        return re.sub(r"<[^>]+>", "", text)

    async def _extract_from_dom(self, query: str) -> SearchResponse:
        from zhihu_utils.extractors import extract_search_results

        results = await extract_search_results(self.page)
        return SearchResponse(
            query=query,
            results=results,
            total=len(results),
            has_more=False,
        )

    async def get_question(self, question_id: int) -> Question | None:
        url = f"https://www.zhihu.com/api/v4/questions/{question_id}"
        self.clear_captured()

        await self.page.goto(url, wait_until="networkidle")

        if self.captured_responses:
            data = self.captured_responses[0]["data"]
            return self._parse_question(data)

        return None

    def _parse_question(self, data: dict[str, Any]) -> Question:
        return Question(
            id=data.get("id", 0),
            title=data.get("title", ""),
            detail=data.get("detail", ""),
            answer_count=data.get("answer_count", 0),
            follower_count=data.get("follower_count", 0),
            url=f"https://www.zhihu.com/question/{data.get('id', 0)}",
        )

    async def get_answers(
        self,
        question_id: int,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "default",
    ) -> list[Answer]:
        url = f"https://www.zhihu.com/api/v4/questions/{question_id}/answers?offset={offset}&limit={limit}&sort_by={sort_by}"
        self.clear_captured()

        await self.page.goto(url, wait_until="networkidle")

        if self.captured_responses:
            data = self.captured_responses[0]["data"]
            return self._parse_answers(data.get("data", []))

        return []

    def _parse_answers(self, items: list[dict[str, Any]]) -> list[Answer]:
        answers: list[Answer] = []
        for item in items:
            answer = self._parse_answer(item)
            if answer:
                answers.append(answer)
        return answers

    def _parse_answer(self, data: dict[str, Any]) -> Answer | None:
        if not data:
            return None

        question = data.get("question", {})
        author = data.get("author", {})

        return Answer(
            id=data.get("id", 0),
            question_id=question.get("id", 0),
            question_title=question.get("title", ""),
            content=data.get("content", ""),
            excerpt=data.get("excerpt", ""),
            author_name=author.get("name", ""),
            author_url_token=author.get("url_token", ""),
            vote_count=data.get("voteup_count", 0) or 0,
            comment_count=data.get("comment_count", 0) or 0,
            url=f"https://www.zhihu.com/question/{question.get('id', 0)}/answer/{data.get('id', 0)}",
        )
