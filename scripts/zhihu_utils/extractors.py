from playwright.async_api import Page
from zhihu_utils.data_models import SearchResult


async def extract_search_results(page: Page) -> list[SearchResult]:
    results: list[SearchResult] = []

    await page.wait_for_selector(".SearchResult-Card, .List-item", timeout=10000)

    cards = await page.locator(".SearchResult-Card, .List-item").all()

    for card in cards:
        result = await _extract_search_card(card)
        if result:
            results.append(result)

    return results


async def _extract_search_card(card) -> SearchResult | None:
    try:
        title_el = card.locator("h2 a, .ContentItem-title a")
        if await title_el.count() == 0:
            return None

        title = await title_el.inner_text()
        url = await title_el.get_attribute("href") or ""

        excerpt_el = card.locator(".RichContent-inner, .content")
        excerpt = ""
        if await excerpt_el.count() > 0:
            excerpt = await excerpt_el.inner_text()
            excerpt = excerpt[:200] + "..." if len(excerpt) > 200 else excerpt

        author_el = card.locator(".AuthorInfo-name, .UserLink-link")
        author = ""
        if await author_el.count() > 0:
            author = await author_el.inner_text()

        item_type = "unknown"
        if "/question/" in url:
            if "/answer/" in url:
                item_type = "answer"
            else:
                item_type = "question"
        elif "/p/" in url or "zhuanlan" in url:
            item_type = "article"
        elif "/people/" in url:
            item_type = "people"

        vote_el = card.locator(".VoteButton--up")
        vote_count = 0
        if await vote_el.count() > 0:
            vote_text = await vote_el.inner_text()
            vote_count = _parse_vote_count(vote_text)

        comment_el = card.locator('button:has-text("评论"), a:has-text("评论")')
        comment_count = 0
        if await comment_el.count() > 0:
            comment_text = await comment_el.first.inner_text()
            comment_count = _parse_comment_count(comment_text)

        item_id = url.split("/")[-1] if url else ""

        return SearchResult(
            id=item_id,
            type=item_type,
            title=title.strip(),
            excerpt=excerpt.strip(),
            author=author.strip() or None,
            url=url,
            vote_count=vote_count,
            comment_count=comment_count,
        )
    except Exception:
        return None


def _parse_vote_count(text: str) -> int:
    text = text.strip()
    if not text:
        return 0

    text = text.replace("赞同", "").replace(" ", "")
    if "万" in text:
        num = float(text.replace("万", ""))
        return int(num * 10000)
    elif "k" in text.lower():
        num = float(text.lower().replace("k", ""))
        return int(num * 1000)
    else:
        try:
            return int(text)
        except ValueError:
            return 0


def _parse_comment_count(text: str) -> int:
    import re

    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    return 0


async def extract_question_detail(page: Page) -> dict:
    title_el = page.locator("h1.QuestionHeader-title")
    title = await title_el.inner_text() if await title_el.count() > 0 else ""

    detail_el = page.locator(".QuestionRichText, .QuestionHeader-detail")
    detail = await detail_el.inner_text() if await detail_el.count() > 0 else ""

    answer_count_el = page.locator(".List-headerText")
    answer_count = 0
    if await answer_count_el.count() > 0:
        text = await answer_count_el.inner_text()
        import re

        match = re.search(r"(\d+)", text)
        if match:
            answer_count = int(match.group(1))

    return {
        "title": title.strip(),
        "detail": detail.strip(),
        "answer_count": answer_count,
    }


async def extract_answers(page: Page) -> list[dict]:
    answers: list[dict] = []

    await page.wait_for_selector(".List-item", timeout=10000)
    items = await page.locator(".List-item").all()

    for item in items:
        answer = await _extract_answer_item(item)
        if answer:
            answers.append(answer)

    return answers


async def _extract_answer_item(item) -> dict | None:
    try:
        author_el = item.locator(".AuthorInfo-name")
        author = await author_el.inner_text() if await author_el.count() > 0 else ""

        content_el = item.locator(".RichContent-inner")
        content = await content_el.inner_text() if await content_el.count() > 0 else ""

        vote_el = item.locator(".VoteButton--up")
        vote_count = 0
        if await vote_el.count() > 0:
            vote_text = await vote_el.inner_text()
            vote_count = _parse_vote_count(vote_text)

        return {
            "author": author.strip(),
            "content": content.strip(),
            "vote_count": vote_count,
        }
    except Exception:
        return None
