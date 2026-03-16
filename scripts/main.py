import asyncio
import argparse
import json
import re
from login_helper import login_interactive, ensure_authenticated, AuthenticationError
from zhihu_utils.api_handler import APIHandler
from zhihu_utils.data_models import SearchType


def parse_url(url: str) -> dict:
    result = {"type": None, "id": None, "question_id": None}

    question_answer = re.search(r"zhihu\.com/question/(\d+)/answer/(\d+)", url)
    if question_answer:
        result["type"] = "answer"
        result["question_id"] = int(question_answer.group(1))
        result["id"] = int(question_answer.group(2))
        return result

    question = re.search(r"zhihu\.com/question/(\d+)", url)
    if question:
        result["type"] = "question"
        result["id"] = int(question.group(1))
        return result

    article = re.search(r"zhuanlan\.zhihu\.com/p/(\d+)", url)
    if article:
        result["type"] = "article"
        result["id"] = article.group(1)
        return result

    return result


async def search_command(query: str, search_type: str, limit: int, output: str | None):
    try:
        browser, context, page = await ensure_authenticated(headless=True)
    except AuthenticationError as e:
        print(f"错误: {e}")
        return

    try:
        handler = APIHandler(page)
        st = SearchType(search_type) if search_type else SearchType.ALL
        response = await handler.search(query, search_type=st, limit=limit)

        print(f"\n搜索: {query}")
        print(f"找到 {len(response.results)} 条结果\n")

        for i, result in enumerate(response.results, 1):
            print(f"[{i}] {result.title}")
            print(f"    类型: {result.type}")
            if result.author:
                print(f"    作者: {result.author}")
            if result.vote_count > 0:
                print(f"    赞同: {result.vote_count}")
            print(f"    链接: {result.url}")
            if result.excerpt:
                print(f"    摘要: {result.excerpt[:100]}...")
            print()

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(), f, ensure_ascii=False, indent=2)
            print(f"结果已保存至: {output}")

    finally:
        await browser.close()


async def detail_command(url: str, answer_limit: int, output: str | None):
    try:
        browser, context, page = await ensure_authenticated(headless=True)
    except AuthenticationError as e:
        print(f"错误: {e}")
        return

    try:
        handler = APIHandler(page)
        parsed = parse_url(url)

        if not parsed["type"]:
            print(f"无法解析链接: {url}")
            return

        if parsed["type"] == "answer":
            answer = await handler.get_answer(parsed["id"], parsed.get("question_id"))
            if not answer:
                print("获取回答失败")
                return

            print(f"\n问题: {answer.question_title}")
            print(f"作者: {answer.author_name}")
            print(f"赞同: {answer.vote_count}  评论: {answer.comment_count}")
            print(f"链接: {answer.url}")
            print("\n" + "=" * 50 + "\n")
            content = strip_html(answer.content)
            print(content[:2000] + "..." if len(content) > 2000 else content)

            if output:
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(answer.model_dump(), f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存至: {output}")

        elif parsed["type"] == "question":
            data = await handler.get_question_with_answers(
                parsed["id"], answer_limit=answer_limit
            )
            if not data:
                print("获取问题失败")
                return

            question = data["question"]
            answers = data["answers"]

            print(f"\n问题: {question.title}")
            print(f"回答数: {question.answer_count}  关注数: {question.follower_count}")
            print(f"链接: {question.url}")
            if question.detail:
                print(f"\n问题详情:\n{strip_html(question.detail)[:500]}")

            print(f"\n共 {len(answers)} 个回答:\n")
            for i, ans in enumerate(answers, 1):
                print(f"[{i}] {ans.author_name}")
                print(f"    赞同: {ans.vote_count}  评论: {ans.comment_count}")
                excerpt = strip_html(ans.excerpt or ans.content)[:200]
                print(f"    {excerpt}...")
                print()

            if output:
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "question": question.model_dump(),
                            "answers": [a.model_dump() for a in answers],
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                print(f"结果已保存至: {output}")

        elif parsed["type"] == "article":
            article = await handler.get_article(parsed["id"])
            if not article:
                print("获取文章失败")
                return

            print(f"\n文章: {article.title}")
            print(f"作者: {article.author_name}")
            print(f"赞同: {article.vote_count}  评论: {article.comment_count}")
            print(f"链接: {article.url}")
            print("\n" + "=" * 50 + "\n")
            content = strip_html(article.content)
            print(content[:2000] + "..." if len(content) > 2000 else content)

            if output:
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(article.model_dump(), f, ensure_ascii=False, indent=2)
                print(f"\n结果已保存至: {output}")

    finally:
        await browser.close()


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def main():
    parser = argparse.ArgumentParser(description="知乎搜索脚本")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    login_parser = subparsers.add_parser("login", help="交互式登录")
    login_parser.add_argument("--check", action="store_true", help="检查登录状态")

    search_parser = subparsers.add_parser("search", help="搜索知乎内容")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument(
        "--type",
        "-t",
        choices=["all", "question", "answer", "article", "people"],
        default="all",
        help="搜索类型",
    )
    search_parser.add_argument("--limit", "-l", type=int, default=10, help="结果数量")
    search_parser.add_argument("--output", "-o", help="输出文件路径 (JSON)")

    detail_parser = subparsers.add_parser("detail", help="获取帖子详情")
    detail_parser.add_argument("url", help="知乎链接 (问题/回答/文章)")
    detail_parser.add_argument(
        "--answer-limit", "-a", type=int, default=5, help="获取回答数量 (仅问题)"
    )
    detail_parser.add_argument("--output", "-o", help="输出文件路径 (JSON)")

    args = parser.parse_args()

    if args.command == "login":
        if hasattr(args, "check") and args.check:
            try:
                browser, context, page = await ensure_authenticated(headless=True)
                print("登录状态: 已认证")
                await browser.close()
            except AuthenticationError as e:
                print(f"登录状态: 未认证 - {e}")
        else:
            await login_interactive(headless=False)
    elif args.command == "search":
        await search_command(args.query, args.type, args.limit, args.output)
    elif args.command == "detail":
        await detail_command(args.url, args.answer_limit, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
