import asyncio
import argparse
import json
from login_helper import login_interactive, ensure_authenticated, AuthenticationError
from zhihu_utils.api_handler import APIHandler
from zhihu_utils.data_models import SearchType


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
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
