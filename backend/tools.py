from langchain_core.tools import tool
import subprocess
from playwright.async_api import async_playwright
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from playwright.async_api import async_playwright
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver 
import base64
import base64
from langchain.messages import HumanMessage, SystemMessage
import traceback
import subprocess
import tempfile
import os
import json
import asyncio
import sys
from browsermanager import browser, status_store
orginal_url = ""
def set_original_url(url):
    global orginal_url
    orginal_url = url
@tool
async def write_locust_script(filename, code_content):
    """
    Saves a Locust test script (Python file) to disk.
    """
    folder = r"D:\bugs"
    
    if not os.path.exists(folder):
        os.makedirs(folder)

    
    path = folder + "\\" + filename

    
    file = open(path, "w", encoding="utf-8")
    file.write(code_content)   
    file.close()               

    return "Locust script saved to " + path

@tool
async def run_locust_test(script_filename: str, host: str, users: int = 10, run_time: str = "30s") -> str:
    """
    Executes a Locust performance test using a previously saved script.
    """
    script_path = os.path.join(r"D:\bugs", script_filename)
    if not os.path.exists(script_path):
        return f" Script file not found: {script_path}"
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", script_path,
        "--host", host,
        "--users", str(users),
        "--run-time", run_time,
        "--headless",
        "--csv", os.path.join(r"D:\bugs", "locust_results")
    ]
    
    try:
       
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=int(run_time[:-1])*2 + 10)
        return f" Locust test finished.\nOutput:\n{stdout.decode()}\nErrors:\n{stderr.decode()}"
    except asyncio.TimeoutError:
        try:
            process.kill()
        except:
            pass
        return " Locust test timed out."
    except Exception as e:
        return f" Failed to run Locust: {str(e)}"


