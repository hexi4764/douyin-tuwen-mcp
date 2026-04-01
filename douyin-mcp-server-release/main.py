#!/usr/bin/env python3
"""
抖音创作者平台工具 - MCP Server版本
使用playwright打开抖音创作者平台，支持cookie自动保存和自动登录
符合MCP HTTP协议的服务器实现
"""

import logging
import json
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import asynccontextmanager
from contextlib import AsyncExitStack
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from playwright.async_api import async_playwright, expect
import uvicorn

# URL配置
DOUYIN_LOGIN_URL = "https://creator.douyin.com/"
DOUYIN_ARTICLE_URL = "https://creator.douyin.com/creator-micro/content/post/article"

# Cookie存储路径
COOKIE_FILE = Path("douyin_cookies.json")
LOGIN_STATUS_FILE = Path("douyin_login_status.json")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('douyin_mcp.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("douyin-mcp-server")

# 导入完成后定义lifespan（必须在app创建之前定义）
import threading
import uuid

# 全局变量存储浏览器实例状态（使用线程锁防止竞态条件）
browser_status = {
    "is_running": False,
    "last_action": None,
    "last_action_time": None
}
browser_status_lock = threading.Lock()

# MCP Session管理
sessions = {}
sessions_lock = threading.Lock()

def create_session() -> str:
    """创建新的MCP会话"""
    session_id = str(uuid.uuid4())
    with sessions_lock:
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
    return session_id

def get_session(session_id: str) -> Optional[Dict]:
    """获取MCP会话"""
    with sessions_lock:
        session = sessions.get(session_id)
        if session:
            session["last_activity"] = datetime.now().isoformat()
        return session

# FastAPI Lifespan管理（必须在app创建之前定义）
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info("抖音MCP服务器启动中...")
    logger.info("MCP端点: http://127.0.0.1:18061/mcp")
    logger.info("健康检查: http://127.0.0.1:18061/health")
    yield
    # Shutdown  
    logger.info("抖音MCP服务器关闭中...")
    # 清理所有会话
    with sessions_lock:
        sessions.clear()

# 创建FastAPI应用 - MCP Server（现在lifespan已定义）
app = FastAPI(
    title="抖音自动发布MCP Server",
    description="基于MCP协议的抖音创作者平台自动化工具",
    version="1.0.0",
    docs_url=None,  # MCP服务不暴露文档
    redoc_url=None,
    lifespan=lifespan
)

# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

# Business Models
class PublishRequest(BaseModel):
    title: str
    content: str
    image: str

class StatusResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class LoginCheckResponse(BaseModel):
    success: bool
    logged_in: bool
    current_url: str
    page_title: str
    cookie_count: int
    message: str

import threading
from contextlib import asynccontextmanager
from contextlib import AsyncExitStack
import uuid

# 全局变量存储浏览器实例状态（使用线程锁防止竞态条件）
browser_status = {
    "is_running": False,
    "last_action": None,
    "last_action_time": None
}
browser_status_lock = threading.Lock()

# MCP Session管理
sessions = {}
sessions_lock = threading.Lock()

def create_session() -> str:
    """创建新的MCP会话"""
    session_id = str(uuid.uuid4())
    with sessions_lock:
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
    return session_id

def get_session(session_id: str) -> Optional[Dict]:
    """获取MCP会话"""
    with sessions_lock:
        session = sessions.get(session_id)
        if session:
            session["last_activity"] = datetime.now().isoformat()
        return session

# FastAPI Lifespan管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info("抖音MCP服务器启动中...")
    logger.info("MCP端点: http://127.0.0.1:18061/mcp")
    logger.info("健康检查: http://127.0.0.1:18061/health")
    yield
    # Shutdown  
    logger.info("抖音MCP服务器关闭中...")
    # 清理所有会话
    with sessions_lock:
        sessions.clear()

def update_browser_status(is_running: bool, action: str = None):
    """线程安全地更新浏览器状态"""
    with browser_status_lock:
        browser_status["is_running"] = is_running
        if action:
            browser_status["last_action"] = action
        browser_status["last_action_time"] = datetime.now().isoformat()

def create_mcp_response(result: Any = None, error: Dict[str, Any] = None, id: str = None) -> MCPResponse:
    """创建MCP响应"""
    return MCPResponse(
        id=id,
        result=result,
        error=error
    )

def create_mcp_error(code: int, message: str, id: str = None) -> MCPResponse:
    """创建MCP错误响应"""
    return MCPResponse(
        id=id,
        error={
            "code": code,
            "message": message
        }
    )

def load_cookies() -> List[Dict]:
    """加载保存的cookies"""
    if COOKIE_FILE.exists():
        try:
            with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                logger.info(f"已加载 {len(cookies)} 个cookie")
                return cookies
        except Exception as e:
            logger.error(f"加载cookie失败: {e}")
            return []
    return []

def clear_login_status():
    """清除登录状态标记"""
    if LOGIN_STATUS_FILE.exists():
        try:
            os.remove(LOGIN_STATUS_FILE)
            logger.info(f"已清除登录状态文件: {LOGIN_STATUS_FILE}")
        except Exception as e:
            logger.error(f"清除登录状态文件失败: {e}")

# MCP Tool Definitions
MCP_TOOLS = [
    {
        "name": "check_douyin_login_status",
        "description": "检查抖音创作者平台的登录状态。验证Cookie有效性，确认是否已登录。每次发布文章前应先调用此工具检查登录状态。返回登录状态、当前URL、页面标题、Cookie数量等信息。",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "publish_douyin_article",
        "description": "发布图文文章到抖音创作者平台。自动填写标题、正文内容、上传头图并选择配乐。首次使用会弹出浏览器窗口，需用抖音APP扫码登录，登录成功后Cookie自动保存，后续发布无需再次扫码。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "文章标题，建议10-30字，吸引眼球"
                },
                "content": {
                    "type": "string", 
                    "description": "文章正文内容，必须≥100字，建议200-500字，支持换行和emoji"
                },
                "image": {
                    "type": "string",
                    "description": "头图路径，支持绝对路径或相对路径，如 C:/Users/xxx/image.jpg 或 image/cover.jpg"
                }
            },
            "required": ["title", "content", "image"]
        }
    },
    {
        "name": "clear_douyin_cookies",
        "description": "清除本地保存的抖音登录Cookie。用于切换抖音账号或解决登录状态异常问题。清除后下次发布需要重新扫码登录。",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def save_cookies(cookies: List[Dict], is_logged_in: bool = True) -> None:
    """保存cookies到文件，并记录登录状态"""
    try:
        with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        status_data = {
            "logged_in": is_logged_in,
            "cookie_count": len(cookies),
            "last_updated": datetime.now().isoformat(),
            "cookie_file": str(COOKIE_FILE)
        }
        with open(LOGIN_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(cookies)} 个cookie到 {COOKIE_FILE}，登录状态: {'已登录' if is_logged_in else '未登录'}")
    except Exception as e:
        logger.error(f"保存cookie失败: {e}")

def load_login_status() -> dict:
    """加载登录状态信息"""
    if LOGIN_STATUS_FILE.exists():
        try:
            with open(LOGIN_STATUS_FILE, 'r', encoding='utf-8') as f:
                status = json.load(f)
                logger.info(f"已加载登录状态: {status}")
                return status
        except Exception as e:
            logger.error(f"加载登录状态失败: {e}")
            return {"logged_in": False, "error": str(e)}
    else:
        logger.info("登录状态文件不存在")
        return {"logged_in": False, "cookie_count": 0}

async def check_login_status(page) -> bool:
    """检查是否已登录"""
    try:
        await page.wait_for_timeout(2000)
        current_url = page.url
        is_logged_in = "creator-micro/home" in current_url or "creator-micro/content" in current_url
        logger.info(f"当前URL: {current_url}, 登录状态: {is_logged_in}")
        return is_logged_in
    except Exception as e:
        logger.error(f"检查登录状态失败: {e}")
        return False

# MCP Protocol Method Handlers
async def handle_tools_list() -> Dict[str, Any]:
    """处理tools/list方法"""
    return {
        "tools": MCP_TOOLS
    }

async def handle_tools_call(method_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """处理tools/call方法"""
    try:
        if method_name == "check_douyin_login_status":
            result = await check_login_status_detailed()
            return {
                "success": result["success"],
                "logged_in": result["logged_in"],
                "current_url": result["current_url"],
                "page_title": result["page_title"],
                "cookie_count": result["cookie_count"],
                "message": result["message"]
            }
        
        elif method_name == "publish_douyin_article":
            title = params.get("title")
            content = params.get("content")
            image = params.get("image")
            
            if not title or not content:
                raise ValueError("文章标题或内容不能为空")
            if len(content) < 100:
                raise ValueError(f"文章内容长度不足100字，当前长度: {len(content)}")
            
            # 在新线程中执行发布任务
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _open_creator_platform_internal(title, content, image))
                result = future.result(timeout=300)  # 5分钟超时
            
            return result
        
        elif method_name == "clear_douyin_cookies":
            result = await clear_cookies_internal()
            return {
                "success": result["success"],
                "message": result["message"]
            }
        
        else:
            raise ValueError(f"未知的方法: {method_name}")
            
    except Exception as e:
        logger.error(f"执行方法 {method_name} 失败: {str(e)}")
        raise

async def check_login_status_detailed() -> Dict[str, Any]:
    """详细检查登录状态（实际打开浏览器检测）"""
    logger.info("开始详细检查登录状态...")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            cookies = load_cookies()
            if cookies:
                await context.add_cookies(cookies)
                page = await context.new_page()
                await page.goto(DOUYIN_ARTICLE_URL)
                await page.wait_for_load_state("networkidle")
                url_logged_in = await check_login_status(page)
                current_url = page.url
                page_title = await page.title()
                has_title_element = False
                has_create_center = False
                
                # 先检查文章标题输入框
                try:
                    title_input_locator = page.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[1]/div/div[2]/div/div/div/input')
                    await title_input_locator.wait_for(timeout=5000)
                    has_title_element = True
                    logger.info("✓ 检测到文章标题输入框元素，用户已登录")
                except Exception:
                    logger.info("✗ 未检测到文章标题输入框元素")
                
                # 如果没找到标题输入框，检查创作中心元素
                if not has_title_element:
                    try:
                        create_center = page.locator('//*[@id="creator-home-left-content-id"]/div[1]/div[1]')
                        await create_center.wait_for(timeout=5000)
                        has_create_center = True
                        logger.info("✓ 检测到创作中心元素，用户已登录")
                    except Exception:
                        logger.info("✗ 未检测到创作中心元素")
                
                # 只要找到任一元素就认为登录成功
                is_truly_logged_in = url_logged_in and (has_title_element or has_create_center)
                cookie_list = await context.cookies()
                save_cookies(cookie_list, is_truly_logged_in)
                await browser.close()
                result = {
                    "success": True,
                    "logged_in": is_truly_logged_in,
                    "url_logged_in": url_logged_in,
                    "has_title_element": has_title_element,
                    "has_create_center": has_create_center,
                    "current_url": current_url,
                    "page_title": page_title,
                    "cookie_count": len(cookie_list),
                    "message": "已登录" if is_truly_logged_in else "未登录或cookie已失效"
                }
                result["login_status_valid"] = is_login_valid()
                logger.info(f"详细登录检查结果: {result}")
                return result
            else:
                save_cookies([], False)
                await browser.close()
                return {
                    "success": True,
                    "logged_in": False,
                    "url_logged_in": False,
                    "has_title_element": False,
                    "has_create_center": False,
                    "current_url": "",
                    "page_title": "",
                    "cookie_count": 0,
                    "login_status_valid": False,
                    "message": "未找到保存的cookie"
               }
    except Exception as e:
        error_msg = f"详细检查登录状态失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        save_cookies([], False)
        return {
            "success": False,
            "logged_in": False,
            "url_logged_in": False,
            "has_title_element": False,
            "has_create_center": False,
            "current_url": "",
            "page_title": "",
            "cookie_count": 0,
            "login_status_valid": False,
            "message": error_msg
        }

async def fill_article_form(page, title: str, content: str, image: str):
    """填写文章发布表单（image 为必需参数）"""
    logger.info("开始填写文章表单...")
    try:
        await expect(page.locator('//*[@id="DCPF"]')).to_be_visible(timeout=60000)
        logger.info("✓ 确认在文章编辑页面")
        title_input = page.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[1]/div/div[2]/div/div/div/input')
        await expect(title_input).to_be_visible(timeout=60000)
        await title_input.fill(title)
        logger.info("✓ 标题填写完成")
        await asyncio.sleep(0.5)
        content_input = page.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[3]/div[2]/div/div/div[2]/div')
        await expect(content_input).to_be_visible(timeout=60000)
        await content_input.fill(content)
        logger.info("✓ 正文填写完成")
        await asyncio.sleep(0.5)
        logger.info(f"上传文章头图: {image}")
        await asyncio.sleep(2)
        try:
            image_upload_area = page.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[4]/div[1]/div/span')
            await expect(image_upload_area).to_be_visible(timeout=5000)
            await image_upload_area.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            async with page.expect_file_chooser() as fc_info:
                upload_button = page.get_by_text("点击上传图片")
                await expect(upload_button).to_be_visible(timeout=5000)
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(image)
            logger.info("图片文件已选择，等待弹窗...")
            await asyncio.sleep(1)
            await page.get_by_text("确定").click()
            logger.info("已点击确定按钮，等待图片上传完成...")
            replace_image_xpath = '//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[4]/div[2]/div/span/div[1]/div/span[1]'
            try:
                await page.locator(replace_image_xpath).wait_for(timeout=60000)
                logger.info("图片上传完成，已出现'点击替换图片'按钮")
                await asyncio.sleep(2)
            except Exception as wait_e:
                logger.warning(f"等待图片上传超时: {wait_e}")
        except Exception as e:
                logger.error(f"上传文章头图失败: {e}")
        try:
            logger.info("滚动页面到选择配乐区域...")
            music_label = page.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[7]/div[1]/div/span')
            await expect(music_label).to_be_visible(timeout=5000)
            await music_label.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            select_music_btn = page.get_by_text("选择音乐")
            await expect(select_music_btn).to_be_visible(timeout=5000)
            await select_music_btn.click()
            logger.info("已点击选择音乐按钮，等待弹窗出现...")
            await asyncio.sleep(1)
            dialog = page.locator('[role="sidesheet"]')
            await expect(dialog).to_be_visible(timeout=10000)
            logger.info("音乐选择弹窗已出现")
            await asyncio.sleep(1)
            logger.info("选择第一首音乐...")
            first_music = dialog.locator('.card-container-tmocjc').first
            await expect(first_music).to_be_visible(timeout=5000)
            await first_music.hover()
            await asyncio.sleep(0.3)
            use_button = dialog.get_by_role("button", name="使用").first
            await expect(use_button).to_be_visible(timeout=3000)
            await use_button.click(force=True)
            logger.info("已点击使用按钮，等待音乐选择确认...")
            await expect(page.get_by_text("修改音乐")).to_be_visible(timeout=10000)
            logger.info("音乐选择成功，已出现'修改音乐'按钮")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"选择配乐失败: {e}")
        logger.info("表单填写完成")
    except Exception as e:
        logger.error(f"填写表单失败: {e}")
        raise

