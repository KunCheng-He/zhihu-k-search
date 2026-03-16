import asyncio
import argparse
from login_helper import login_interactive, ensure_authenticated, AuthenticationError


async def main():
    parser = argparse.ArgumentParser(description="知乎搜索脚本")
    parser.add_argument("--login", action="store_true", help="执行交互式登录")
    parser.add_argument("--check", action="store_true", help="检查登录状态")
    args = parser.parse_args()

    if args.login:
        await login_interactive(headless=False)
    elif args.check:
        try:
            browser, context, page = await ensure_authenticated(headless=True)
            print("登录状态: 已认证")
            await browser.close()
        except AuthenticationError as e:
            print(f"登录状态: 未认证 - {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