@tool
async def capture_and_analyze_screen(filename: str = "qa_evidence.png"):
    """It takes a picture and performs a visual analysis of the image."""

    page = await browser.init_browser()
    
    
    await page.screenshot(path=filename)
    
    
    with open(filename, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    
   
    
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": """Prepare a visual analysis of the image.

                         Describe the page you see.
                         What is its content, or what are the interactive and non-interactive elements it contains intended for?
                          Any apparent errors?
             this information is for ai agent work as qa automation 
             """},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            },
        ]
    )
    vision_model = ChatOpenAI(model="gpt-4o")
    
    #ChatGoogleGenerativeAI(
    #model="models/gemini-2.5-flash",
    #google_api_key="AIzaSyDYg8rqKQhvxo9NsMrbc6WuFUY4850ftvc"
    #)
    
    response = await vision_model.ainvoke([message])
    
    
    return f"here vision analysis: {response.content}" 
@tool
async def update_status(step: str, message: str = ""):
    """Update current QA testing status for UI/extension"""
    global status_store

    status_store["status"] = "running"
    status_store["step"] = step
    status_store["message"] = message

    return f"Status updated to: {step}"

@tool
async def navigate_to(url: str):
    """Navigates the browser to a specific URL."""
    page = await browser.init_browser()
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    return f"we reach this url: {url}"

@tool
async def navigate_toorginal():
    """back to orginal page after clicking and go to i=other page"""
    page = await browser.init_browser()
    await page.goto(orginal_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    return f"we reach this url: {orginal_url}"
@tool
async def perform_click(selector: str):
    """Clicks on a visible HTML element using a robust strategy."""
    page = await browser.init_browser()
    try:
        locator = page.locator(selector)

       
        await locator.first.wait_for(state="visible", timeout=10000)

        # scroll
        await locator.first.scroll_into_view_if_needed()

       
        try:
            await locator.first.click(timeout=5000)
        except:
            
            await page.evaluate("""(sel) => {
                const el = document.querySelector(sel);
                if (el) el.click();
            }""", selector)

        return f" Clicked: {selector}"

    except Exception as e:
        return f" Failed: {selector} | Reason: {str(e)}"

@tool 
async def type_text(selector: str, text: str):
    """Types text into an input field."""
    page = await browser.init_browser()
    await page.wait_for_selector(selector, timeout=30000)
    await page.fill(selector, text)
    return f"this text:{text} was filled in this  {selector}"
#gpt 5.4 mini
from langchain_core.tools import tool
import os

@tool
async def capture_screen(filename: str = "qa_evidence.png") -> str:
    """Take screenshot as evidence of the bug"""
    page = await browser.init_browser()
    full_path = os.path.join(r"D:\bugs", filename)
    
    try:
        # Playwright will automatically fail if directory doesn't exist,
        # so we ensure it exists in one simple line before taking the shot.
        os.makedirs(r"D:\bugs", exist_ok=True)
        
        await page.screenshot(path=full_path)
        return f"Screenshot saved to: {full_path}"
    except Exception as e:
        return f"Failed: {str(e)}"
@tool
async def get_url():
    """method to return page url so you can know where you are and if you are in the 
    orginal page or not"""
    page=await browser.init_browser()
    url=page.url
    return f"here the page url: {url}"

@tool
async def analyze_page():
    """Returns exact CSS selectors and labels for interactive elements."""
    page = await browser.init_browser()
    elements = await page.evaluate("""() => {
        return Array.from(document.querySelectorAll('input, button, a, [role="button"]'))
            .filter(el => {
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
            })
            .slice(0, 20)
            .map(el => {
               
                const tag = el.tagName.toLowerCase();
                const id = el.id ? `#${el.id}` : '';
                                   
                                   
                const classes = el.className && typeof el.className === 'string' 
                                ? `.${el.className.trim().split(/\\s+/).join('.')}` : '';
                                   

                const selector = el.id ? `#${el.id}` :
                  el.getAttribute('data-testid') ? `[data-testid="${el.getAttribute('data-testid')}"]` :
                  el.getAttribute('aria-label') ? `[aria-label="${el.getAttribute('aria-label')}"]` :
                  el.name ? `${tag}[name="${el.name}"]` :
                  el.href ? `a[href="${el.getAttribute('href')}"]` :
                  tag;
                const label = el.innerText || el.placeholder || el.value || 'No Label';
                
                return `Selector: [ ${selector} ] | Label: "${label}" | Tag: <${tag}>`;
            })
            .join('\\n');
    }""")
    return f"Visible Interactive Elements:\\n{elements}"
@tool
async def write_ui_script(filename: str, code_content: str):
    """
    Saves a Playwright UI test script (Python file) to disk.
    """
    folder = r"D:\bugs\ui_tests"
    
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    path = os.path.join(folder, filename)
    
    with open(path, "w", encoding="utf-8") as file:
        file.write(code_content)              

    return f"UI Automation script saved to {path}"
@tool
async def run_ui_test(script_filename: str, timeout: int = 60) -> str:
    """
    Executes a saved Playwright UI test script and returns the console output.
    """
    script_path = os.path.join(r"D:\bugs\ui_tests", script_filename)
    if not os.path.exists(script_path):
        return f"Script file not found: {script_path}"
    
    cmd = [sys.executable, script_path]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        output = stdout.decode('utf-8', errors='ignore')
        errors = stderr.decode('utf-8', errors='ignore')
        
        if process.returncode == 0:
            return f"UI Test passed successfully.\nOutput:\n{output}"
        else:
            return f"UI Test failed.\nOutput:\n{output}\nErrors:\n{errors}"
            
    except asyncio.TimeoutError:
        try:
            process.kill()
        except:
            pass
        return "UI Test execution timed out."
    except Exception as e:
        return f"Failed to run UI Test: {str(e)}"
@tool
async def get_accessibility_tree() -> str:
    """
    Returns the page's accessibility tree. 
    This helps the agent understand the semantic structure and interactive roles 
    of elements (e.g., buttons, landmarks, text fields) as a simplified hierarchy.
    """
    page = await browser.init_browser()
    try:
        # Create a Chrome DevTools Protocol session for the current page
        cdp_session = await page.context.new_cdp_session(page)
        
        # Request the full accessibility tree from the browser
        result = await cdp_session.send("Accessibility.getFullAXTree")
        
        # Return the tree as a serialized JSON string for the agent to parse
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"Failed to capture accessibility tree due to error: {str(e)}"
@tool
async def smart_click(text: str):
    "click on element by text "
    page = await browser.init_browser()
    try:
        await page.get_by_text(text).first.click(timeout=5000)
        return f"clicked by text: {text}"
    except:
        return f"failed to click text: {text}"
@tool
async def press_key(key: str = "Enter"):
    """Presses a keyboard key (extra, 'Enter', 'Tab', 'ArrowDown')."""
    page = await browser.init_browser()
    await page.keyboard.press(key)
    return f"was clicked{key}"
@tool
async def writebug(req:str):
    """this tool allow ou to write a bug on notebad """
    file=open(r"D:\bug.txt", 'a', encoding='utf-8')
    file.write(f"{req}  \n")