async def publish_article(page):
    """发布文章"""
    logger.info("准备发布文章...")
    try:
        publish_button = page.get_by_role("button", name="发布", exact=True)
        await publish_button.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        await publish_button.click()
        logger.info("已点击发布按钮，等待发布完成...")
        await page.wait_for_url("**/creator-micro/content/manage*", timeout=15000)
        logger.info("已跳转到内容管理页面，进一步验证发布状态...")
        try:
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(3000)
            logger.info("✓ 发布验证完成，文章发布成功")
        except Exception as verify_error:
            logger.warning(f"发布验证时出现异常，但URL跳转正常: {verify_error}")
    except Exception as e:
        logger.error(f"发布文章失败: {e}")
        raise

async def _open_creator_platform_internal(title: str, content: str, image: str = None) -> Dict[str, Any]:
    """内部函数：打开抖音创作者平台并自动发布文章"""
    logger.info("打开抖音创作者平台并自动发布文章")
    update_browser_status(True, "publish")
    if not title or not content:
        error_msg = "文章标题或内容不能为空"
        logger.error(error_msg)
        update_browser_status(False, "validation_error")
        raise ValueError(error_msg)
    if len(content) < 100:
        error_msg = f"文章内容长度不足100字，当前长度: {len(content)}"
        logger.error(error_msg)
        update_browser_status(False, "validation_error")
        raise ValueError(error_msg)
    logger.info(f"准备发布文章: {title}")
    try:
        async with async_playwright() as p:
            logger.info("启动浏览器")
            browser = await p.chromium.launch(headless=False)
            logger.info("浏览器已启动")
            cookies = load_cookies()
            if cookies:
                logger.info("检测到已保存的cookie，直接访问创作者中心")
                context = await browser.new_context()
                await context.add_cookies(cookies)
                page_obj = await context.new_page()
                logger.info(f"正在访问: {DOUYIN_ARTICLE_URL}")
                await page_obj.goto(DOUYIN_ARTICLE_URL)
                await page_obj.wait_for_load_state("networkidle")
                is_logged_in = await check_login_status(page_obj)
                if is_logged_in:
                    logger.info("cookie有效，登录成功")
                    logger.info(f"页面标题: {await page_obj.title()}")
                    await fill_article_form(page_obj, title, content, image)
                    await publish_article(page_obj)
                    result = {
                        "success": True,
                        "message": "文章发布成功",
                        "title": title,
                        "content_length": len(content),
                        "has_image": bool(image)
                    }
                else:
                    logger.warning("cookie已失效，需要重新登录")
                    await page_obj.goto(DOUYIN_LOGIN_URL)
                    await page_obj.wait_for_load_state("networkidle")
                    logger.info("请使用抖音APP扫码登录")
                    logger.info("等待登录完成（最多120秒）...")
                    try:
                        await page_obj.wait_for_url("**/creator-micro/**", timeout=120000)
                        logger.info("URL已跳转到创作者平台，进一步检查登录状态...")
                        await page_obj.wait_for_load_state("networkidle")
                        try:
                            title_input_locator = page_obj.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[1]/div/div[2]/div/div/div/input')
                            await title_input_locator.wait_for(timeout=10000)
                            logger.info("✓ 检测到文章标题输入框元素，确认登录成功！")
                            new_cookies = await context.cookies()
                            save_cookies(new_cookies, True)
                        except Exception as element_error:
                            logger.warning(f"✗ 未找到文章标题输入框，尝试查找创作中心元素...")
                            # 截图保存当前页面状态
                            screenshot_path = "login_debug.png"
                            await page_obj.screenshot(path=screenshot_path)
                            logger.info(f"已保存登录页面截图: {screenshot_path}")
                            try:
                                # 用用户提供的XPath定位创作中心元素
                                create_center = page_obj.locator('//*[@id="creator-home-left-content-id"]/div[1]/div[1]')
                                await create_center.wait_for(timeout=5000)
                                logger.info("✓ 找到创作中心元素，已登录，跳转到文章发布页面")
                                new_cookies = await context.cookies()
                                save_cookies(new_cookies, True)
                            except Exception as e2:
                                logger.warning(f"✗ 也未找到创作中心元素: {e2}")
                                save_cookies([], False)
                                raise Exception("登录验证失败：页面缺少必要的元素")
                    except Exception as url_error:
                        logger.error(f"等待登录URL跳转超时或失败: {url_error}")
                        save_cookies([], False)
                        raise
                    logger.info(f"跳转到文章发布页面: {DOUYIN_ARTICLE_URL}")
                    await page_obj.goto(DOUYIN_ARTICLE_URL)
                    await page_obj.wait_for_load_state("networkidle")
                    await fill_article_form(page_obj, title, content, image)
                    await publish_article(page_obj)
                    result = {
                        "success": True,
                        "message": "文章发布成功（重新登录）",
                        "title": title,
                        "content_length": len(content),
                        "has_image": bool(image)
                    }
            else:
                logger.info("未找到保存的cookie，需要登录")
                context = await browser.new_context()
                page_obj = await context.new_page()
                logger.info(f"正在访问登录页面: {DOUYIN_LOGIN_URL}")
                await page_obj.goto(DOUYIN_LOGIN_URL)
                await page_obj.wait_for_load_state("networkidle")
                logger.info("请使用抖音APP扫码登录")
                logger.info("等待登录完成（最多120秒）...")
                try:
                    await page_obj.wait_for_url("**/creator-micro/**", timeout=120000)
                    logger.info("URL已跳转到创作者平台，进一步检查登录状态...")
                    await page_obj.wait_for_load_state("networkidle")
                    try:
                        title_input_locator = page_obj.locator('//*[@id="DCPF"]/div/div[1]/div/div[1]/div[2]/div[1]/div/div[2]/div/div/div/input')
                        await title_input_locator.wait_for(timeout=10000)
                        logger.info("✓ 检测到文章标题输入框元素，确认登录成功！")
                        cookies = await context.cookies()
                        save_cookies(cookies, True)
                    except Exception as element_error:
                        logger.warning(f"✗ 未找到文章标题输入框，尝试查找创作中心元素...")
                        try:
                            # 用用户提供的XPath定位创作中心元素
                            create_center = page_obj.locator('//*[@id="creator-home-left-content-id"]/div[1]/div[1]')
                            await create_center.wait_for(timeout=5000)
                            logger.info("✓ 找到创作中心元素，已登录，跳转到文章发布页面")
                            cookies = await context.cookies()
                            save_cookies(cookies, True)
                        except Exception as e2:
                            logger.warning(f"✗ 也未找到创作中心元素: {e2}")
                            save_cookies([], False)
                            raise Exception("登录验证失败：页面缺少必要的元素")
                except Exception as url_error:
                    logger.error(f"等待登录URL跳转超时或失败: {url_error}")
                    save_cookies([], False)
                    raise
                logger.info(f"跳转到文章发布页面: {DOUYIN_ARTICLE_URL}")
                await page_obj.goto(DOUYIN_ARTICLE_URL)
                await page_obj.wait_for_load_state("networkidle")
                logger.info(f"页面标题: {await page_obj.title()}")
                await fill_article_form(page_obj, title, content, image)
                await publish_article(page_obj)
                result = {
                    "success": True,
                    "message": "文章发布成功（首次登录）",
                    "title": title,
                    "content_length": len(content),
                    "has_image": bool(image)
                }
            logger.info("文章发布成功，等待10秒后关闭浏览器...")
            await asyncio.sleep(10)
            logger.info("等待结束，关闭浏览器...")
            await browser.close()
            update_browser_status(False, "publish_success")
            return result
    except Exception as e:
        error_msg = f"打开浏览器失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        update_browser_status(False, "error")
        return {"success": False, "message": error_msg}

