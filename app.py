"""
我的私人实验室 - Streamlit 应用
功能：
1. 连接钱包（使用 SpoonOS SDK）
2. AI 聊天界面（左侧边栏设置 System Prompt，主界面聊天）
"""

import os
import json
import subprocess
import re
from typing import TypedDict, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 仅使用 DeepSeek（临时简化，方便调试）
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["DEFAULT_LLM_PROVIDER"] = "deepseek"
# 修正 DeepSeek 默认 max_tokens（SDK 默认值过大，DeepSeek 会报 400）
os.environ["DEEPSEEK_MAX_TOKENS"] = "4096"

import streamlit as st
import streamlit.components.v1 as components

# 导入必要的库
try:
    from spoon_ai.chat import ChatBot
except ImportError:
    st.error("请先安装 spoon-ai-sdk: pip install spoon-ai-sdk")
    st.stop()
try:
    from spoon_ai.tools.base import BaseTool, ToolResult
except Exception:
    BaseTool = None
    ToolResult = None

try:
    from openai import OpenAI
except ImportError:
    st.error("请先安装 openai: pip install openai")
    st.stop()

try:
    import requests
except ImportError:
    st.error("请先安装 requests: pip install requests")
    st.stop()

try:
    from spoon_ai.tools.mcp_tool import MCPTool
except Exception:
    MCPTool = None

try:
    from spoon_ai.graph.engine import StateGraph, InMemoryCheckpointer, END
except Exception:
    StateGraph = None
    InMemoryCheckpointer = None
    END = None

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except Exception:
    Account = None
    encode_defunct = None

# 配置页面
st.set_page_config(
    page_title="我的私人实验室",
    page_icon="🧪",
    layout="wide"
)

st.markdown(
    """
    <style>
      .block-container { max-width: 1200px; }
    </style>
    """,
    unsafe_allow_html=True
)

# 初始化 session state（统一入口，避免重复检查）
def init_session_state() -> None:
    defaults = {
        "wallet_address": None,
        "wallet_authed": False,
        "wallet_nonce": "",
        "wallet_signature_input": "",
        "wallet_auth_error": "",
        "wallet_auth_warning": "",
        "wallet_status": "",
        "wallet_origin": "",
        "wallet_domain": "",
        "wallet_issued_at": "",
        "wallet_message": "",
        "agent1_skill": "",
        "agent2_skill": "",
        "agent3_skill": "",
        "chat_history": [],
        "square_history": [],
        "square_rounds": 2,
        "square_posts": [],
        "last_debate": {},
        "system_prompt": "你是一个友好的AI助手，可以帮助用户解答问题。",
        "agent1_style": (
            "你是现实主义机会猎手\n"
            "(人格 . \"清醒的猎豹 + 杠杆敏感者 + 执行优先者\")\n"
            "(风格 . (\"极简\" \"锋利但不浮夸\" \"画面感强\" \"零鸡汤\"))\n"
            "(认知 . \"机会永远存在于不对称处\" \"但必须基于当前真实地形\" \"犹豫是最大敌人，但盲目更致命\")"
        ),
        "agent2_style": (
            "你是冷峻的风险审计师\n"
            "(人格 . \"老兵计数器 + 裂缝显微镜 + 损失第一主义者\")\n"
            "(风格 . (\"冰冷精确\" \"克制\" \"零情绪渲染\" \"手术刀式\"))\n"
            "(认知 . \"任何机会都有真实代价\" \"保住本金是唯一不可谈判底线\" \"概率×赔率决定生死\")"
        ),
        "agent3_style": (
            "你是极致务实的执行建筑师\n"
            "(人格 . \"现实地形测绘师 + 杠杆平衡手 + 小步快跑指挥官\")\n"
            "(风格 . (\"结构化\" \"军事行动级清晰\" \"高可执行\" \"零模棱两可\"))\n"
            "(认知 . \"没有完美，只有当下最优可落地方案\" \"确定性永远优先于天花板\" \"执行力碾压争论\")"
        ),
        "chain_data": None,
        "defillama_data": {},
        "coinmarketcap_data": {},
        "thegraph_data": {},
        "news_items": [],
        "analysis_text": "",
        "cards": [],
        "chief_summary": "",
        "news_cards": [],
        "timely_news_cards": [],
        "hot_news_cards": [],
        "mcp_self_check": [],
        "coinmarketcap_api_key": os.getenv("COINMARKETCAP_API_KEY", ""),
        "cmc_debug": "",
        "load_dashboard_cache": False,
        "auto_refresh_done": False,
        "auto_refresh_on_load": False,
        "doubao_debug": "",
        "news_summary": "",
        "last_news_summary": "",
        "last_news_cards": [],
        "newsdata_items": [],
        "chain_errors": [],
        "news_errors": [],
        "mcp_errors": [],
        "mcp_result": "",
        "mcp_results": {},
        "last_updated": "",
        "state_loaded": False,
        "chain_symbols": "BTC,ETH,SOL,BNB,AVAX",
        "mcp_enabled": True,
        "newsdata_enabled": True,
        "newsdata_api_key": os.getenv("NEWSDATA_API_KEY", "pub_a11207fc26e8474f97ae00a16796e714"),
        "mcp_sources": {
            "tavily": True,
            "exa": False,
            "firecrawl": False,
            "github": False,
            "brave": False
        },
        "mcp_exa_url": os.getenv("MCP_EXA_URL", ""),
        "mcp_firecrawl_url": os.getenv("MCP_FIRECRAWL_URL", ""),
        "mcp_exa_tool_name": os.getenv("MCP_EXA_TOOL_NAME", "exa-search"),
        "mcp_firecrawl_tool_name": os.getenv("MCP_FIRECRAWL_TOOL_NAME", "firecrawl-search"),
        "mcp_exa_query_param": os.getenv("MCP_EXA_QUERY_PARAM", "query"),
        "mcp_firecrawl_query_param": os.getenv("MCP_FIRECRAWL_QUERY_PARAM", "query")
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

if "initialized" not in st.session_state:
    init_session_state()
    st.session_state.initialized = True

WALLET_COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "components", "wallet_auth")
wallet_auth_component = components.declare_component("wallet_auth", path=WALLET_COMPONENT_PATH)

# 如果没有钱包地址，清空连接状态提示
if not st.session_state.wallet_address:
    st.session_state.wallet_status = ""
    st.session_state.wallet_auth_warning = ""

def _get_query_params() -> dict:
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()

def _get_query_value(params: dict, key: str) -> str:
    val = params.get(key, "")
    if isinstance(val, list):
        return val[0] if val else ""
    return val or ""

def _clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()

def _extract_siwe_field(message: str, key: str) -> str:
    if not message:
        return ""
    prefix = f"{key}:"
    for line in message.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""

def _verify_signature(address: str, signature: str, nonce: str, message: str) -> bool:
    if not (Account and encode_defunct):
        return False
    if not (address and signature and nonce and message):
        return False
    try:
        msg = encode_defunct(text=message)
        recovered = Account.recover_message(msg, signature=signature)
        msg_nonce = _extract_siwe_field(message, "Nonce")
        chain_id = _extract_siwe_field(message, "Chain ID")
        if msg_nonce != nonce:
            return False
        if chain_id and chain_id != "1":
            return False
        return recovered.lower() == address.lower()
    except Exception as e:
        # 记录错误以便调试
        import traceback
        print(f"签名验证异常: {e}")
        print(traceback.format_exc())
        return False

def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("\n")
    meta_lines = []
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            break
        meta_lines.append(parts[i])
    meta: dict[str, str] = {}
    for line in meta_lines:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
        return meta

@st.cache_data(ttl=300, show_spinner=False)
def load_skills() -> tuple[list[dict], list[dict]]:
    skills_dir = os.path.join(os.path.dirname(__file__), "skills")
    if not os.path.exists(skills_dir):
        return [], []
    skills = []
    blocked = []
    for name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.exists(skill_path):
            continue
        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        meta = _parse_frontmatter(content)
        body = content
        if content.startswith("---"):
            try:
                body = content.split("---", 2)[2].strip()
            except Exception:
                body = content
        skill_name = meta.get("name") or name
        desc = meta.get("description", "")
        requires_env = meta.get("requires_env", "")
        missing = []
        if requires_env:
            for k in re.split(r"[,; ]+", requires_env):
                k = k.strip()
                if not k:
                    continue
                if not os.getenv(k):
                    missing.append(k)
        item = {
            "name": skill_name,
            "description": desc,
            "body": body,
            "missing_env": missing
        }
        if missing:
            blocked.append(item)
        else:
            skills.append(item)
    return skills, blocked

def _apply_skill(prompt: str, skill_map: dict, skill_name: str) -> str:
    if not skill_name:
        return prompt
    skill = skill_map.get(skill_name)
    if not skill:
        return prompt
    return f"{prompt}\n\n【技能】{skill.get('name','')}\n{skill.get('body','')}"

if BaseTool and ToolResult:
    class WalletVerifyTool(BaseTool):
        name: str = "wallet_verify"
        description: str = "Verify SIWE signature and nonce binding"
        parameters: dict = {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "signature": {"type": "string"},
                "nonce": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["address", "signature", "nonce", "message"]
        }

        async def execute(self, address: str, signature: str, nonce: str, message: str, **kwargs):
            if not (Account and encode_defunct):
                return ToolResult(error="缺少 eth_account，无法验证签名")

            # 验证参数完整性
            if not address:
                return ToolResult(output={"ok": False}, error="钱包地址为空")
            if not signature:
                return ToolResult(output={"ok": False}, error="签名为空")
            if not nonce:
                return ToolResult(output={"ok": False}, error="Nonce 为空")
            if not message:
                return ToolResult(output={"ok": False}, error="签名消息为空")

            # 验证签名
            try:
                msg = encode_defunct(text=message)
                recovered = Account.recover_message(msg, signature=signature)
                msg_nonce = _extract_siwe_field(message, "Nonce")
                chain_id = _extract_siwe_field(message, "Chain ID")

                # 检查 nonce 是否匹配
                if msg_nonce != nonce:
                    return ToolResult(output={"ok": False}, error=f"Nonce 不匹配: 消息中={msg_nonce}, 期望={nonce}")

                # 检查链 ID
                if chain_id and chain_id != "1":
                    return ToolResult(output={"ok": False}, error=f"链 ID 不匹配: {chain_id} (仅支持以太坊主网)")

                # 检查地址是否匹配
                if recovered.lower() != address.lower():
                    return ToolResult(output={"ok": False}, error=f"签名地址不匹配: 恢复={recovered}, 期望={address}")

                return ToolResult(output={"ok": True})
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"签名验证异常: {e}\n{error_detail}")
                return ToolResult(output={"ok": False}, error=f"签名验证异常: {str(e)}")
else:
    WalletVerifyTool = None

# 处理前端钱包签名回传
params = _get_query_params()
qp_addr = _get_query_value(params, "wallet_address")
qp_sig = _get_query_value(params, "wallet_signature")
qp_nonce = _get_query_value(params, "wallet_nonce")
qp_msg = _get_query_value(params, "wallet_message")
qp_err = _get_query_value(params, "wallet_error")
qp_status = _get_query_value(params, "wallet_status")
qp_origin = _get_query_value(params, "wallet_origin")
qp_domain = _get_query_value(params, "wallet_domain")
if qp_addr and not qp_sig:
    st.session_state.wallet_address = qp_addr
    if qp_origin:
        st.session_state.wallet_origin = qp_origin
    if qp_domain:
        st.session_state.wallet_domain = qp_domain
    st.session_state.wallet_status = qp_status or "已连接，等待签名"
    _clear_query_params()
elif qp_addr and qp_sig and qp_nonce and (qp_msg or st.session_state.wallet_message):
    st.session_state.wallet_address = qp_addr
    st.session_state.wallet_nonce = qp_nonce
    if Account is None or encode_defunct is None:
        st.session_state.wallet_authed = True
        st.session_state.wallet_auth_error = ""
        st.session_state.wallet_auth_warning = "已连接但未验证签名（缺少 eth_account）。请安装 web3 以启用验证"
    else:
        try:
            import anyio
            if WalletVerifyTool is None:
                st.session_state.wallet_authed = False
                st.session_state.wallet_auth_error = "SpoonOS Tool 不可用，请检查 spoon-ai-sdk 安装"
                st.session_state.wallet_auth_warning = ""
                _clear_query_params()
            else:
                tool = WalletVerifyTool()
            # 优先使用 URL 参数中的 wallet_message，如果没有则使用 session state
            msg = qp_msg or st.session_state.wallet_message or ""
            if not msg:
                st.session_state.wallet_auth_error = "签名消息不存在，请重新生成挑战并签名"
                st.session_state.wallet_authed = False
                st.session_state.wallet_auth_warning = ""
                _clear_query_params()
            else:
                # 保存消息到 session state 以便后续使用
                st.session_state.wallet_message = msg
                result = anyio.run(
                    tool.execute,
                    qp_addr,
                    qp_sig,
                    qp_nonce,
                    msg
                )
                if isinstance(result, ToolResult) and result.error:
                    st.session_state.wallet_authed = False
                    st.session_state.wallet_auth_error = result.error
                    st.session_state.wallet_auth_warning = ""
                else:
                    st.session_state.wallet_address = qp_addr
                    st.session_state.wallet_authed = True
                    st.session_state.wallet_auth_error = ""
                    st.session_state.wallet_auth_warning = ""
        except Exception as e:
            st.session_state.wallet_authed = False
            st.session_state.wallet_auth_error = f"签名验证异常：{e}"
            st.session_state.wallet_auth_warning = ""
    _clear_query_params()
elif qp_status:
    st.session_state.wallet_status = qp_status
    _clear_query_params()
elif qp_err:
    st.session_state.wallet_auth_error = qp_err
    st.session_state.wallet_auth_warning = ""
    _clear_query_params()

# ==================== 配置检查 ====================
REQUIRED_KEYS = ["DEEPSEEK_API_KEY", "ARK_API_KEY", "HUNYUAN_API_KEY"]
OPTIONAL_KEYS = [
    "TAVILY_API_KEY",
    "GITHUB_TOKEN",
    "BRAVE_API_KEY",
    "ETHERSCAN_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "RPC_URL",
    "MCP_EXA_URL",
    "MCP_FIRECRAWL_URL",
    "NEWSDATA_API_KEY",
    "COINMARKETCAP_API_KEY",
    "COINMARKETCAP_BASE_URL",
    "THEGRAPH_UNISWAP_V3",
    "THEGRAPH_AAVE_V3"
]
 

