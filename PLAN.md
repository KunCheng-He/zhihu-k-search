# 知乎搜索脚本技术方案 (zhihu-k-search)

本项目旨在实现一个知乎搜索脚本，通过浏览器自动化技术模拟用户行为，获取搜索结果、问题内容及回答数据。该脚本后续将封装为 SKILL 供 Agent 使用。

## 1. 技术栈选型

*   **编程语言**: Python 3.14+
*   **包管理工具**: `uv` (高性能 Python 包管理器)
*   **自动化库**: `Playwright` (强大的浏览器控制库)
*   **反爬插件**: `playwright-stealth` (隐藏自动化特征，规避人机校验)
*   **数据模型**: `Pydantic` (用于结构化搜索结果和问答数据)
*   **HTML解析**: `BeautifulSoup4` (备用方案，用于补充解析部分服务端渲染内容)

## 2. 核心技术流程

### 2.1 身份认证持久化
*   **手动登录**: 首次运行时，脚本以"有头模式（Headed）"启动内置 Chromium 浏览器。
*   **状态保存**: 用户扫码或账号登录成功后，利用 Playwright 的 `context.storage_state()` 功能，将所有的 Cookie、LocalStorage 和 SessionStorage 导出并保存为项目根目录下的 `auth.json` 文件。
*   **免密复用**: 后续脚本运行时，直接加载 `auth.json` 初始化浏览器上下文，实现无需重复登录的身份校验。
*   **Token刷新机制**: 知乎的 `z_c0` (Authorization Token) 有时效性，脚本需检测 401 状态码并提示重新登录。

### 2.2 数据采集方案
*   **混合采集策略**:
    *   **主方案 - 网络请求拦截**: 监听浏览器网络流量，拦截知乎后端 API 响应（JSON 格式）。知乎的搜索、问题详情、回答列表均有对应的 GraphQL/REST API。
    *   **备用方案 - DOM 提取**: 对于部分服务端渲染的内容（如富文本回答），结合 Playwright 的页面元素提取作为补充。
*   **API 端点识别**:
    *   搜索接口: `https://www.zhihu.com/api/v4/search_v3` 或 `graphql` 查询
    *   问题详情: `https://www.zhihu.com/api/v4/questions/{id}`
    *   回答列表: `https://www.zhihu.com/api/v4/questions/{id}/answers`
    *   用户主页: `https://www.zhihu.com/api/v4/members/{url_token}`
*   **无头运行**: 在身份信息有效的情况下，脚本将以"无头模式（Headless）"运行，不弹出窗口，适合作为后台服务或 SKILL 调用。

## 3. 项目目录结构

```text
zhihu-k-search/scripts/
├── .python-version      # Python 版本声明 (3.14+)
├── pyproject.toml       # 项目依赖配置 (uv 管理)
├── auth.json            # 【身份认证信息】存储登录状态（本地存储，gitignore）
├── main.py              # 脚本入口，分发搜索与抓取任务
├── login_helper.py      # 专门负责处理首次登录及身份校验逻辑
├── zhihu_utils/         # 核心业务逻辑模块
│   ├── __init__.py
│   ├── browser.py       # 封装 Playwright 启动与反爬配置
│   ├── api_handler.py   # 拦截并处理 Zhihu API 请求 (GraphQL/REST)
│   ├── data_models.py   # 定义数据解析结构 (Pydantic Models)
│   └── extractors.py    # DOM 提取器（备用方案）
└── tests/               # 测试目录
    └── test_search.py
```