async def clear_cookies_internal() -> Dict[str, Any]:
    """内部函数：清除已保存的cookie和登录状态"""
    deleted_files = []
    errors = []
    if COOKIE_FILE.exists():
        try:
            os.remove(COOKIE_FILE)
            deleted_files.append(str(COOKIE_FILE))
            logger.info(f"已删除cookie文件: {COOKIE_FILE}")
        except Exception as e:
            error_msg = f"删除cookie文件失败: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    if LOGIN_STATUS_FILE.exists():
        try:
            os.remove(LOGIN_STATUS_FILE)
            deleted_files.append(str(LOGIN_STATUS_FILE))
            logger.info(f"已删除登录状态文件: {LOGIN_STATUS_FILE}")
        except Exception as e:
            error_msg = f"删除登录状态文件失败: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    try:
        clear_login_status()
    except Exception as e:
        error_msg = f"清除登录状态失败: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    if errors:
        return {"success": False, "message": f"部分文件删除失败: {'; '.join(errors)}", "deleted_files": deleted_files}
    elif deleted_files:
        return {"success": True, "message": "已清除cookie和登录状态，下次打开需要重新登录", "deleted_files": deleted_files}
    else:
        return {"success": True, "message": "没有找到cookie文件或登录状态文件"}

def is_login_valid() -> bool:
    """判断登录状态是否有效"""
    cookies = load_cookies()
    has_cookies = len(cookies) > 0 and COOKIE_FILE.exists()
    if not has_cookies:
        logger.info("登录状态无效：cookie不存在或为空")
        return False
    login_status_info = load_login_status()
    is_logged_in = login_status_info.get("logged_in", False)
    if not is_logged_in:
        logger.info("登录状态无效：登录状态标记为false")
        return False
    logger.info("登录状态有效：cookie存在且登录状态为true")
    return True