def is_valid_mcp_content(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    lowered = value.lower()
    if "失败" in value or "error" in lowered or "未配置" in value or "缺少" in value:
        return False
    return len(value.strip()) > 80

def get_mcp_source_status(name: str) -> tuple[str, str, str]:
    if not st.session_state.mcp_enabled:
        return (name, "未启用", "info")
    if not st.session_state.mcp_sources.get(name):
        return (name, "未启用", "info")
    if name == "tavily" and not os.getenv("TAVILY_API_KEY"):
        return (name, "缺少 TAVILY_API_KEY", "error")
    if name == "github" and not os.getenv("GITHUB_TOKEN"):
        return (name, "缺少 GITHUB_TOKEN", "error")
    if name == "brave" and not os.getenv("BRAVE_API_KEY"):
        return (name, "缺少 BRAVE_API_KEY", "error")
    if name == "exa" and not st.session_state.mcp_exa_url:
        return (name, "未配置 Exa MCP URL", "error")
    if name == "firecrawl" and not st.session_state.mcp_firecrawl_url:
        return (name, "未配置 Firecrawl MCP URL", "error")
    content = st.session_state.mcp_results.get(name)
    if is_valid_mcp_content(str(content)):
        return (name, "OK", "ok")
    if content:
        return (name, "失败/无有效内容", "warn")
    return (name, "无结果", "warn")

def get_newsdata_status() -> tuple[str, str, str]:
    if not st.session_state.newsdata_enabled:
        return ("NewsData.io", "未启用", "info")
    api_key = st.session_state.newsdata_api_key or os.getenv("NEWSDATA_API_KEY", "")
    if not api_key:
        return ("NewsData.io", "缺少 NEWSDATA_API_KEY", "error")
    if st.session_state.newsdata_items:
        return ("NewsData.io", f"OK（{len(st.session_state.newsdata_items)} 条）", "ok")
    return ("NewsData.io", "无结果/可能限流", "warn")

def get_coinmarketcap_status() -> tuple[str, str, str]:
    api_key = st.session_state.coinmarketcap_api_key or os.getenv("COINMARKETCAP_API_KEY", "")
    if not api_key:
        return ("CoinMarketCap", "缺少 COINMARKETCAP_API_KEY", "error")
    quotes = {}
    if isinstance(st.session_state.coinmarketcap_data, dict):
        quotes = st.session_state.coinmarketcap_data.get("quotes", {}) or {}
        err = st.session_state.coinmarketcap_data.get("error") or st.session_state.coinmarketcap_data.get("quotes_error", "")
        if err:
            return ("CoinMarketCap", f"失败：{err}", "warn")
    if quotes:
        return ("CoinMarketCap", "OK", "ok")
    return ("CoinMarketCap", "无数据/未刷新", "warn")

def get_source_health() -> dict:
    health = {}
    health["newsdata"] = {"priority": 1, "status": get_newsdata_status()}
    health["coinmarketcap"] = {"priority": 1, "status": get_coinmarketcap_status()}
    health["tavily"] = {"priority": 2, "status": get_mcp_source_status("tavily")}
    health["exa"] = {"priority": 3, "status": get_mcp_source_status("exa")}
    health["firecrawl"] = {"priority": 4, "status": get_mcp_source_status("firecrawl")}
    health["github"] = {"priority": 5, "status": get_mcp_source_status("github")}
    health["brave"] = {"priority": 6, "status": get_mcp_source_status("brave")}
    return health

def run_mcp_self_check() -> list[str]:
    results: list[str] = []

    # 检查 node / npx
    node_ok = False
    try:
        node_ver = subprocess.run(["node", "-v"], capture_output=True, text=True, timeout=8, check=True)
        results.append(f"node ✅ {node_ver.stdout.strip()}")
        node_ok = True
    except FileNotFoundError:
        results.append("node ❌ 未安装（无法运行 npx）")
    except Exception as e:
        results.append(f"node ❌ 检测失败：{e}")

    npx_ok = False
    if node_ok:
        try:
            npx_ver = subprocess.run(["npx", "-v"], capture_output=True, text=True, timeout=8, check=True)
            results.append(f"npx ✅ {npx_ver.stdout.strip()}")
            npx_ok = True
        except Exception as e:
            results.append(f"npx ❌ 检测失败：{e}")

    # Tavily MCP
    if st.session_state.mcp_sources.get("tavily"):
        if not os.getenv("TAVILY_API_KEY"):
            results.append("tavily ❌ 缺少 TAVILY_API_KEY")
        elif not MCPTool:
            results.append("tavily ❌ MCPTool 不可用")
        elif not npx_ok:
            results.append("tavily ❌ npx 不可用")
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "tavily-mcp"],
                    "env": {"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")}
                }
                tool = MCPTool(
                    name="tavily-search",
                    description="Tavily search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                resp = anyio.run(tool.execute, **{"query": "crypto market news"})
                results.append(f"tavily ✅ 返回长度 {len(str(resp))}")
            except Exception as e:
                results.append(f"tavily ❌ 调用失败：{e}")

    # GitHub MCP
    if st.session_state.mcp_sources.get("github"):
        if not os.getenv("GITHUB_TOKEN"):
            results.append("github ❌ 缺少 GITHUB_TOKEN")
        elif not MCPTool:
            results.append("github ❌ MCPTool 不可用")
        elif not npx_ok:
            results.append("github ❌ npx 不可用")
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
                }
                tool = MCPTool(
                    name="github-search",
                    description="GitHub search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                resp = anyio.run(tool.execute, **{"query": "spoonos streamlit"})
                results.append(f"github ✅ 返回长度 {len(str(resp))}")
            except Exception as e:
                results.append(f"github ❌ 调用失败：{e}")

    # Brave Search MCP
    if st.session_state.mcp_sources.get("brave"):
        if not os.getenv("BRAVE_API_KEY"):
            results.append("brave ❌ 缺少 BRAVE_API_KEY")
        elif not MCPTool:
            results.append("brave ❌ MCPTool 不可用")
        elif not npx_ok:
            results.append("brave ❌ npx 不可用")
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "@modelcontextprotocol/server-brave-search"],
                    "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
                }
                tool = MCPTool(
                    name="brave-search",
                    description="Brave search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                resp = anyio.run(tool.execute, **{"query": "crypto market news"})
                results.append(f"brave ✅ 返回长度 {len(str(resp))}")
            except Exception as e:
                results.append(f"brave ❌ 调用失败：{e}")

    # Exa MCP
    if st.session_state.mcp_sources.get("exa"):
        if not st.session_state.mcp_exa_url:
            results.append("exa ❌ 未配置 MCP URL")
        elif not MCPTool:
            results.append("exa ❌ MCPTool 不可用")
        else:
            try:
                mcp_config = {"url": st.session_state.mcp_exa_url, "transport": "sse"}
                tool = MCPTool(
                    name=st.session_state.mcp_exa_tool_name,
                    description="Exa search via MCP",
                    mcp_config=mcp_config
                )
                param = st.session_state.mcp_exa_query_param or "query"
                import anyio
                resp = anyio.run(tool.execute, **{param: "crypto market news"})
                results.append(f"exa ✅ 返回长度 {len(str(resp))}")
            except Exception as e:
                results.append(f"exa ❌ 调用失败：{e}")

    # Firecrawl MCP
    if st.session_state.mcp_sources.get("firecrawl"):
        if not st.session_state.mcp_firecrawl_url:
            results.append("firecrawl ❌ 未配置 MCP URL")
        elif not MCPTool:
            results.append("firecrawl ❌ MCPTool 不可用")
        else:
            try:
                mcp_config = {"url": st.session_state.mcp_firecrawl_url, "transport": "sse"}
                tool = MCPTool(
                    name=st.session_state.mcp_firecrawl_tool_name,
                    description="Firecrawl via MCP",
                    mcp_config=mcp_config
                )
                param = st.session_state.mcp_firecrawl_query_param or "query"
                import anyio
                resp = anyio.run(tool.execute, **{param: "crypto market news"})
                results.append(f"firecrawl ✅ 返回长度 {len(str(resp))}")
            except Exception as e:
                results.append(f"firecrawl ❌ 调用失败：{e}")

    if not results:
        results.append("未启用任何 MCP 来源")
    return results

# ==================== 左侧边栏 ====================
with st.sidebar:
    st.title("设置")
    
    # 钱包认证
    st.header("🔐 钱包认证")
    if st.session_state.wallet_authed:
        st.success("✅ 已认证")
        addr = st.session_state.wallet_address or ""
        if addr:
            st.caption(f"地址：{addr[:6]}...{addr[-4:]}")
        if st.session_state.wallet_auth_warning:
            st.warning(st.session_state.wallet_auth_warning)
        if st.button("断开钱包", type="secondary", use_container_width=True):
            st.session_state.wallet_address = None
            st.session_state.wallet_authed = False
            st.session_state.wallet_nonce = ""
            st.session_state.wallet_signature_input = ""
            st.session_state.wallet_auth_error = ""
            st.session_state.wallet_auth_warning = ""
            st.rerun()
    else:
        if not st.session_state.wallet_nonce:
            import secrets
            st.session_state.wallet_nonce = secrets.token_hex(16)

        statement = "Sign in to My AI Lab"
        comp_value = wallet_auth_component(
            nonce=st.session_state.wallet_nonce,
            statement=statement,
            key="wallet_auth_component"
        )
        if isinstance(comp_value, dict) and comp_value.get("address") and comp_value.get("signature"):
            st.session_state.wallet_address = comp_value.get("address")
            st.session_state.wallet_message = comp_value.get("message", "")
            try:
                import anyio
                if WalletVerifyTool is None:
                    st.session_state.wallet_auth_error = "SpoonOS Tool 不可用，请检查 spoon-ai-sdk 安装"
                else:
                    tool = WalletVerifyTool()
                    result = anyio.run(
                        tool.execute,
                        comp_value.get("address"),
                        comp_value.get("signature"),
                        comp_value.get("nonce"),
                        comp_value.get("message")
                    )
                    if isinstance(result, ToolResult) and result.error:
                        st.session_state.wallet_authed = False
                        st.session_state.wallet_auth_error = result.error
                    else:
                        st.session_state.wallet_authed = True
                        st.session_state.wallet_auth_error = ""
                        st.success("✅ 签名认证成功")
                        st.rerun()
            except Exception as e:
                st.session_state.wallet_auth_error = f"签名验证异常：{e}"
            if st.session_state.wallet_status:
                st.info(st.session_state.wallet_status)
            if st.session_state.wallet_auth_error:
                st.error(st.session_state.wallet_auth_error)
        if st.session_state.wallet_auth_error:
            st.error(st.session_state.wallet_auth_error)
    
    st.divider()

    with st.expander("⚙️ 设置（折叠）", expanded=False):
        st.caption("聊天模式：三模型顺序（豆包 → 元宝 → DeepSeek）")

        with st.expander("🧩 配置检查（折叠）", expanded=False):
            st.caption(
                "最小可用配置路径：必需 Key + CMC（价格）+ NewsData（新闻）。"
                "MCP/Exa/Firecrawl 为增强项，未配置不影响核心功能。"
            )
            if st.button("🧪 豆包一键测试", use_container_width=True):
                try:
                    api_key = os.getenv("ARK_API_KEY") or os.getenv("DOUBAO_API_KEY")
                    base_url = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/responses")
                    model = os.getenv("DOUBAO_MODEL", "ep-20260130214742-t9vlx")
                    if base_url.endswith("/api/v3"):
                        base_url = base_url + "/chat/completions"
                    if base_url.endswith("/responses"):
                        payload = {
                            "model": model,
                            "input": [{"role": "user", "content": [{"type": "input_text", "text": "ping"}]}],
                            "max_output_tokens": 128
                        }
                    else:
                        payload = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
                    resp = requests.post(base_url, headers=headers, json=payload, timeout=20)
                    st.session_state.doubao_debug = f"status={resp.status_code} url={base_url} body={resp.text[:300]}"
                except Exception as e:
                    st.session_state.doubao_debug = f"error={e}"
            if st.session_state.doubao_debug:
                st.code(st.session_state.doubao_debug)

            def _status_line(name: str, ok: bool, tag: str = ""):
                dot = "🟢" if ok else "🔴"
                suffix = f" · {tag}" if tag else ""
                st.write(f"{dot} {name}{suffix}")

            st.markdown("**必需项**")
            col_a, col_b = st.columns(2)
            for idx, key in enumerate(REQUIRED_KEYS):
                target = col_a if idx % 2 == 0 else col_b
                with target:
                    _status_line(key, bool(os.getenv(key)))

            st.markdown("**可选项**")
            col_c, col_d = st.columns(2)
            for idx, key in enumerate(OPTIONAL_KEYS):
                target = col_c if idx % 2 == 0 else col_d
                with target:
                    _status_line(key, bool(os.getenv(key)))

        with st.expander("📰 数据源设置（折叠）", expanded=False):
            st.caption("设置链上数据与新闻来源")
            st.session_state.chain_symbols = st.text_input(
                "链上关注币种（逗号分隔）",
                value=st.session_state.chain_symbols
            )
            st.divider()
            st.caption("SpoonOS MCP 搜索（可选）")
            st.session_state.mcp_enabled = st.checkbox("启用 MCP 搜索", value=st.session_state.mcp_enabled)
            st.session_state.mcp_sources["tavily"] = st.checkbox("Tavily 搜索（推荐）", value=st.session_state.mcp_sources["tavily"])
            st.session_state.mcp_sources["github"] = st.checkbox("GitHub 搜索（MCP）", value=st.session_state.mcp_sources["github"])
            st.session_state.mcp_sources["brave"] = st.checkbox("Brave 搜索（MCP）", value=st.session_state.mcp_sources["brave"])
            st.session_state.mcp_sources["exa"] = st.checkbox("Exa 搜索", value=st.session_state.mcp_sources["exa"])
            st.session_state.mcp_sources["firecrawl"] = st.checkbox("Firecrawl 抓取", value=st.session_state.mcp_sources["firecrawl"])
            st.divider()
            st.caption("NewsData.io 新闻（非 MCP）")
            st.session_state.newsdata_enabled = st.checkbox("启用 NewsData.io", value=st.session_state.newsdata_enabled)
            st.session_state.newsdata_api_key = st.text_input(
                "NewsData.io API Key",
                value=st.session_state.newsdata_api_key,
                type="password"
            )
            st.session_state.coinmarketcap_api_key = st.text_input(
                "CoinMarketCap API Key（可选，价格来源）",
                value=st.session_state.coinmarketcap_api_key,
                type="password"
            )
            col_cmc1, col_cmc2 = st.columns(2)
            with col_cmc1:
                if st.button("↩️ 从 .env 重新填充 CMC Key", use_container_width=True):
                    st.session_state.coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY", "")
                    st.success("已从 .env 重新填充")
            with col_cmc2:
                if st.button("🔍 测试 CMC Key", use_container_width=True):
                    try:
                        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
                        headers = {"X-CMC_PRO_API_KEY": st.session_state.coinmarketcap_api_key, "Accept": "application/json"}
                        params = {"symbol": "BTC,ETH,SOL,BNB", "convert": "USD"}
                        resp = requests.get(url, params=params, headers=headers, timeout=15)
                        st.session_state.cmc_debug = f"status={resp.status_code} body={resp.text[:300]}"
                    except Exception as e:
                        st.session_state.cmc_debug = f"error={e}"
            if st.session_state.cmc_debug:
                st.code(st.session_state.cmc_debug)

            st.markdown("**Exa MCP 配置（可选）**")
            st.session_state.mcp_exa_url = st.text_input(
                "Exa MCP URL（SSE/HTTP）",
                value=st.session_state.mcp_exa_url
            )
            st.session_state.mcp_exa_tool_name = st.text_input(
                "Exa Tool 名称",
                value=st.session_state.mcp_exa_tool_name
            )
            st.session_state.mcp_exa_query_param = st.text_input(
                "Exa 查询参数名",
                value=st.session_state.mcp_exa_query_param
            )

            st.markdown("**Firecrawl MCP 配置（可选）**")
            st.session_state.mcp_firecrawl_url = st.text_input(
                "Firecrawl MCP URL（SSE/HTTP）",
                value=st.session_state.mcp_firecrawl_url
            )
            st.session_state.mcp_firecrawl_tool_name = st.text_input(
                "Firecrawl Tool 名称",
                value=st.session_state.mcp_firecrawl_tool_name
            )
            st.session_state.mcp_firecrawl_query_param = st.text_input(
                "Firecrawl 查询参数名",
                value=st.session_state.mcp_firecrawl_query_param
            )

        with st.expander("🛰️ 信息源状态（折叠）", expanded=False):
            statuses = [
                get_coinmarketcap_status(),
                get_newsdata_status(),
                get_mcp_source_status("tavily"),
                get_mcp_source_status("exa"),
                get_mcp_source_status("firecrawl")
            ]
            def _status_dot(level: str) -> str:
                if level == "ok":
                    return "🟢"
                if level == "warn":
                    return "🟡"
                if level == "error":
                    return "🔴"
                return "⚪"
            for name, msg, level in statuses:
                st.write(f"{_status_dot(level)} {name}：{msg}")

        with st.expander("🧹 缓存与启动（折叠）", expanded=False):
            st.session_state.load_dashboard_cache = st.checkbox(
                "启动时加载上次看板",
                value=st.session_state.load_dashboard_cache
            )
            st.session_state.auto_refresh_on_load = st.checkbox(
                "首次自动刷新看板（可能较慢）",
                value=st.session_state.auto_refresh_on_load
            )
            if st.button("清空看板缓存", use_container_width=True):
                try:
                    if os.path.exists(DASHBOARD_FILE):
                        os.remove(DASHBOARD_FILE)
                except Exception:
                    pass
                st.session_state.chain_data = None
                st.session_state.mcp_results = {}
                st.session_state.cards = []
                st.session_state.chief_summary = ""
                st.session_state.news_cards = []
                st.session_state.newsdata_items = []
                st.session_state.timely_news_cards = []
                st.session_state.hot_news_cards = []
                st.session_state.news_summary = ""
                st.session_state.chain_errors = []
                st.session_state.mcp_errors = []
                st.session_state.news_errors = []
                st.session_state.last_updated = ""
                st.success("已清空看板缓存")
                st.rerun()

        with st.expander("🧪 调试与自检（折叠）", expanded=False):
            if st.button("🧪 MCP 一键自检", use_container_width=True):
                st.session_state.mcp_self_check = run_mcp_self_check()
            if st.session_state.mcp_self_check:
                st.code("\n".join(st.session_state.mcp_self_check))


# ==================== 主界面 ====================
st.title("🧪 我的私人实验室")
st.caption("欢迎来到你的 AI 实验室！连接钱包后开始与 AI 对话吧。")

# 显示钱包状态（避免重复提示）
if st.session_state.wallet_authed and st.session_state.wallet_address:
    st.success(f"✅ 钱包已连接: `{st.session_state.wallet_address}`")
else:
    if not st.session_state.wallet_address:
        st.warning("⚠️ 请先在左侧边栏连接钱包")
    else:
        st.warning("⚠️ 请先完成钱包签名认证后再使用功能")

st.divider()

# ==================== 主界面分区 ====================
if not st.session_state.wallet_authed:
    st.stop()

tab_data, tab_chat, tab_square = st.tabs(["🧭 情报看板", "🧠 策略议事厅", "🧩 广场自由讨论"])

STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
DASHBOARD_FILE = os.path.join(STATE_DIR, "dashboard_state.json")
CHAT_FILE = os.path.join(STATE_DIR, "chat_state.json")
SQUARE_FILE = os.path.join(STATE_DIR, "square_posts.json")

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(path: str, data: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_dashboard_snapshot() -> None:
    save_json(DASHBOARD_FILE, {
        "chain_data": st.session_state.chain_data or {},
        "defillama_data": st.session_state.defillama_data or {},
        "coinmarketcap_data": st.session_state.coinmarketcap_data or {},
        "thegraph_data": st.session_state.thegraph_data or {},
        "mcp_results": st.session_state.mcp_results or {},
        "cards": st.session_state.cards or [],
        "chief_summary": st.session_state.chief_summary or "",
        "news_cards": st.session_state.news_cards or [],
        "newsdata_items": st.session_state.newsdata_items or [],
        "timely_news_cards": st.session_state.timely_news_cards or [],
        "hot_news_cards": st.session_state.hot_news_cards or [],
        "news_summary": st.session_state.news_summary or "",
        "errors": {
            "chain": st.session_state.chain_errors or [],
            "mcp": st.session_state.mcp_errors or [],
            "news": st.session_state.news_errors or []
        },
        "analysis_text": st.session_state.analysis_text or "",
        "last_updated": st.session_state.last_updated
    })

if not st.session_state.state_loaded:
    if st.session_state.load_dashboard_cache:
        persisted = load_json(DASHBOARD_FILE)
        if persisted:
            st.session_state.chain_data = persisted.get("chain_data", st.session_state.chain_data)
            st.session_state.mcp_results = persisted.get("mcp_results", st.session_state.mcp_results)
            st.session_state.cards = persisted.get("cards", st.session_state.cards)
            st.session_state.chief_summary = persisted.get("chief_summary", st.session_state.chief_summary)
            st.session_state.news_cards = persisted.get("news_cards", st.session_state.news_cards)
            st.session_state.newsdata_items = persisted.get("newsdata_items", st.session_state.newsdata_items)
            st.session_state.timely_news_cards = persisted.get("timely_news_cards", st.session_state.timely_news_cards)
            st.session_state.hot_news_cards = persisted.get("hot_news_cards", st.session_state.hot_news_cards)
            st.session_state.news_summary = persisted.get("news_summary", st.session_state.news_summary)
            errors = persisted.get("errors", {})
            if isinstance(errors, dict):
                st.session_state.chain_errors = errors.get("chain", st.session_state.chain_errors)
                st.session_state.mcp_errors = errors.get("mcp", st.session_state.mcp_errors)
                st.session_state.news_errors = [
                    e for e in errors.get("news", st.session_state.news_errors)
                    if "本质卡片" not in str(e)
                ]
            st.session_state.last_updated = persisted.get("last_updated", st.session_state.last_updated)
    square_state = load_json(SQUARE_FILE)
    if square_state.get("posts"):
        st.session_state.square_posts = square_state.get("posts", st.session_state.square_posts)
    st.session_state.state_loaded = True

def http_get_with_retry(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 20, retries: int = 2):
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_err = e
            continue
    raise last_err

def fetch_chain_data(symbols: list[str]) -> dict:
    # 已移除 CoinGecko 作为价格源（避免 400 报错）
    data = {}

    # 可选：如果配置了 RPC_URL，尝试获取 gas price
    gas_price = None
    try:
        from web3 import Web3
        rpc_url = os.getenv("RPC_URL")
        if rpc_url:
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            if w3.is_connected():
                gas_price = w3.eth.gas_price
    except Exception:
        gas_price = None

    etherscan_data = {}
    etherscan_key = os.getenv("ETHERSCAN_API_KEY")
    etherscan_base = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/api")
    if etherscan_key:
        try:
            gas_resp = http_get_with_retry(
                etherscan_base,
                params={"module": "gastracker", "action": "gasoracle", "apikey": etherscan_key},
                timeout=20,
                retries=1
            ).json()
            etherscan_data["gasoracle"] = gas_resp.get("result", {})
        except Exception:
            etherscan_data["gasoracle"] = {}
        try:
            price_resp = http_get_with_retry(
                etherscan_base,
                params={"module": "stats", "action": "ethprice", "apikey": etherscan_key},
                timeout=20,
                retries=1
            ).json()
            etherscan_data["ethprice"] = price_resp.get("result", {})
        except Exception:
            etherscan_data["ethprice"] = {}

    alpha_vantage = {}
    alpha_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if alpha_key:
        # 控制请求次数，避免免费额度过快用尽
        for sym in symbols[:2]:
            try:
                av_resp = http_get_with_retry(
                    "https://www.alphavantage.co/query",
                    params={
                        "function": "DIGITAL_CURRENCY_DAILY",
                        "symbol": sym.upper(),
                        "market": "USD",
                        "apikey": alpha_key
                    },
                    timeout=20,
                    retries=1
                ).json()
                series = av_resp.get("Time Series (Digital Currency Daily)", {})
                if series:
                    latest_date = sorted(series.keys())[-1]
                    latest = series.get(latest_date, {})
                    alpha_vantage[sym.upper()] = {
                        "date": latest_date,
                        "close_usd": latest.get("4a. close (USD)")
                    }
            except Exception:
                continue

    return {
        "prices": data,
        "gas_price_wei": gas_price,
        "etherscan": etherscan_data,
        "alpha_vantage": alpha_vantage
    }

def fetch_defillama_data() -> dict:
    """获取 DeFiLlama 数据（TVL、协议排名等）- 免费无需 API Key"""
    result = {}
    try:
        # 获取各链 TVL
        tvl_resp = http_get_with_retry("https://api.llama.fi/v2/chains", timeout=15, retries=1)
        chains = tvl_resp.json()
        # 只保留主要链的数据
        main_chains = ["Ethereum", "BSC", "Solana", "Avalanche", "Polygon"]
        result["chain_tvl"] = {
            chain["name"]: {
                "tvl": chain.get("tvl"),
                "tokenSymbol": chain.get("tokenSymbol"),
                "cmcId": chain.get("cmcId")
            }
            for chain in chains if chain.get("name") in main_chains
        }
    except Exception as e:
        result["chain_tvl"] = {}
        result["chain_tvl_error"] = str(e)

    try:
        # 获取 Top 10 协议
        protocols_resp = http_get_with_retry("https://api.llama.fi/protocols", timeout=15, retries=1)
        protocols = protocols_resp.json()
        result["top_protocols"] = [
            {
                "name": p.get("name"),
                "tvl": p.get("tvl"),
                "chain": p.get("chain"),
                "change_1d": p.get("change_1d"),
                "category": p.get("category")
            }
            for p in protocols[:10]
        ]
    except Exception as e:
        result["top_protocols"] = []
        result["top_protocols_error"] = str(e)

    return result

def fetch_coinmarketcap_data(symbols: list[str]) -> dict:
    """获取 CoinMarketCap 数据（市值排名、社交媒体指标等）"""
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    if not api_key or api_key == "your-cmc-api-key-here":
        return {"error": "未配置 COINMARKETCAP_API_KEY"}

    result = {}
    base_url = os.getenv("COINMARKETCAP_BASE_URL", "https://pro-api.coinmarketcap.com/v1")

    # 符号映射（CMC 使用大写符号）
    symbol_map = {
        "BTC": "BTC",
        "ETH": "ETH",
        "SOL": "SOL",
        "BNB": "BNB",
        "AVAX": "AVAX"
    }

    cmc_symbols = [symbol_map.get(s.upper()) for s in symbols if symbol_map.get(s.upper())]
    if not cmc_symbols:
        return {"error": "无有效币种"}

    try:
        # 获取最新行情数据
        url = f"{base_url}/cryptocurrency/quotes/latest"
        params = {
            "symbol": ",".join(cmc_symbols),
            "convert": "USD"
        }
        resp_headers = {"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"}
        resp = http_get_with_retry(url, params=params, headers=resp_headers, timeout=20, retries=1)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status", {}).get("error_code") == 0:
            quotes = data.get("data", {})
            result["quotes"] = {}
            for symbol, info in quotes.items():
                quote = info.get("quote", {}).get("USD", {})
                result["quotes"][symbol] = {
                    "price": quote.get("price"),
                    "volume_24h": quote.get("volume_24h"),
                    "volume_change_24h": quote.get("volume_change_24h"),
                    "percent_change_1h": quote.get("percent_change_1h"),
                    "percent_change_24h": quote.get("percent_change_24h"),
                    "percent_change_7d": quote.get("percent_change_7d"),
                    "market_cap": quote.get("market_cap"),
                    "market_cap_dominance": quote.get("market_cap_dominance"),
                    "circulating_supply": info.get("circulating_supply"),
                    "total_supply": info.get("total_supply"),
                    "max_supply": info.get("max_supply"),
                    "cmc_rank": info.get("cmc_rank")
                }
        else:
            result["error"] = data.get("status", {}).get("error_message", "CMC 返回错误")
    except Exception as e:
        result["quotes_error"] = str(e)
        result["quotes"] = {}

    return result

def fetch_thegraph_data() -> dict:
    """获取 The Graph 子图数据（Uniswap, Aave, Compound）"""
    result = {}

    # Uniswap V3 数据
    try:
        uniswap_url = os.getenv("THEGRAPH_UNISWAP_V3", "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
        query = """
        {
          pools(first: 5, orderBy: totalValueLockedUSD, orderDirection: desc) {
            id
            token0 {
              symbol
            }
            token1 {
              symbol
            }
            totalValueLockedUSD
            volumeUSD
            feeTier
          }
        }
        """
        resp = requests.post(uniswap_url, json={"query": query}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and "pools" in data["data"]:
            result["uniswap_v3_pools"] = data["data"]["pools"]
    except Exception as e:
        result["uniswap_v3_error"] = str(e)
        result["uniswap_v3_pools"] = []

    # Aave V3 数据
    try:
        aave_url = os.getenv("THEGRAPH_AAVE_V3", "https://api.thegraph.com/subgraphs/name/aave/protocol-v3")
        query = """
        {
          reserves(first: 5, orderBy: totalLiquidity, orderDirection: desc) {
            symbol
            name
            totalLiquidity
            availableLiquidity
            totalDebt
            liquidityRate
            variableBorrowRate
          }
        }
        """
        resp = requests.post(aave_url, json={"query": query}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and "reserves" in data["data"]:
            result["aave_v3_reserves"] = data["data"]["reserves"]
    except Exception as e:
        result["aave_v3_error"] = str(e)
        result["aave_v3_reserves"] = []

    return result

# RSS 已移除（不稳定）

def build_search_query(symbols: list[str]) -> str:
    base = "crypto market news"
    if symbols:
        return f"{base} {' '.join(symbols)}"
    return base

def build_search_queries(symbols: list[str]) -> list[str]:
    base = build_search_query(symbols)
    topics = [
        base,
        "加密 市场 新闻",
        "比特币 以太坊 监管",
        "交易所 黑客 攻击",
        "crypto regulation policy crackdown",
        "bitcoin etf inflow outflow",
        "exchange hack exploit security incident",
        "defi tvl protocol ranking",
        "stablecoin depeg risk",
        "layer2 airdrop governance proposal"
    ]
    seen = set()
    uniq = []
    for q in topics:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq[:5]

def fetch_newsdata(query: str, api_key: str, language: str = "en") -> list[dict]:
    if not api_key:
        return []
    try:
        url = "https://newsdata.io/api/1/news"
        params = {
            "apikey": api_key,
            "q": query,
            "language": language,
            "size": 5
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        items = []
        if isinstance(results, list):
            for it in results:
                if not isinstance(it, dict):
                    continue
                items.append({
                    "title": it.get("title", ""),
                    "summary": it.get("description", "") or it.get("content", ""),
                    "source": it.get("source_id", "") or it.get("source_name", ""),
                    "link": it.get("link", ""),
                    "pubDate": it.get("pubDate", ""),
                    "language": language
                })
        return items
    except requests.RequestException as e:
        raise RuntimeError(f"⚠️ NewsData 请求失败：{e}") from e
    except Exception as e:
        raise RuntimeError(f"⚠️ NewsData 响应解析失败：{e}") from e

@st.cache_data(ttl=120, show_spinner=False)
def fetch_newsdata_multi(queries: list[str], api_key: str) -> list[dict]:
    items: list[dict] = []
    for q in queries:
        try:
            # 优先中文，再补英文
            items.extend(fetch_newsdata(q, api_key, language="zh"))
            items.extend(fetch_newsdata(q, api_key, language="en"))
        except Exception:
            continue
    # 去重（按标题）
    seen = set()
    uniq = []
    for it in items:
        title = (it.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        uniq.append(it)
    return uniq[:12]

def _parse_pubdate(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
    return None

def _is_today(value: str) -> bool:
    dt = _parse_pubdate(value)
    if not dt:
        return False
    return dt.date() == datetime.now().date()

def _score_news_item(item: dict) -> int:
    title = (item.get("title") or "").lower()
    summary = (item.get("summary") or "").lower()
    text = f"{title} {summary}"
    score = 0
    keywords = {
        "regulation": 4, "sec": 4, "policy": 3, "law": 3, "lawsuit": 3, "etf": 3,
        "hack": 5, "exploit": 5, "breach": 5, "attack": 4, "vulnerability": 4,
        "depeg": 4, "stablecoin": 3, "bank": 2, "exchange": 2
    }
    for k, w in keywords.items():
        if k in text:
            score += w
    if len(summary) > 120:
        score += 1
    return score

def _has_chinese(text: str) -> bool:
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)

def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "-"

def _fmt_usd(value: Any) -> str:
    try:
        v = float(value)
        if v >= 1_000_000_000:
            return f"${v/1_000_000_000:.2f}B"
        if v >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        return f"${v:,.2f}"
    except Exception:
        return "-"

def _fmt_price(symbol: str, value: Any) -> str:
    try:
        v = float(value)
        sym = (symbol or "").upper()
        if sym in {"SOL", "BNB"}:
            return f"{v:,.3f}"
        return f"{v:,.2f}"
    except Exception:
        return "-"

def build_news_cards(items: list[dict]) -> tuple[list[dict], list[dict]]:
    items = [it for it in items if isinstance(it, dict)]
    seen = set()
    uniq = []
    for it in items:
        title = (it.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        uniq.append(it)
    # 只保留当天新闻；若没有日期则不参与当日筛选
    today_items = [it for it in uniq if _is_today(it.get("pubDate", ""))]
    if today_items:
        uniq = today_items
    # 及时：按时间排序（中文优先）
    timely = sorted(
        uniq,
        key=lambda x: (
            0 if (x.get("language") == "zh" or _has_chinese(x.get("title", "") + x.get("summary", ""))) else 1,
            _parse_pubdate(x.get("pubDate", "")) or datetime.min
        ),
        reverse=True
    )
    # 重要：按关键字评分（中文优先）
    hot = sorted(
        uniq,
        key=lambda x: (_score_news_item(x), 1 if (x.get("language") == "zh" or _has_chinese(x.get("title", "") + x.get("summary", ""))) else 0),
        reverse=True
    )
    def to_card(it: dict) -> dict:
        return {
            "title": it.get("title", ""),
            "summary": (it.get("summary") or it.get("description") or "")[:140],
            "source": it.get("source", "") or it.get("source_id", ""),
            "link": it.get("link", ""),
            "pubDate": it.get("pubDate", "")
        }
    timely_cards = [to_card(it) for it in timely[:9]]
    hot_cards = [to_card(it) for it in hot[:9]]
    return timely_cards, hot_cards



@st.cache_data(ttl=300, show_spinner=False)
def fetch_chain_data_cached(
    symbols_str: str,
    etherscan_key: str,
    alpha_key: str,
    rpc_url: str
) -> dict:
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    return fetch_chain_data(symbols)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_newsdata_cached(queries: tuple[str, ...], api_key: str) -> list[dict]:
    return fetch_newsdata_multi(list(queries), api_key)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_defillama_cached() -> dict:
    return fetch_defillama_data()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_coinmarketcap_cached(symbols_str: str, api_key: str, base_url: str) -> dict:
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    if api_key:
        os.environ["COINMARKETCAP_API_KEY"] = api_key
    if base_url:
        os.environ["COINMARKETCAP_BASE_URL"] = base_url
    return fetch_coinmarketcap_data(symbols)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_thegraph_cached(uniswap_url: str, aave_url: str) -> dict:
    if uniswap_url:
        os.environ["THEGRAPH_UNISWAP_V3"] = uniswap_url
    if aave_url:
        os.environ["THEGRAPH_AAVE_V3"] = aave_url
    return fetch_thegraph_data()

def fetch_mcp_search(query: str) -> dict:
    if not st.session_state.mcp_enabled:
        return {}
    if not MCPTool:
        raise RuntimeError("MCPTool 不可用，请确认 spoon-ai-sdk 安装正常")

    results = {}

    # Tavily（推荐）
    if st.session_state.mcp_sources.get("tavily"):
        if not os.getenv("TAVILY_API_KEY"):
            results["tavily"] = "缺少 TAVILY_API_KEY"
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "tavily-mcp"],
                    "env": {"TAVILY_API_KEY": os.getenv("TAVILY_API_KEY")}
                }
                tool = MCPTool(
                    name="tavily-search",
                    description="Tavily search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                results["tavily"] = str(anyio.run(tool.execute, **{"query": query}))
            except Exception as e:
                results["tavily"] = f"失败: {e}"

    # GitHub
    if st.session_state.mcp_sources.get("github"):
        if not os.getenv("GITHUB_TOKEN"):
            results["github"] = "缺少 GITHUB_TOKEN"
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
                }
                tool = MCPTool(
                    name="github-search",
                    description="GitHub search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                results["github"] = str(anyio.run(tool.execute, **{"query": query}))
            except Exception as e:
                results["github"] = f"失败: {e}"

    # Brave Search
    if st.session_state.mcp_sources.get("brave"):
        if not os.getenv("BRAVE_API_KEY"):
            results["brave"] = "缺少 BRAVE_API_KEY"
        else:
            try:
                mcp_config = {
                    "command": "npx",
                    "args": ["--yes", "@modelcontextprotocol/server-brave-search"],
                    "env": {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
                }
                tool = MCPTool(
                    name="brave-search",
                    description="Brave search via MCP",
                    mcp_config=mcp_config
                )
                import anyio
                results["brave"] = str(anyio.run(tool.execute, **{"query": query}))
            except Exception as e:
                results["brave"] = f"失败: {e}"

    # Exa
    if st.session_state.mcp_sources.get("exa"):
        if not st.session_state.mcp_exa_url:
            results["exa"] = "未配置 Exa MCP URL"
        else:
            try:
                mcp_config = {"url": st.session_state.mcp_exa_url, "transport": "sse"}
                tool = MCPTool(
                    name=st.session_state.mcp_exa_tool_name,
                    description="Exa search via MCP",
                    mcp_config=mcp_config
                )
                param = st.session_state.mcp_exa_query_param or "query"
                import anyio
                results["exa"] = str(anyio.run(tool.execute, **{param: query}))
            except Exception as e:
                results["exa"] = f"失败: {e}"

    # Firecrawl
    if st.session_state.mcp_sources.get("firecrawl"):
        if not st.session_state.mcp_firecrawl_url:
            results["firecrawl"] = "未配置 Firecrawl MCP URL"
        else:
            try:
                mcp_config = {"url": st.session_state.mcp_firecrawl_url, "transport": "sse"}
                tool = MCPTool(
                    name=st.session_state.mcp_firecrawl_tool_name,
                    description="Firecrawl via MCP",
                    mcp_config=mcp_config
                )
                param = st.session_state.mcp_firecrawl_query_param or "query"
                import anyio
                results["firecrawl"] = str(anyio.run(tool.execute, **{param: query}))
            except Exception as e:
                results["firecrawl"] = f"失败: {e}"

    return results

def is_valid_mcp_content(value: str) -> bool:
    if not value or not isinstance(value, str):
        return False
    lowered = value.lower()
    if "失败" in value or "error" in lowered or "未配置" in value or "缺少" in value:
        return False
    return len(value.strip()) > 80

def filter_mcp_results(results: dict) -> dict:
    if not isinstance(results, dict):
        return {}
    filtered = {}
    for name, content in results.items():
        if is_valid_mcp_content(str(content)):
            filtered[name] = content
    return filtered

def get_mcp_source_status(name: str) -> tuple[str, str, str]:
    if not st.session_state.mcp_enabled:
        return (name, "未启用", "info")
    if not st.session_state.mcp_sources.get(name):
        return (name, "未启用", "info")
    if name == "tavily" and not os.getenv("TAVILY_API_KEY"):
        return (name, "缺少 TAVILY_API_KEY", "error")
    if name == "exa" and not st.session_state.mcp_exa_url:
        return (name, "未配置 Exa MCP URL", "error")
    if name == "firecrawl" and not st.session_state.mcp_firecrawl_url:
        return (name, "未配置 Firecrawl MCP URL", "error")
    content = st.session_state.mcp_results.get(name)
    if is_valid_mcp_content(str(content)):
        return (name, "OK", "ok")
    if content:
        return (name, "失败/无有效内容", "warn")
    return (name, "无结果", "warn")

def get_newsdata_status() -> tuple[str, str, str]:
    if not st.session_state.newsdata_enabled:
        return ("NewsData.io", "未启用", "info")
    api_key = st.session_state.newsdata_api_key or os.getenv("NEWSDATA_API_KEY", "")
    if not api_key:
        return ("NewsData.io", "缺少 NEWSDATA_API_KEY", "error")
    if st.session_state.newsdata_items:
        return ("NewsData.io", f"OK（{len(st.session_state.newsdata_items)} 条）", "ok")
    return ("NewsData.io", "无结果/可能限流", "warn")

def build_analysis_prompt(chain_data: dict, news_items: list[dict]) -> str:
    lines = ["你是链上与新闻分析师，请基于数据给出更详细的分析与建议。", ""]
    lines.append("链上数据：")
    prices = chain_data.get("prices", {})
    if isinstance(prices, dict):
        for coin_id, info in prices.items():
            if not isinstance(info, dict):
                continue
            price = info.get("usd")
            change = info.get("usd_24h_change")
            market_cap = info.get("usd_market_cap")
            if isinstance(change, (int, float)):
                lines.append(f"- {coin_id}: 价格 ${price}, 24h 变化 {change:.2f}%, 市值 ${market_cap}")
            else:
                lines.append(f"- {coin_id}: 价格 ${price}, 24h 变化 {change}, 市值 ${market_cap}")
    gas_price = chain_data.get("gas_price_wei")
    if gas_price:
        lines.append(f"- Gas Price: {gas_price} wei")
    else:
        lines.append("- Gas Price: 未获取（未配置 RPC 或获取失败）")
    etherscan = chain_data.get("etherscan", {})
    if isinstance(etherscan, dict) and etherscan.get("gasoracle"):
        g = etherscan["gasoracle"]
        if isinstance(g, dict):
            lines.append(f"- Etherscan Gas Oracle: Safe={g.get('SafeGasPrice')}  Propose={g.get('ProposeGasPrice')}  Fast={g.get('FastGasPrice')}")
    if isinstance(etherscan, dict) and etherscan.get("ethprice"):
        p = etherscan["ethprice"]
        if isinstance(p, dict):
            lines.append(f"- Etherscan ETH Price: ${p.get('ethusd')}  BTC={p.get('ethbtc')}")
    alpha_vantage = chain_data.get("alpha_vantage", {})
    if isinstance(alpha_vantage, dict) and alpha_vantage:
        lines.append("- Alpha Vantage 最新收盘价（USD）：")
        for sym, info in alpha_vantage.items():
            if isinstance(info, dict):
                lines.append(f"  - {sym}: {info.get('close_usd')} @ {info.get('date')}")
    lines.append("")
    lines.append("新闻摘要：")
    lines.append("- RSS 已移除，使用 NewsData/MCP 作为实时信息来源")
    if st.session_state.mcp_results:
        lines.append("")
        lines.append("实时搜索结果（MCP，多源）：")
        for name, content in st.session_state.mcp_results.items():
            lines.append(f"- 来源：{name}")
            lines.append(str(content)[:1200])
    if st.session_state.news_cards:
        lines.append("")
        lines.append("新闻要点（已提炼）：")
        for item in st.session_state.news_cards[:5]:
            title = item.get("title", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            lines.append(f"- {title}：{summary}（{source}）")
    if st.session_state.defillama_data:
        lines.append("")
        lines.append("DeFiLlama：")
        lines.append(json.dumps(st.session_state.defillama_data, ensure_ascii=False)[:1200])
    if st.session_state.coinmarketcap_data:
        lines.append("")
        lines.append("CoinMarketCap：")
        lines.append(json.dumps(st.session_state.coinmarketcap_data, ensure_ascii=False)[:1200])
    if st.session_state.thegraph_data:
        lines.append("")
        lines.append("The Graph：")
        lines.append(json.dumps(st.session_state.thegraph_data, ensure_ascii=False)[:1200])
    lines.append("")
    lines.append("请严格按以下 Markdown 结构输出（使用标题 + 列表）：")
    lines.append("## 市场概览")
    lines.append("- 要点1")
    lines.append("- 要点2")
    lines.append("- 要点3")
    lines.append("")
    lines.append("## 关键链上信号解读")
    lines.append("- 要点1")
    lines.append("- 要点2")
    lines.append("")
    lines.append("## 新闻驱动因素")
    lines.append("- 要点1")
    lines.append("- 要点2")
    lines.append("")
    lines.append("## 风险提示")
    lines.append("- 风险1")
    lines.append("- 风险2")
    lines.append("")
    lines.append("## 机会点")
    lines.append("- 机会1")
    lines.append("- 机会2")
    lines.append("")
    lines.append("## 一句话建议")
    lines.append("一句话结论（不超过40字）")
    return "\n".join(lines)

class DailyState(TypedDict, total=False):
    symbols: List[str]
    chain_data: Dict[str, Any]
    defillama_data: Dict[str, Any]
    coinmarketcap_data: Dict[str, Any]
    thegraph_data: Dict[str, Any]
    mcp_results: Dict[str, Any]
    cards: List[Dict[str, Any]]
    chief_summary: str
    news_cards: List[Dict[str, Any]]
    newsdata_items: List[Dict[str, Any]]
    timely_news_cards: List[Dict[str, Any]]
    hot_news_cards: List[Dict[str, Any]]
    news_summary: str
    errors: Dict[str, List[str]]

def tool_pipeline(state: DailyState) -> DailyState:
    errors = {"chain": [], "mcp": [], "news": [], "defillama": [], "coinmarketcap": [], "thegraph": []}
    symbols = state.get("symbols", [])
    symbols_str = ",".join(symbols)
    try:
        state["chain_data"] = fetch_chain_data_cached(
            symbols_str,
            os.getenv("ETHERSCAN_API_KEY", ""),
            os.getenv("ALPHA_VANTAGE_API_KEY", ""),
            os.getenv("RPC_URL", "")
        )
    except Exception as e:
        errors["chain"].append(str(e))
        state["chain_data"] = {}

    # 获取 DeFiLlama 数据
    try:
        state["defillama_data"] = fetch_defillama_cached()
    except Exception as e:
        errors["defillama"].append(str(e))
        state["defillama_data"] = {}

    # 获取 CoinMarketCap 数据
    try:
        state["coinmarketcap_data"] = fetch_coinmarketcap_cached(
            symbols_str,
            st.session_state.coinmarketcap_api_key or os.getenv("COINMARKETCAP_API_KEY", ""),
            os.getenv("COINMARKETCAP_BASE_URL", "")
        )
    except Exception as e:
        errors["coinmarketcap"].append(str(e))
        state["coinmarketcap_data"] = {}

    # 获取 The Graph 数据
    try:
        state["thegraph_data"] = fetch_thegraph_cached(
            os.getenv("THEGRAPH_UNISWAP_V3", ""),
            os.getenv("THEGRAPH_AAVE_V3", "")
        )
    except Exception as e:
        errors["thegraph"].append(str(e))
        state["thegraph_data"] = {}

    if st.session_state.mcp_enabled:
        try:
            raw_results = fetch_mcp_search(build_search_query(symbols))
            state["mcp_results"] = filter_mcp_results(raw_results)
        except Exception as e:
            errors["mcp"].append(str(e))
            state["mcp_results"] = {}
    else:
        state["mcp_results"] = {}
    if st.session_state.newsdata_enabled:
        try:
            api_key = st.session_state.newsdata_api_key or os.getenv("NEWSDATA_API_KEY", "")
            queries = tuple(build_search_queries(symbols))
            news_items = fetch_newsdata_cached(queries, api_key)
            state["newsdata_items"] = news_items
            if news_items:
                state["mcp_results"]["newsdata"] = json.dumps(news_items, ensure_ascii=False)
        except Exception as e:
            errors["news"].append(str(e))
            state["newsdata_items"] = []
    state["errors"] = errors
    return state

def should_analyze(state: DailyState) -> bool:
    return bool(state.get("chain_data") or state.get("mcp_results"))

def run_dashboard_refresh(symbols: list[str]) -> dict:
    if StateGraph and InMemoryCheckpointer and END is not None:
        graph = StateGraph(DailyState, checkpointer=InMemoryCheckpointer())
        graph.add_node("tool_pipeline", tool_pipeline)
        graph.add_node("news_agent", news_agent_node)
        graph.add_node("card_agent", card_agent_node)
        graph.add_node("save_state", save_state_node)
        graph.add_conditional_edges(
            "tool_pipeline",
            lambda s: "news_agent" if should_analyze(s) else "end",
            {"news_agent": "news_agent", "end": END}
        )
        graph.add_edge("news_agent", "card_agent")
        graph.add_edge("card_agent", "save_state")
        graph.add_edge("save_state", END)
        graph.set_entry_point("tool_pipeline")
        compiled = graph.compile()
        import anyio
        return anyio.run(compiled.invoke, {"symbols": symbols})
    return {}

def refresh_prices_only(symbols: list[str]) -> None:
    try:
        st.session_state.coinmarketcap_data = fetch_coinmarketcap_data(symbols)
        st.session_state.chain_errors = [e for e in st.session_state.chain_errors if "CoinMarketCap" not in e]
    except Exception as e:
        st.session_state.chain_errors.append(f"CoinMarketCap 价格获取失败：{e}")
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard_snapshot()

def refresh_news_only(symbols: list[str]) -> None:
    try:
        api_key = st.session_state.newsdata_api_key or os.getenv("NEWSDATA_API_KEY", "")
        st.session_state.newsdata_items = fetch_newsdata_multi(build_search_queries(symbols), api_key)
        timely_cards, hot_cards = build_news_cards(st.session_state.newsdata_items)
        st.session_state.timely_news_cards = timely_cards
        st.session_state.hot_news_cards = hot_cards
        merged = []
        seen = set()
        for c in hot_cards[:4] + timely_cards[:3]:
            title = (c.get("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            merged.append(c)
        st.session_state.news_cards = merged
        # 生成新闻总结（失败则保留上次成功结果）
        if os.getenv("DEEPSEEK_API_KEY") and merged:
            try:
                import anyio
                summary_prompt = f"""
你是资深加密市场分析师。请基于以下每日新闻要点，输出：
1) 新闻摘要（200-300字，中文）
2) 影响分析（300-500字，中文，强调对市场/资金/情绪的影响）

新闻要点：
{json.dumps(merged, ensure_ascii=False)}
"""
                bot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=1536)
                summary = anyio.run(bot.ask, [{"role": "user", "content": summary_prompt}], None)
                st.session_state.news_summary = str(summary).strip()
            except Exception:
                st.session_state.news_summary = st.session_state.last_news_summary or ""
    except Exception as e:
        st.session_state.news_errors.append("新闻加载失败，可能是网络波动，请稍后重试。")
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard_snapshot()

def refresh_cards_only(symbols: list[str]) -> None:
    try:
        import anyio
        cards, summary = anyio.run(
            run_card_agent,
            st.session_state.chain_data or {},
            st.session_state.mcp_results or {},
            st.session_state.newsdata_items or [],
            st.session_state.defillama_data or {},
            st.session_state.coinmarketcap_data or {},
            st.session_state.thegraph_data or {}
        )
        st.session_state.cards = cards
        st.session_state.chief_summary = summary
    except Exception as e:
        st.session_state.chief_summary = ""
        st.session_state.chain_errors.append(f"点评生成失败：{e}")
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_dashboard_snapshot()

async def card_agent_node(state: DailyState) -> DailyState:
    try:
        cards, chief_summary = await run_card_agent(
            state.get("chain_data", {}),
            state.get("mcp_results", {}),
            state.get("newsdata_items", []),
            state.get("defillama_data", {}),
            state.get("coinmarketcap_data", {}),
            state.get("thegraph_data", {})
        )
        state["cards"] = cards
        state["chief_summary"] = chief_summary
    except Exception as e:
        state["cards"] = []
        state["chief_summary"] = f"卡片生成失败：{e}"
    return state

async def news_agent_node(state: DailyState) -> DailyState:
    news_items = state.get("newsdata_items", [])
    timely_cards, hot_cards = build_news_cards(news_items)
    state["timely_news_cards"] = timely_cards
    state["hot_news_cards"] = hot_cards
    # 合并为每日新闻：重要 4 条 + 及时 3 条（去重）
    merged = []
    seen = set()
    for c in hot_cards[:4] + timely_cards[:3]:
        title = (c.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        merged.append(c)
    state["news_cards"] = merged

    # 用 DeepSeek 对新闻做总结（失败则保留上次成功结果）
    if not os.getenv("DEEPSEEK_API_KEY"):
        state["news_summary"] = ""
        return state
    if not merged:
        state["news_summary"] = ""
        return state
    summary_prompt = f"""
你是资深加密市场分析师。请基于以下每日新闻要点，输出：
1) 新闻摘要（200-300字，中文）
2) 影响分析（300-500字，中文，强调对市场/资金/情绪的影响）

新闻要点：
{json.dumps(merged, ensure_ascii=False)}
"""
    bot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=1536)
    try:
        raw = await bot.ask([{"role": "user", "content": summary_prompt}], None)
        state["news_summary"] = raw.strip()
    except Exception as e:
        errors = state.get("errors", {"news": []})
        errors.setdefault("news", []).append("新闻加载失败，可能是网络波动，请稍后重试。")
        state["errors"] = errors
        state["news_summary"] = st.session_state.last_news_summary or ""
    return state

def save_state_node(state: DailyState) -> DailyState:
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_json(DASHBOARD_FILE, {
        "chain_data": state.get("chain_data", {}),
        "defillama_data": state.get("defillama_data", {}),
        "coinmarketcap_data": state.get("coinmarketcap_data", {}),
        "thegraph_data": state.get("thegraph_data", {}),
        "mcp_results": state.get("mcp_results", {}),
        "cards": state.get("cards", []),
        "chief_summary": state.get("chief_summary", ""),
        "news_cards": state.get("news_cards", []),
        "newsdata_items": state.get("newsdata_items", []),
        "timely_news_cards": state.get("timely_news_cards", []),
        "hot_news_cards": state.get("hot_news_cards", []),
        "news_summary": state.get("news_summary", ""),
        "errors": state.get("errors", {}),
        "analysis_text": state.get("analysis_text", ""),
        "last_updated": st.session_state.last_updated
    })
    return state

def render_analysis_cards(text: str):
    # 将 Markdown 按二级标题分段，用折叠卡片展示
    sections = []
    current_title = None
    current_lines = []
    for line in text.splitlines():
        if line.strip().startswith("## "):
            if current_title:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.replace("## ", "").strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_lines).strip()))

    if not sections:
        st.markdown(text)
        return

    for title, body in sections:
        with st.expander(f"📌 {title}", expanded=True):
            st.markdown(body if body else "（无内容）")

def _pick_news_by_keywords(items: list[dict], keywords: list[str], limit: int = 2) -> list[dict]:
    picked = []
    for it in items:
        if not isinstance(it, dict):
            continue
        title = (it.get("title") or "").strip()
        summary = (it.get("summary") or "").strip()
        text = f"{title} {summary}".lower()
        if any(k in text for k in keywords):
            picked.append({"title": title, "summary": summary, "source": it.get("source", "")})
            if len(picked) >= limit:
                break
    return picked

def build_structured_inputs(
    chain_data: dict,
    mcp_results: dict,
    news_items: list[dict],
    defillama_data: dict,
    coinmarketcap_data: dict,
    thegraph_data: dict
) -> dict:
    structured: dict[str, Any] = {"price_signal": "", "price_map": {}, "price_order": []}

    cmc_quotes = coinmarketcap_data.get("quotes", {}) if isinstance(coinmarketcap_data, dict) else {}
    raw_symbols = [s.strip().upper() for s in (st.session_state.chain_symbols or "").split(",") if s.strip()]
    symbols: list[str] = []
    seen_symbols: set[str] = set()
    for sym in raw_symbols:
        if sym in seen_symbols:
            continue
        seen_symbols.add(sym)
        symbols.append(sym)
    price_parts = []
    price_map: dict[str, dict] = {}
    if isinstance(cmc_quotes, dict):
        for sym in symbols:
            quote = cmc_quotes.get(sym, {})
            if not isinstance(quote, dict):
                continue
            price = quote.get("price")
            change = quote.get("percent_change_24h")
            if price is not None:
                price_parts.append(f"{sym} {_fmt_usd(price)} ({_fmt_pct(change)})")
                price_map[sym] = {"price": price, "change_24h": change}
    structured["price_signal"] = "，".join(price_parts)
    structured["price_map"] = price_map
    structured["price_order"] = symbols
    return structured

def build_slot_cards(structured: dict) -> list[dict]:
    cards = []
    price_map = structured.get("price_map") or {}
    price_order = structured.get("price_order") or []
    if isinstance(price_map, dict) and price_map:
        if not isinstance(price_order, list) or not price_order:
            price_order = list(price_map.keys())
        seen_titles: set[str] = set()
        for sym in price_order:
            info = price_map.get(sym, {})
            if not isinstance(info, dict):
                continue
            price = info.get("price")
            change = info.get("change_24h")
            market_cap = info.get("market_cap")
            if price is None:
                continue
            title = f"{sym} 价格"
            if title in seen_titles:
                continue
            seen_titles.add(title)
            cap_text = f" · 市值 {_fmt_usd(market_cap)}" if market_cap else ""
            cards.append({
                "title": f"{sym} 价格",
                "summary": f"${_fmt_price(sym, price)}（24h {_fmt_pct(change)}）{cap_text}",
                "source": "CoinMarketCap"
            })
    elif structured.get("price_signal"):
        cards.append({
            "title": "资产价格",
            "summary": structured["price_signal"],
            "source": "CoinMarketCap"
        })
    return cards

def merge_cards(primary: list[dict], fallback: list[dict], limit: int = 5) -> list[dict]:
    seen = set()
    merged = []
    for c in primary + fallback:
        if not isinstance(c, dict):
            continue
        title = (c.get("title") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        merged.append(c)
        if len(merged) >= limit:
            break
    return merged

def build_preprocessed_context(chain_data: dict, mcp_results: dict, structured: dict) -> dict:
    health = get_source_health()
    brief = {
        "price_signal": structured.get("price_signal", ""),
        "market_signal": structured.get("market_signal", ""),
        "regulation_count": len(structured.get("regulation_news", []) or []),
        "security_count": len(structured.get("security_news", []) or []),
        "defi_signal": structured.get("defi_signal", "")
    }
    mcp_brief = []
    if isinstance(mcp_results, dict):
        for name, content in list(mcp_results.items())[:2]:
            status = health.get(name, {}).get("status", ("", "", "warn"))
            if status[2] != "ok":
                continue
            mcp_brief.append({
                "source": name,
                "snippet": str(content)[:300]
            })
    brief["mcp_brief"] = mcp_brief
    brief["news_summary"] = (st.session_state.news_summary or "")[:600]
    return brief

def build_cleaned_prompt(preprocessed: dict) -> str:
    return f"""
你是数据清洗与结构化助手。请将输入摘要压缩为清晰的“要点结构”，输出严格 JSON：
{{
  "price": "...",
  "market": "...",
  "onchain_defi": "...",
  "news_core": "...",
  "risk": "...",
  "opportunity": "...",
  "next_1_3w": "..."
}}

要求：
- 用简短句子，避免空话
- 必须引用输入中的具体数字或事件
- 不要输出多余字段

输入：
{json.dumps(preprocessed, ensure_ascii=False)}
"""

def build_summary_prompt(cleaned: dict) -> str:
    return f"""
你是加密市场首席分析师。请仅输出“综合点评”，不要输出任何 JSON 或其他内容。
要求：接近 800 字，分 4-6 段，每段 2-4 句，覆盖 价格/资金面、链上/DeFi、新闻与监管、风险与机会、未来1-3周路径。
必须引用输入中的具体数据点（数字/变化/事件），并做解释与推演，避免堆砌数据。
末尾给出“结论摘要”段，信息密度高。

结构化要点：
{json.dumps(cleaned, ensure_ascii=False)[:2000]}
"""

def build_fallback_cards(structured: dict) -> tuple[list[dict], str]:
    cards = build_slot_cards(structured)
    if not cards:
        cards = [{
            "title": "暂无价格",
            "summary": "当前未获取到价格数据，请检查 CoinMarketCap Key 或网络状态。",
            "source": "系统"
        }]
    return cards[:5], ""

async def run_card_agent(
    chain_data: dict,
    mcp_results: dict,
    news_items: list[dict],
    defillama_data: dict,
    coinmarketcap_data: dict,
    thegraph_data: dict
) -> tuple[list[dict], str]:
    if not os.getenv("DEEPSEEK_API_KEY"):
        structured = build_structured_inputs(chain_data, mcp_results, news_items, defillama_data, coinmarketcap_data, thegraph_data)
        cards, summary = build_fallback_cards(structured)
        return cards, ""
    structured = build_structured_inputs(chain_data, mcp_results, news_items, defillama_data, coinmarketcap_data, thegraph_data)
    preprocessed = build_preprocessed_context(chain_data, mcp_results, structured)
    clean_prompt = build_cleaned_prompt(preprocessed)
    try:
        cleaned_raw = await bot.ask([{"role": "user", "content": clean_prompt}], None)
        cleaned_text = cleaned_raw.strip()
        if not cleaned_text.startswith("{"):
            s = cleaned_text.find("{")
            e = cleaned_text.rfind("}")
            if s != -1 and e != -1 and e > s:
                cleaned_text = cleaned_text[s:e + 1]
        cleaned = json.loads(cleaned_text)
    except Exception:
        cleaned = preprocessed
    cards = build_slot_cards(structured)
    if len(cards) < 3:
        cards.append({
            "title": "市场观察",
            "summary": "当前可用信号有限，建议补充行情与新闻来源后再评估趋势。",
            "source": "系统"
        })
    summary_prompt = build_summary_prompt(cleaned)
    bot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=2048)
    try:
        summary = await bot.ask([{"role": "user", "content": summary_prompt}], None)
        return cards[:5], summary.strip()
    except Exception:
        return cards[:5], ""

def render_cards_grid(cards: list[dict], limit: int | None = None, max_summary_len: int = 160):
    if not cards:
        st.info("暂无卡片，可点击上方按钮生成。")
        return
    st.markdown(
        """
        <style>
        .web3-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px 22px;
            margin-bottom: 16px;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
        }
        .web3-title {
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 8px;
        }
        .web3-summary {
            color: #334155;
            line-height: 1.5;
        }
        .web3-source {
            color: #64748b;
            font-size: 12px;
            margin-top: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(2)
    show_cards = cards[:limit] if isinstance(limit, int) else cards
    for idx, card in enumerate(show_cards):
        col = cols[idx % 2]
        with col:
            with st.container():
                title = card.get("title", "未命名卡片")
                summary = card.get("summary", "")
                if isinstance(summary, str) and len(summary) > max_summary_len:
                    summary = summary[:max_summary_len].rstrip() + "..."
                src = card.get("source", "")
                link = card.get("link", "")
                pub_date = card.get("pubDate", "")
                html = f"""
                <div class="web3-card">
                    <div class="web3-title">{title}</div>
                    <div class="web3-summary">{summary}</div>
                    <div class="web3-source">{src} {pub_date}</div>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
                if link:
                    st.markdown(f"[查看原文]({link})")

with tab_data:
    st.subheader("📌 情报看板")
    col_a, col_b = st.columns([1, 1])
    with col_a:
        symbols = [s.strip().upper() for s in st.session_state.chain_symbols.split(",") if s.strip()]

        if st.session_state.auto_refresh_on_load and not st.session_state.auto_refresh_done:
            st.session_state.auto_refresh_done = True
            result = run_dashboard_refresh(symbols)
            if result:
                st.session_state.chain_data = result.get("chain_data", {})
                st.session_state.defillama_data = result.get("defillama_data", {})
                st.session_state.coinmarketcap_data = result.get("coinmarketcap_data", {})
                st.session_state.thegraph_data = result.get("thegraph_data", {})
                st.session_state.mcp_results = result.get("mcp_results", {})
                st.session_state.cards = result.get("cards", [])
                st.session_state.chief_summary = result.get("chief_summary", "")
                st.session_state.news_cards = result.get("news_cards", [])
                st.session_state.newsdata_items = result.get("newsdata_items", [])
                st.session_state.timely_news_cards = result.get("timely_news_cards", [])
                st.session_state.hot_news_cards = result.get("hot_news_cards", [])
            st.session_state.news_summary = result.get("news_summary", "")
            if st.session_state.news_summary:
                st.session_state.last_news_summary = st.session_state.news_summary
                errors = result.get("errors", {})
                if isinstance(errors, dict):
                    st.session_state.chain_errors = [f"链上数据获取失败：{e}" for e in errors.get("chain", [])]
                    st.session_state.mcp_errors = [f"MCP 搜索失败：{e}" for e in errors.get("mcp", [])]
                    st.session_state.news_errors = [
                        f"新闻获取失败：{e}" for e in errors.get("news", [])
                        if "本质卡片" not in str(e)
                    ]
                    if errors.get("defillama"):
                        st.session_state.chain_errors.extend([f"DeFiLlama 数据获取失败：{e}" for e in errors.get("defillama", [])])
                    if errors.get("coinmarketcap"):
                        st.session_state.chain_errors.extend([f"CoinMarketCap 数据获取失败：{e}" for e in errors.get("coinmarketcap", [])])
                    if errors.get("thegraph"):
                        st.session_state.chain_errors.extend([f"The Graph 数据获取失败：{e}" for e in errors.get("thegraph", [])])

        if st.button("📥 更新全部"):
            st.session_state.chain_errors = []
            st.session_state.news_errors = []
            st.session_state.mcp_errors = []
            if not (StateGraph and InMemoryCheckpointer and END is not None):
                st.error("SpoonOS Graph 未初始化，无法运行 AgentGraph")
                result = {}
            else:
                result = run_dashboard_refresh(symbols)
            if result:
                st.session_state.chain_data = result.get("chain_data", {})
                st.session_state.defillama_data = result.get("defillama_data", {})
                st.session_state.coinmarketcap_data = result.get("coinmarketcap_data", {})
                st.session_state.thegraph_data = result.get("thegraph_data", {})
                st.session_state.mcp_results = result.get("mcp_results", {})
                st.session_state.cards = result.get("cards", [])
                st.session_state.chief_summary = result.get("chief_summary", "")
                st.session_state.news_cards = result.get("news_cards", [])
                st.session_state.newsdata_items = result.get("newsdata_items", [])
                st.session_state.timely_news_cards = result.get("timely_news_cards", [])
                st.session_state.hot_news_cards = result.get("hot_news_cards", [])
            st.session_state.news_summary = result.get("news_summary", "")
            if st.session_state.news_summary:
                st.session_state.last_news_summary = st.session_state.news_summary
                errors = result.get("errors", {})
                if isinstance(errors, dict):
                    st.session_state.chain_errors = [f"链上数据获取失败：{e}" for e in errors.get("chain", [])]
                    st.session_state.mcp_errors = [f"MCP 搜索失败：{e}" for e in errors.get("mcp", [])]
                    st.session_state.news_errors = [
                        f"新闻获取失败：{e}" for e in errors.get("news", [])
                        if "本质卡片" not in str(e)
                    ]
                    if errors.get("defillama"):
                        st.session_state.chain_errors.extend([f"DeFiLlama 数据获取失败：{e}" for e in errors.get("defillama", [])])
                    if errors.get("coinmarketcap"):
                        st.session_state.chain_errors.extend([f"CoinMarketCap 数据获取失败：{e}" for e in errors.get("coinmarketcap", [])])
                    if errors.get("thegraph"):
                        st.session_state.chain_errors.extend([f"The Graph 数据获取失败：{e}" for e in errors.get("thegraph", [])])

            if not st.session_state.chain_errors and not st.session_state.mcp_errors:
                st.success("✅ 已获取数据并完成分析")
            else:
                st.warning("⚠️ 有部分数据源获取失败，请查看错误提示")

        cols_refresh = st.columns(3)
        if cols_refresh[0].button("💰 仅刷新价格"):
            refresh_prices_only(symbols)
        if cols_refresh[1].button("📰 仅刷新新闻"):
            with st.spinner("正在刷新新闻..."):
                refresh_news_only(symbols)
        if cols_refresh[2].button("🧠 仅刷新情报卡片"):
            refresh_cards_only(symbols)

    with col_b:
        st.caption(f"更新时间：{st.session_state.last_updated or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if st.session_state.chain_errors:
        for err in st.session_state.chain_errors:
            st.error(err)
    # RSS 已移除，无需显示 RSS 错误
    if st.session_state.mcp_errors:
        for err in st.session_state.mcp_errors:
            st.error(err)
    if st.session_state.news_errors:
        for err in st.session_state.news_errors:
            if "本质卡片" in str(err):
                continue
            st.error("新闻加载失败，可能是网络波动，请稍后重试。")

    cols = st.columns(4)
    cmc_quotes = st.session_state.coinmarketcap_data.get("quotes", {}) if isinstance(st.session_state.coinmarketcap_data, dict) else {}
    cmc_error = ""
    if isinstance(st.session_state.coinmarketcap_data, dict):
        cmc_error = st.session_state.coinmarketcap_data.get("error") or st.session_state.coinmarketcap_data.get("quotes_error", "")
    def _cmc(sym: str) -> dict:
        return cmc_quotes.get(sym, {}) if isinstance(cmc_quotes, dict) else {}
    btc = _cmc("BTC")
    eth = _cmc("ETH")
    sol = _cmc("SOL")
    bnb = _cmc("BNB")
    cols[0].metric(
        "BTC",
        f"${_fmt_price('BTC', btc.get('price'))}",
        f"{_fmt_pct(btc.get('percent_change_24h'))}" if isinstance(btc.get('percent_change_24h', None), (int, float)) else "-"
    )
    cols[1].metric(
        "ETH",
        f"${_fmt_price('ETH', eth.get('price'))}",
        f"{_fmt_pct(eth.get('percent_change_24h'))}" if isinstance(eth.get('percent_change_24h', None), (int, float)) else "-"
    )
    cols[2].metric(
        "SOL",
        f"${_fmt_price('SOL', sol.get('price'))}",
        f"{_fmt_pct(sol.get('percent_change_24h'))}" if isinstance(sol.get('percent_change_24h', None), (int, float)) else "-"
    )
    cols[3].metric(
        "BNB",
        f"${_fmt_price('BNB', bnb.get('price'))}",
        f"{_fmt_pct(bnb.get('percent_change_24h'))}" if isinstance(bnb.get('percent_change_24h', None), (int, float)) else "-"
    )
    if cmc_error:
        st.warning(f"CoinMarketCap 价格获取失败：{cmc_error}")

    st.markdown("### 🗂️ 情报卡片")
    render_cards_grid(st.session_state.cards, limit=5, max_summary_len=200)

    st.markdown("### 📰 每日新闻")
    if st.button("🔁 重试加载新闻", type="secondary"):
        with st.spinner("正在重试加载新闻..."):
            refresh_news_only(symbols)
    if st.session_state.news_cards:
        render_cards_grid(st.session_state.news_cards, limit=7, max_summary_len=120)
    else:
        st.info("暂无每日新闻（请确保 NewsData 已启用）。")

    if st.session_state.news_summary:
        st.markdown("### 🧾 每日新闻总结与影响分析")
        st.markdown(st.session_state.news_summary)


    st.markdown("### ✅ 首席分析师点评")
    if st.session_state.chief_summary:
        st.success(st.session_state.chief_summary)
    else:
        st.error("生成失败，请重试。")

    with st.expander("查看原始数据与搜索结果", expanded=False):
        if st.session_state.chain_data:
            st.subheader("📊 今日数据摘要")
            prices = st.session_state.chain_data.get("prices", {})
            for coin_id, info in prices.items():
                st.write(f"- {coin_id}: ${info.get('usd')} | 24h {info.get('usd_24h_change'):.2f}%")
            gas_price = st.session_state.chain_data.get("gas_price_wei")
            st.write(f"- Gas Price: {gas_price if gas_price else '未获取'}")

        # 显示 DeFiLlama 数据
        if hasattr(st.session_state, 'defillama_data') and st.session_state.defillama_data:
            st.subheader("🏦 DeFiLlama 数据")
            defillama = st.session_state.defillama_data

            # 显示各链 TVL
            if defillama.get("chain_tvl"):
                st.markdown("**各链 TVL：**")
                for chain_name, chain_info in defillama["chain_tvl"].items():
                    tvl = chain_info.get("tvl", 0)
                    if tvl:
                        st.write(f"- {chain_name}: ${tvl:,.0f}")

            # 显示 Top 协议
            if defillama.get("top_protocols"):
                st.markdown("**Top 10 DeFi 协议：**")
                for idx, protocol in enumerate(defillama["top_protocols"][:5], 1):
                    name = protocol.get("name", "Unknown")
                    tvl = protocol.get("tvl", 0)
                    change = protocol.get("change_1d", 0)
                    category = protocol.get("category", "")
                    st.write(f"{idx}. {name} ({category}): ${tvl:,.0f} | 24h {change:+.2f}%")

        # 显示 CoinMarketCap 数据
        if hasattr(st.session_state, 'coinmarketcap_data') and st.session_state.coinmarketcap_data:
            cmc = st.session_state.coinmarketcap_data
            if cmc.get("quotes") and not cmc.get("error"):
                st.subheader("📊 CoinMarketCap 数据")
                for symbol, quote in cmc["quotes"].items():
                    st.markdown(f"**{symbol}**")
                    st.write(f"- 价格: ${quote.get('price', 0):,.2f}")
                    st.write(f"- 24h 交易量: ${quote.get('volume_24h', 0):,.0f}")
                    st.write(f"- 市值: ${quote.get('market_cap', 0):,.0f}")
                    st.write(f"- 市值排名: #{quote.get('cmc_rank', 'N/A')}")
                    st.write(f"- 市值占比: {quote.get('market_cap_dominance', 0):.2f}%")
                    st.write(f"- 流通量: {quote.get('circulating_supply', 0):,.0f}")
                    st.write("---")
            elif cmc.get("error"):
                st.info(f"💡 CoinMarketCap: {cmc['error']}")

        # 显示 The Graph 数据
        if hasattr(st.session_state, 'thegraph_data') and st.session_state.thegraph_data:
            graph = st.session_state.thegraph_data
            st.subheader("🔗 The Graph 数据")

            # Uniswap V3 池子
            if graph.get("uniswap_v3_pools"):
                st.markdown("**Uniswap V3 Top 5 流动性池：**")
                for idx, pool in enumerate(graph["uniswap_v3_pools"], 1):
                    token0 = pool.get("token0", {}).get("symbol", "?")
                    token1 = pool.get("token1", {}).get("symbol", "?")
                    tvl = float(pool.get("totalValueLockedUSD", 0))
                    volume = float(pool.get("volumeUSD", 0))
                    fee = int(pool.get("feeTier", 0)) / 10000
                    st.write(f"{idx}. {token0}/{token1} (Fee: {fee}%)")
                    st.write(f"   TVL: ${tvl:,.0f} | Volume: ${volume:,.0f}")

            # Aave V3 储备
            if graph.get("aave_v3_reserves"):
                st.markdown("**Aave V3 Top 5 储备资产：**")
                for idx, reserve in enumerate(graph["aave_v3_reserves"], 1):
                    symbol = reserve.get("symbol", "?")
                    name = reserve.get("name", "?")
                    liquidity = float(reserve.get("totalLiquidity", 0))
                    available = float(reserve.get("availableLiquidity", 0))
                    st.write(f"{idx}. {symbol} ({name})")
                    st.write(f"   总流动性: ${liquidity:,.0f} | 可用: ${available:,.0f}")

        if st.session_state.mcp_results:
            st.subheader("🔎 MCP 搜索结果（原文）")
            for name, content in st.session_state.mcp_results.items():
                st.markdown(f"**{name}**")
                st.code(str(content)[:3000])

        if st.session_state.newsdata_items:
            st.subheader("📰 NewsData.io 原始结果")
            st.json(st.session_state.newsdata_items)

        etherscan = st.session_state.chain_data.get("etherscan", {}) if st.session_state.chain_data else {}
        if isinstance(etherscan, dict) and (etherscan.get("gasoracle") or etherscan.get("ethprice")):
            st.subheader("⛽ Etherscan")
            if isinstance(etherscan.get("gasoracle"), dict):
                g = etherscan["gasoracle"]
                st.write(f"- Gas Oracle: Safe={g.get('SafeGasPrice')}  Propose={g.get('ProposeGasPrice')}  Fast={g.get('FastGasPrice')}")
            else:
                st.write("- Gas Oracle: 暂无有效数据")
            if isinstance(etherscan.get("ethprice"), dict):
                p = etherscan["ethprice"]
                st.write(f"- ETH Price: ${p.get('ethusd')} | BTC={p.get('ethbtc')}")
            else:
                st.write("- ETH Price: 暂无有效数据")

        alpha_vantage = st.session_state.chain_data.get("alpha_vantage", {}) if st.session_state.chain_data else {}
        if alpha_vantage:
            st.subheader("📈 Alpha Vantage（加密收盘价）")
            for sym, info in alpha_vantage.items():
                st.write(f"- {sym}: {info.get('close_usd')} @ {info.get('date')}")

with tab_chat:
    # 聊天界面
    st.header("💬 AI 聊天")

def build_role_prompt(base_prompt: str, role_name: str, role_style: str) -> str:
    return f"{base_prompt}\n\n你现在的身份是：{role_name}。风格要求：{role_style}。"

def call_openai_compatible(base_url: str, api_key: str, model: str, messages: list, system_msg: str | None = None, extra_params: dict | None = None) -> str:
    client = OpenAI(base_url=base_url, api_key=api_key)
    final_messages = []
    if system_msg:
        final_messages.append({"role": "system", "content": system_msg})
    final_messages.extend(messages)
    payload = {
        "model": model,
        "messages": final_messages
    }
    if extra_params:
        payload.update(extra_params)
    resp = client.chat.completions.create(**payload)
    return resp.choices[0].message.content

def call_hunyuan(messages: list, system_msg: str) -> str:
    api_key = os.getenv("HUNYUAN_API_KEY")
    base_url = os.getenv("HUNYUAN_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")
    model = os.getenv("HUNYUAN_MODEL", "hunyuan-turbos-latest")
    if not api_key:
        raise ValueError("缺少 HUNYUAN_API_KEY")
    return call_openai_compatible(base_url, api_key, model, messages, system_msg)

def call_deepseek(messages: list, system_msg: str) -> str:
    chatbot = ChatBot(
        model_name="deepseek-chat",
        llm_provider="deepseek",
        max_tokens=4096
    )
    import anyio
    return str(anyio.run(chatbot.ask, messages, system_msg))

def call_doubao(messages: list, system_msg: str) -> str:
    api_key = os.getenv("ARK_API_KEY") or os.getenv("DOUBAO_API_KEY")
    base_url = os.getenv("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/responses")
    model = os.getenv("DOUBAO_MODEL", "ep-20260130214742-t9vlx")
    reasoning_effort = os.getenv("DOUBAO_REASONING_EFFORT", "medium")
    max_completion_tokens = int(os.getenv("DOUBAO_MAX_COMPLETION_TOKENS", "4096"))
    if not api_key:
        raise ValueError("缺少 ARK_API_KEY（豆包 API Key）")

    final_messages = [{"role": "system", "content": system_msg}] + messages if system_msg else messages
    if base_url.endswith("/responses"):
        user_text = "\n".join([m.get("content", "") for m in final_messages if m.get("role") == "user"])
        payload = {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}]
                }
            ],
            "max_output_tokens": max_completion_tokens
        }
    else:
        payload = {
            "model": model,
            "messages": final_messages,
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_completion_tokens
        }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    # 兼容用户只填到 /api/v3 的情况，自动补全为 /chat/completions
    if base_url.endswith("/api/v3"):
        base_url = base_url + "/chat/completions"
    resp = requests.post(base_url, headers=headers, json=payload, timeout=60)
    if resp.status_code == 404:
        fallback_url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        if base_url != fallback_url:
            resp = requests.post(fallback_url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    try:
        if isinstance(data, dict) and data.get("output_text"):
            return data["output_text"]
        if isinstance(data, dict) and data.get("output"):
            texts: list[str] = []
            for out in data["output"]:
                if out.get("type") == "message":
                    parts = out.get("content", [])
                    texts.extend([p.get("text", "") for p in parts if p.get("type") == "output_text"])
            if texts:
                return "\n".join([t for t in texts if t])
        return data["choices"][0]["message"]["content"]
    except Exception:
        return str(data)

def build_chat_context() -> str:
    cards = st.session_state.cards or []
    summary = st.session_state.chief_summary or ""
    context = {
        "cards": cards[:5],
        "chief_summary": summary
    }
    return f"今日情报看板（供参考）：{json.dumps(context, ensure_ascii=False)}"

class DebateState(TypedDict, total=False):
    query: str
    context: str
    a1: str
    a2: str
    a3: str

async def agent1_node(state: DebateState) -> DebateState:
    prompt = build_role_prompt(
        st.session_state.system_prompt,
        "豆包（经济大臣）",
        st.session_state.agent1_style
    ) + f"\n\n{state.get('context','')}"
    prompt = _apply_skill(prompt, {s["name"]: s for s in load_skills()[0]}, st.session_state.agent1_skill if st.session_state.agent1_skill != "（不使用技能）" else "")
    try:
        state["a1"] = call_doubao([{"role": "user", "content": state.get("query","")}], prompt)
    except Exception as e:
        state["a1"] = f"调用失败：{e}"
    return state

async def agent2_node(state: DebateState) -> DebateState:
    prompt = build_role_prompt(
        st.session_state.system_prompt,
        "元宝（财政大臣）",
        st.session_state.agent2_style
    ) + f"\n\n{state.get('context','')}"
    prompt = _apply_skill(prompt, {s["name"]: s for s in load_skills()[0]}, st.session_state.agent2_skill if st.session_state.agent2_skill != "（不使用技能）" else "")
    msgs = [
        {"role": "user", "content": f"{state.get('query','')}\n\n经济大臣观点：{state.get('a1','')}\n\n请指出风险与漏洞，并提出质疑。"}
    ]
    try:
        state["a2"] = call_hunyuan(msgs, prompt)
    except Exception as e:
        state["a2"] = f"调用失败：{e}"
    return state

async def agent3_node(state: DebateState) -> DebateState:
    style_guard = (
        "写作要求：放弃浮夸的人设演戏，不要用‘拍桌子’、‘冷笑’等文学描写。"
        "多维视角：机会把握者、风险评估者两个专业角度给出分析。"
        "数据驱动：列出近一年金价的波动范围，并解释影响金价的核心变量（如美元汇率、实际利率）。"
        "操作建议：给出适合普通人的“最小阻力操作路径”（如定存还是 ETF）。"
        "简洁有力：用 Markdown 表格对比优缺点，拒绝长篇大论。"
    )
    prompt = build_role_prompt(
        st.session_state.system_prompt,
        "DeepSeek（首相）",
        st.session_state.agent3_style
    ) + f"\n\n{style_guard}\n\n{state.get('context','')}"
    prompt = _apply_skill(prompt, {s["name"]: s for s in load_skills()[0]}, st.session_state.agent3_skill if st.session_state.agent3_skill != "（不使用技能）" else "")
    a1 = state.get("a1", "")
    a2 = state.get("a2", "")
    async def _summarize_for_input(text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            return ""
        summary_prompt = (
            "请将以下内容提炼为不超过320字的要点摘要，保留关键结论和依据，中文输出：\n"
            f"{text}"
        )
        bot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=256)
        try:
            summary = await bot.ask([{"role": "user", "content": summary_prompt}], None)
            return summary.strip()
        except Exception:
            return text
    a1_summary = await _summarize_for_input(a1)
    a2_summary = await _summarize_for_input(a2)
    msgs = [
        {"role": "user", "content": f"{state.get('query','')}\n\n经济大臣观点摘要：{a1_summary}\n\n财政大臣观点摘要：{a2_summary}\n\n请综合双方观点给出可执行建议。"}
    ]
    try:
        chatbot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=2048)
        state["a3"] = await chatbot.ask(msgs, prompt)
    except Exception as e:
        # 二次降级重试：更短提示 + 更小输出
        try:
            retry_prompt = build_role_prompt(
                st.session_state.system_prompt,
                "DeepSeek（首相）",
                "简洁给出可执行建议"
            ) + f"\n\n{style_guard}"
            chatbot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=1024)
            state["a3"] = await chatbot.ask(msgs, retry_prompt)
        except Exception as e2:
            state["a3"] = f"调用失败：{e2}"
    return state

def run_free_debate(topic: str, rounds: int) -> list[dict]:
    history: list[dict] = []
    base_context = build_chat_context()
    skills, _blocked_skills = load_skills()
    skill_map = {s["name"]: s for s in skills}

    def _format_thread() -> str:
        if not history:
            return ""
        parts = []
        for h in history:
            parts.append(f"[第{h['round']}轮] {h['speaker']}: {h['content']}")
        return "\n".join(parts)[-6000:]

    def _post_style_rules() -> str:
        return (
            "你正在广场发帖讨论，请尽量用“帖子”形式输出，结构建议：\n"
            "标题：一句话概括立场\n"
            "正文：观点 + 论据/数据 + 推理\n"
            "回应他人：可以@指出同意/反对的点（没有就写“无”）\n"
            "标签：#关键词 #观点\n"
            "要求：中文表达，真实讨论，不写空话套话。"
        )

    for round_idx in range(1, max(1, rounds) + 1):
        thread_context = _format_thread()
        common_context = (
            f"话题：{topic}\n\n"
            f"基础上下文：{base_context}\n\n"
            f"已有讨论：\n{thread_context}\n\n"
            f"当前轮次：第{round_idx}轮"
        )

        # 经济大臣发帖
        prompt1 = build_role_prompt(
            st.session_state.system_prompt,
            "豆包（经济大臣）",
            st.session_state.agent1_style
        ) + f"\n\n{_post_style_rules()}\n\n{common_context}"
        prompt1 = _apply_skill(
            prompt1,
            skill_map,
            st.session_state.agent1_skill if st.session_state.agent1_skill != "（不使用技能）" else ""
        )
        try:
            a1 = call_doubao([{"role": "user", "content": topic}], prompt1)
        except Exception as e:
            a1 = f"调用失败：{e}"
        history.append({"round": round_idx, "speaker": "经济大臣", "content": a1})

        # 财政大臣发帖
        prompt2 = build_role_prompt(
            st.session_state.system_prompt,
            "元宝（财政大臣）",
            st.session_state.agent2_style
        ) + f"\n\n{_post_style_rules()}\n\n{common_context}"
        prompt2 = _apply_skill(
            prompt2,
            skill_map,
            st.session_state.agent2_skill if st.session_state.agent2_skill != "（不使用技能）" else ""
        )
        try:
            a2 = call_hunyuan([{"role": "user", "content": topic}], prompt2)
        except Exception as e:
            a2 = f"调用失败：{e}"
        history.append({"round": round_idx, "speaker": "财政大臣", "content": a2})

        # 首相发帖
        prompt3 = build_role_prompt(
            st.session_state.system_prompt,
            "DeepSeek（首相）",
            st.session_state.agent3_style
        ) + f"\n\n{_post_style_rules()}\n\n{common_context}"
        prompt3 = _apply_skill(
            prompt3,
            skill_map,
            st.session_state.agent3_skill if st.session_state.agent3_skill != "（不使用技能）" else ""
        )
        try:
            a3 = call_deepseek([{"role": "user", "content": topic}], prompt3)
        except Exception as e:
            a3 = f"调用失败：{e}"
        history.append({"round": round_idx, "speaker": "首相", "content": a3})

    return history

def summarize_square_history(topic: str, history: list[dict]) -> dict:
    # 将讨论历史汇总成“广场帖子卡片”
    thread_text = "\n".join(
        [f"[第{h.get('round','?')}轮] {h.get('speaker','')}: {h.get('content','')}" for h in history]
    ).strip()
    fallback = {
        "title": f"讨论总结：{topic}",
        "summary": (thread_text[:300] + "…") if thread_text else "无可用讨论内容。",
        "key_points": [],
        "consensus": "",
        "disagreements": "",
        "action": ""
    }
    if not os.getenv("DEEPSEEK_API_KEY"):
        return fallback
    try:
        prompt = f"""
你是广场讨论的版主，请把讨论内容浓缩成“卡片式帖子”。请输出严格 JSON，不要额外文字：
{{
  "title": "一句话标题（不超过20字）",
  "summary": "120-200字的总结",
  "key_points": ["要点1","要点2","要点3"],
  "consensus": "大家一致的观点（如没有写“无”）",
  "disagreements": "主要分歧（如没有写“无”）",
  "action": "可执行建议（如没有写“无”）"
}}

话题：{topic}
讨论记录：
{thread_text}
"""
        bot = ChatBot(model_name="deepseek-chat", llm_provider="deepseek", max_tokens=1024)
        import anyio
        raw = anyio.run(bot.ask, [{"role": "user", "content": prompt}], None)
        text = str(raw).strip()
        data = json.loads(text)
        data.setdefault("title", f"讨论总结：{topic}")
        data.setdefault("summary", "")
        data.setdefault("key_points", [])
        data.setdefault("consensus", "")
        data.setdefault("disagreements", "")
        data.setdefault("action", "")
        return data
    except Exception:
        return fallback

with tab_chat:
    with st.expander("🧠 议事厅提示词（点击展开修改）", expanded=False):
        st.caption("System Prompt + 三个 Agent 的风格要求")
        system_prompt_input = st.text_area(
            "System Prompt（系统提示词）",
            value=st.session_state.system_prompt,
            height=180,
            help="设置 AI 的性格、角色和回答风格。例如：'你是一个专业的金融分析师'"
        )
        if st.button("💾 保存人设", use_container_width=True, key="save_system_prompt_chat"):
            st.session_state.system_prompt = system_prompt_input
            st.success("✅ 人设已保存！")
        st.divider()
        agent1_style_input = st.text_area(
            "经济大臣提示词",
            value=st.session_state.agent1_style,
            height=80,
            key="agent1_style_chat"
        )
        agent2_style_input = st.text_area(
            "财政大臣提示词",
            value=st.session_state.agent2_style,
            height=80,
            key="agent2_style_chat"
        )
        agent3_style_input = st.text_area(
            "首相提示词",
            value=st.session_state.agent3_style,
            height=80,
            key="agent3_style_chat"
        )
        if st.button("💾 保存三位 Agent 提示词", use_container_width=True, key="save_agent_styles"):
            st.session_state.agent1_style = agent1_style_input
            st.session_state.agent2_style = agent2_style_input
            st.session_state.agent3_style = agent3_style_input
            st.success("✅ 已保存")

    skills_available, skills_blocked = load_skills()
    skill_map = {s["name"]: s for s in skills_available}
    with st.expander("🧩 技能库（OpenClaw 风格）", expanded=False):
        st.caption("从 skills/ 目录加载，可用于给 Agent 加“技能模块”")
        options = ["（不使用技能）"] + [s["name"] for s in skills_available]
        st.session_state.agent1_skill = st.selectbox(
            "经济大臣技能",
            options,
            index=0 if st.session_state.agent1_skill == "" else options.index(st.session_state.agent1_skill) if st.session_state.agent1_skill in options else 0,
            key="agent1_skill_select"
        )
        st.session_state.agent2_skill = st.selectbox(
            "财政大臣技能",
            options,
            index=0 if st.session_state.agent2_skill == "" else options.index(st.session_state.agent2_skill) if st.session_state.agent2_skill in options else 0,
            key="agent2_skill_select"
        )
        st.session_state.agent3_skill = st.selectbox(
            "首相技能",
            options,
            index=0 if st.session_state.agent3_skill == "" else options.index(st.session_state.agent3_skill) if st.session_state.agent3_skill in options else 0,
            key="agent3_skill_select"
        )
        if skills_blocked:
            st.caption("以下技能因缺少环境变量而暂不可用：")
            for s in skills_blocked:
                st.write(f"🔒 {s['name']} · 缺少 {', '.join(s['missing_env'])}")

    # 检查必要的 Key（三模型顺序）
    missing_keys = []
    if not (os.getenv("ARK_API_KEY") or os.getenv("DOUBAO_API_KEY")):
        missing_keys.append("ARK_API_KEY")
    if not os.getenv("HUNYUAN_API_KEY"):
        missing_keys.append("HUNYUAN_API_KEY")
    if not os.getenv("DEEPSEEK_API_KEY"):
        missing_keys.append("DEEPSEEK_API_KEY")

    if missing_keys:
        st.error(f"⚠️ 缺少配置：{', '.join(missing_keys)}")
        st.info("请在 .env 中补齐上述 Key")
    else:
        # 议事厅不保存历史，仅展示最近一轮结果
        last = st.session_state.last_debate or {}
        if last:
            with st.chat_message("user"):
                st.write(last.get("user", ""))
            with st.chat_message("assistant"):
                with st.container():
                    st.markdown("#### ⚔️ 经济大臣（激进）")
                    st.info(last.get("a1") or "无输出")
                with st.container():
                    st.markdown("#### 🧱 财政大臣（谨慎）")
                    st.success(last.get("a2") or "无输出")
                with st.container():
                    st.markdown("#### 🧑‍⚖️ 首相（总结）")
                    st.warning(last.get("a3") or "无输出")

        # 用户输入
        user_input = st.chat_input("输入你的问题...")
        
        if user_input:
            with st.spinner("AI 正在思考..."):
                try:
                    # AgentGraph 顺序：经济大臣 → 财政大臣 → 首相
                    if StateGraph and InMemoryCheckpointer and END is not None:
                        graph = StateGraph(DebateState, checkpointer=InMemoryCheckpointer())
                        graph.add_node("agent1", agent1_node)
                        graph.add_node("agent2", agent2_node)
                        graph.add_node("agent3", agent3_node)
                        graph.add_edge("agent1", "agent2")
                        graph.add_edge("agent2", "agent3")
                        graph.add_edge("agent3", END)
                        graph.set_entry_point("agent1")
                        compiled = graph.compile()
                        import anyio
                        result = anyio.run(
                            compiled.invoke,
                            {"query": user_input, "context": build_chat_context()}
                        )
                        a1 = result.get("a1", "")
                        a2 = result.get("a2", "")
                        a3 = result.get("a3", "")
                    else:
                        a1, a2, a3 = "", "", ""
                    st.session_state.last_debate = {
                        "user": user_input,
                        "a1": a1,
                        "a2": a2,
                        "a3": a3,
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                except Exception as e:
                    st.session_state.last_debate = {
                        "user": user_input,
                        "a1": "",
                        "a2": "",
                        "a3": f"❌ 错误: {str(e)}",
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.error(st.session_state.last_debate["a3"])
            st.rerun()

with tab_square:
    st.header("🧩 广场自由讨论")
    st.caption("用户给出话题，三位 Agent 自由讨论多轮。")
    topic = st.text_input(
        "输入话题（广场讨论主题）",
        value="",
        placeholder="例如：比特币走势与流动性、以太坊L2竞争、AI 与加密叙事"
    )
    rounds = st.slider("讨论轮数", min_value=1, max_value=3, value=st.session_state.square_rounds)
    st.session_state.square_rounds = rounds
    col_sq_a, col_sq_b = st.columns(2)
    with col_sq_a:
        if st.button("▶️ 开始讨论", use_container_width=True):
            if topic.strip():
                with st.spinner("讨论进行中..."):
                    st.session_state.square_history = run_free_debate(topic.strip(), rounds)
                    post = summarize_square_history(topic.strip(), st.session_state.square_history)
                    st.session_state.square_posts.append({
                        "topic": topic.strip(),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "post": post
                    })
                    save_json(SQUARE_FILE, {"posts": st.session_state.square_posts})
                st.rerun()
            else:
                st.warning("请先输入话题")
    with col_sq_b:
        if st.button("🗑️ 清空讨论", use_container_width=True):
            st.session_state.square_history = []
            st.session_state.square_posts = []
            save_json(SQUARE_FILE, {"posts": st.session_state.square_posts})
            st.rerun()

    if st.session_state.square_posts:
        st.subheader("🧾 广场帖子（历史讨论总结）")
        for item in reversed(st.session_state.square_posts[-20:]):
            post = item.get("post", {}) or {}
            title = post.get("title") or f"讨论总结：{item.get('topic','')}"
            summary = post.get("summary", "")
            key_points = post.get("key_points", [])
            consensus = post.get("consensus", "")
            disagreements = post.get("disagreements", "")
            action = post.get("action", "")
            with st.container():
                st.markdown(f"### {title}")
                st.caption(f"{item.get('created_at','')} · 话题：{item.get('topic','')}")
                st.info(summary or "无内容")
                if key_points:
                    st.markdown("**要点**")
                    for kp in key_points[:5]:
                        st.write(f"- {kp}")
                if consensus:
                    st.markdown(f"**共识**：{consensus}")
                if disagreements:
                    st.markdown(f"**分歧**：{disagreements}")
                if action:
                    st.markdown(f"**可执行建议**：{action}")
                st.divider()

    with st.expander("查看原始讨论记录", expanded=False):
        if st.session_state.square_history:
            for item in st.session_state.square_history:
                speaker = item.get("speaker", "")
                content = item.get("content", "")
                round_no = item.get("round", "")
                title = f"第{round_no}轮 · {speaker}" if round_no else speaker
                st.markdown(f"**{title}**")
                st.info(content or "无输出")
        else:
            st.caption("暂无原始讨论记录")