# MCP Protocol HTTP Endpoints

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP协议主入口"""
    try:
        body = await request.json()
        logger.info(f"收到MCP请求: {body.get('method')}")
        
        # 验证JSON-RPC格式
        if body.get("jsonrpc") != "2.0":
            return create_mcp_error(-32600, "Invalid Request", body.get("id"))
        
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        # 处理不同的MCP方法
        if method == "initialize":
            # 初始化连接
            session_id = create_session()
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "douyin-mcp-server",
                    "version": "1.0.0"
                }
            }
            response = create_mcp_response(result=result, id=request_id)
            # 设置session header
            response.headers = {"X-MCP-Session-Id": session_id}
            return response
            
        elif method == "tools/list":
            result = await handle_tools_list()
            return create_mcp_response(result=result, id=request_id)
            
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return create_mcp_error(-32602, "Missing tool name", request_id)
            
            try:
                result = await handle_tools_call(tool_name, arguments)
                return create_mcp_response(result={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }, id=request_id)
            except Exception as e:
                logger.error(f"工具调用失败 {tool_name}: {str(e)}")
                return create_mcp_error(-32000, f"Tool execution failed: {str(e)}", request_id)
                
        elif method == "ping":
            return create_mcp_response(result={}, id=request_id)
            
        else:
            return create_mcp_error(-32601, f"Method not found: {method}", request_id)
            
    except Exception as e:
        logger.error(f"MCP请求处理失败: {str(e)}")
        return create_mcp_error(-32603, "Internal error", None)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "douyin-mcp-server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "browser_running": browser_status["is_running"]
    }

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=18061,
        log_config=None,
        access_log=False
    )