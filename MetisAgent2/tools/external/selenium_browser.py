"""
Selenium Browser MCP Tool - Web browser automation and interaction
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mcp_core import MCPTool, MCPToolResult

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

logger = logging.getLogger(__name__)

class SeleniumBrowser(MCPTool):
    """Selenium browser automation MCP tool"""
    
    def __init__(self):
        super().__init__(
            name="selenium_browser",
            description="Web browser automation with Selenium - navigate, interact, scrape",
            version="1.0.0"
        )
        
        self.driver = None
        self.wait = None
        self.current_browser = None
        self.session_active = False
        
        # Register actions
        self._register_actions()
        
        logger.info("Selenium Browser MCP Tool initialized")
    
    def _register_actions(self):
        """Register all available actions"""
        
        # Browser management
        self.register_action(
            "start_browser",
            self._start_browser,
            required_params=["browser"],
            optional_params=["headless", "window_size", "user_agent", "proxy"]
        )
        
        self.register_action(
            "close_browser",
            self._close_browser,
            required_params=[],
            optional_params=[]
        )
        
        # Navigation
        self.register_action(
            "navigate",
            self._navigate,
            required_params=["url"],
            optional_params=["timeout"]
        )
        
        self.register_action(
            "refresh",
            self._refresh,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "back",
            self._back,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "forward",
            self._forward,
            required_params=[],
            optional_params=[]
        )
        
        # Element finding and interaction
        self.register_action(
            "find_element",
            self._find_element,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "find_elements",
            self._find_elements,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "click",
            self._click,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "double_click",
            self._double_click,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "right_click",
            self._right_click,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "type_text",
            self._type_text,
            required_params=["selector", "text"],
            optional_params=["by", "timeout", "clear_first"]
        )
        
        self.register_action(
            "clear_text",
            self._clear_text,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        # Form operations
        self.register_action(
            "select_dropdown",
            self._select_dropdown,
            required_params=["selector", "value"],
            optional_params=["by", "select_by", "timeout"]
        )
        
        self.register_action(
            "checkbox_toggle",
            self._checkbox_toggle,
            required_params=["selector"],
            optional_params=["by", "timeout", "state"]
        )
        
        # Information gathering
        self.register_action(
            "get_text",
            self._get_text,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "get_attribute",
            self._get_attribute,
            required_params=["selector", "attribute"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "get_page_source",
            self._get_page_source,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "get_title",
            self._get_title,
            required_params=[],
            optional_params=[]
        )
        
        self.register_action(
            "get_current_url",
            self._get_current_url,
            required_params=[],
            optional_params=[]
        )
        
        # Advanced operations
        self.register_action(
            "screenshot",
            self._screenshot,
            required_params=[],
            optional_params=["filename", "element_selector"]
        )
        
        self.register_action(
            "execute_script",
            self._execute_script,
            required_params=["script"],
            optional_params=["args"]
        )
        
        self.register_action(
            "scroll_to",
            self._scroll_to,
            required_params=["selector"],
            optional_params=["by", "timeout"]
        )
        
        self.register_action(
            "wait_for_element",
            self._wait_for_element,
            required_params=["selector"],
            optional_params=["by", "timeout", "condition"]
        )
        
        self.register_action(
            "submit_form",
            self._submit_form,
            required_params=["selector"],
            optional_params=["by", "timeout", "wait_for_page_load"]
        )
        
        self.register_action(
            "wait_for_url_change",
            self._wait_for_url_change,
            required_params=[],
            optional_params=["timeout", "expected_url"]
        )
        
        self.register_action(
            "wait_for_text",
            self._wait_for_text,
            required_params=["text"],
            optional_params=["timeout", "selector"]
        )
        
        self.register_action(
            "smart_wait",
            self._smart_wait,
            required_params=["condition"],
            optional_params=["timeout", "selector", "text", "url"]
        )
    
    def _check_session(self) -> bool:
        """Check if browser session is active"""
        return self.session_active and self.driver is not None
    
    def _get_by_type(self, by: str) -> By:
        """Convert string to By type"""
        by_map = {
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "link_text": By.LINK_TEXT,
            "partial_link_text": By.PARTIAL_LINK_TEXT
        }
        return by_map.get(by.lower(), By.CSS_SELECTOR)
    
    # Browser Management Actions
    def _start_browser(self, browser: str, headless: bool = True, 
                      window_size: str = "1920,1080", user_agent: str = None,
                      proxy: str = None) -> MCPToolResult:
        """Start browser session"""
        try:
            # Force close any existing session
            if self.session_active:
                try:
                    self._close_browser()
                    logger.info("Closed existing browser session")
                except:
                    pass
                self.session_active = False
            
            browser = browser.lower()
            
            if browser == "chrome":
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument(f"--window-size={window_size}")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                # DevToolsActivePort hatası için ek ayarlar
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-logging")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--ignore-ssl-errors")
                options.add_argument("--ignore-certificate-errors-spki-list")
                options.add_argument("--disable-features=VizDisplayCompositor")
                options.add_argument("--remote-debugging-port=0")  # Random port
                options.add_argument("--disable-background-timer-throttling")
                options.add_argument("--disable-renderer-backgrounding")
                options.add_argument("--disable-backgrounding-occluded-windows")
                options.add_argument("--disable-ipc-flooding-protection")
                options.add_argument("--disable-hang-monitor")
                options.add_argument("--disable-prompt-on-repost")
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-sync")
                options.add_argument("--force-color-profile=srgb")
                options.add_argument("--metrics-recording-only")
                options.add_argument("--disable-default-apps")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-translate")
                
                # Temporary directories
                import tempfile
                user_data_dir = tempfile.mkdtemp()
                options.add_argument(f"--user-data-dir={user_data_dir}")
                
                # More crash prevention
                options.add_argument("--disable-crash-reporter")
                options.add_argument("--disable-in-process-stack-traces")
                
                # Explicit binary path
                options.binary_location = "/usr/bin/google-chrome"
                
                if user_agent:
                    options.add_argument(f"--user-agent={user_agent}")
                if proxy:
                    options.add_argument(f"--proxy-server={proxy}")
                
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                
            elif browser == "firefox":
                options = webdriver.FirefoxOptions()
                if headless:
                    options.add_argument("--headless")
                
                if user_agent:
                    options.set_preference("general.useragent.override", user_agent)
                
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
                
                # Set window size for Firefox
                width, height = window_size.split(",")
                self.driver.set_window_size(int(width), int(height))
                
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unsupported browser: {browser}. Use 'chrome' or 'firefox'."
                )
            
            self.wait = WebDriverWait(self.driver, 10)
            self.current_browser = browser
            self.session_active = True
            
            return MCPToolResult(
                success=True,
                data={
                    "browser": browser,
                    "headless": headless,
                    "window_size": window_size,
                    "session_id": id(self.driver)
                },
                metadata={"action": "start_browser"}
            )
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _close_browser(self) -> MCPToolResult:
        """Close browser session"""
        try:
            if not self.session_active:
                return MCPToolResult(
                    success=False,
                    error="No active browser session to close"
                )
            
            if self.driver:
                self.driver.quit()
                self.driver = None
                self.wait = None
                self.current_browser = None
                self.session_active = False
            
            return MCPToolResult(
                success=True,
                data={"message": "Browser session closed successfully"},
                metadata={"action": "close_browser"}
            )
            
        except Exception as e:
            logger.error(f"Failed to close browser: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    # Navigation Actions
    def _navigate(self, url: str, timeout: int = 30) -> MCPToolResult:
        """Navigate to URL"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            self.driver.set_page_load_timeout(timeout)
            self.driver.get(url)
            
            return MCPToolResult(
                success=True,
                data={
                    "url": url,
                    "current_url": self.driver.current_url,
                    "title": self.driver.title
                },
                metadata={"action": "navigate"}
            )
            
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _refresh(self) -> MCPToolResult:
        """Refresh current page"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            self.driver.refresh()
            
            return MCPToolResult(
                success=True,
                data={"message": "Page refreshed successfully"},
                metadata={"action": "refresh"}
            )
            
        except Exception as e:
            logger.error(f"Failed to refresh page: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _back(self) -> MCPToolResult:
        """Go back in browser history"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            self.driver.back()
            
            return MCPToolResult(
                success=True,
                data={"current_url": self.driver.current_url},
                metadata={"action": "back"}
            )
            
        except Exception as e:
            logger.error(f"Failed to go back: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _forward(self) -> MCPToolResult:
        """Go forward in browser history"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            self.driver.forward()
            
            return MCPToolResult(
                success=True,
                data={"current_url": self.driver.current_url},
                metadata={"action": "forward"}
            )
            
        except Exception as e:
            logger.error(f"Failed to go forward: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    # Element Finding and Interaction
    def _find_element(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Find single element with smart selector fallback"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            
            # Smart selector fallback için özel durumlar
            selectors_to_try = [selector]
            
            # Google arama kutusu için fallback
            if selector == 'input[name="q"]':
                selectors_to_try = [
                    'textarea[name="q"]',
                    'input[name="q"]',
                    'input[title="Search"]',
                    'textarea[title="Search"]',
                    '#APjFqb',
                    '.gLFyf',
                    'input[aria-label="Search"]',
                    'textarea[aria-label="Search"]'
                ]
            
            # Her selector'ı dene
            element = None
            used_selector = selector
            
            for test_selector in selectors_to_try:
                try:
                    element = wait.until(EC.presence_of_element_located((by_type, test_selector)))
                    used_selector = test_selector
                    break
                except TimeoutException:
                    continue
            
            if element is None:
                return MCPToolResult(
                    success=False,
                    error=f"Element not found: {selector} (by {by}) within {timeout} seconds"
                )
            
            return MCPToolResult(
                success=True,
                data={
                    "found": True,
                    "tag_name": element.tag_name,
                    "text": element.text,
                    "is_displayed": element.is_displayed(),
                    "is_enabled": element.is_enabled(),
                    "used_selector": used_selector
                },
                metadata={"action": "find_element", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to find element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _find_elements(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Find multiple elements"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by_type, selector)))
            
            element_data = []
            for i, element in enumerate(elements):
                element_data.append({
                    "index": i,
                    "tag_name": element.tag_name,
                    "text": element.text[:100],  # Limit text length
                    "is_displayed": element.is_displayed(),
                    "is_enabled": element.is_enabled()
                })
            
            return MCPToolResult(
                success=True,
                data={
                    "count": len(elements),
                    "elements": element_data
                },
                metadata={"action": "find_elements", "selector": selector, "by": by}
            )
            
        except TimeoutException:
            return MCPToolResult(
                success=False,
                error=f"Elements not found: {selector} (by {by}) within {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to find elements: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _click(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Click element with smart selector fallback"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            
            # Smart selector fallback
            selectors_to_try = [selector]
            
            # Google arama kutusu için fallback
            if selector == 'input[name="q"]':
                selectors_to_try = [
                    'textarea[name="q"]',
                    'input[name="q"]',
                    'input[title="Search"]',
                    'textarea[title="Search"]',
                    '#APjFqb',
                    '.gLFyf'
                ]
            
            element = None
            used_selector = selector
            
            for test_selector in selectors_to_try:
                try:
                    element = wait.until(EC.element_to_be_clickable((by_type, test_selector)))
                    used_selector = test_selector
                    break
                except TimeoutException:
                    continue
            
            if element is None:
                return MCPToolResult(
                    success=False,
                    error=f"Element not clickable: {selector} (by {by}) within {timeout} seconds"
                )
            
            # JavaScript click fallback eğer normal click çalışmazsa
            try:
                element.click()
            except Exception:
                logger.warning(f"Normal click failed for {used_selector}, trying JavaScript click")
                self.driver.execute_script("arguments[0].click();", element)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Clicked element: {selector}",
                    "used_selector": used_selector
                },
                metadata={"action": "click", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to click element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _double_click(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Double click element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            action_chains = ActionChains(self.driver)
            action_chains.double_click(element).perform()
            
            return MCPToolResult(
                success=True,
                data={"message": f"Double clicked element: {selector}"},
                metadata={"action": "double_click", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to double click element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _right_click(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Right click element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            action_chains = ActionChains(self.driver)
            action_chains.context_click(element).perform()
            
            return MCPToolResult(
                success=True,
                data={"message": f"Right clicked element: {selector}"},
                metadata={"action": "right_click", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to right click element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _type_text(self, selector: str, text: str, by: str = "css", 
                   timeout: int = 10, clear_first: bool = True) -> MCPToolResult:
        """Type text into element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Typed text into element: {selector}",
                    "text_length": len(text)
                },
                metadata={"action": "type_text", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _clear_text(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Clear text from element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            element.clear()
            
            return MCPToolResult(
                success=True,
                data={"message": f"Cleared text from element: {selector}"},
                metadata={"action": "clear_text", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to clear text: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    # Form Operations
    def _select_dropdown(self, selector: str, value: str, by: str = "css", 
                        select_by: str = "value", timeout: int = 15) -> MCPToolResult:
        """Select option from dropdown with improved reliability"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            
            # Dropdown elementini bul ve bekle
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            # Dropdown görünür olana kadar bekle
            wait.until(EC.visibility_of(element))
            
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            select = Select(element)
            
            # Tüm seçenekleri al ve debug için yazdır
            all_options = select.options
            available_options = [opt.get_attribute("value") for opt in all_options]
            logger.info(f"Available dropdown options: {available_options}")
            
            # Seçimi yap
            if select_by == "value":
                select.select_by_value(value)
            elif select_by == "text":
                select.select_by_visible_text(value)
            elif select_by == "index":
                select.select_by_index(int(value))
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Invalid select_by parameter: {select_by}. Use 'value', 'text', or 'index'."
                )
            
            # Seçim başarılı olup olmadığını kontrol et
            selected_option = select.first_selected_option
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Selected option in dropdown: {selector}",
                    "selected_value": value,
                    "select_by": select_by,
                    "selected_text": selected_option.text,
                    "available_options": available_options
                },
                metadata={"action": "select_dropdown", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to select dropdown option: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _checkbox_toggle(self, selector: str, by: str = "css", 
                        timeout: int = 10, state: str = "toggle") -> MCPToolResult:
        """Toggle, check, or uncheck checkbox"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            current_state = element.is_selected()
            
            if state == "toggle":
                element.click()
                new_state = not current_state
            elif state == "check" and not current_state:
                element.click()
                new_state = True
            elif state == "uncheck" and current_state:
                element.click()
                new_state = False
            else:
                new_state = current_state
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Checkbox {state}: {selector}",
                    "previous_state": current_state,
                    "new_state": new_state
                },
                metadata={"action": "checkbox_toggle", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to toggle checkbox: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    # Information Gathering
    def _get_text(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Get text content of element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by_type, selector)))
            
            text = element.text
            
            return MCPToolResult(
                success=True,
                data={
                    "text": text,
                    "length": len(text)
                },
                metadata={"action": "get_text", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_attribute(self, selector: str, attribute: str, by: str = "css", 
                      timeout: int = 10) -> MCPToolResult:
        """Get attribute value of element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by_type, selector)))
            
            attr_value = element.get_attribute(attribute)
            
            return MCPToolResult(
                success=True,
                data={
                    "attribute": attribute,
                    "value": attr_value
                },
                metadata={"action": "get_attribute", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to get attribute: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_page_source(self) -> MCPToolResult:
        """Get page source HTML"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            source = self.driver.page_source
            
            return MCPToolResult(
                success=True,
                data={
                    "source": source,
                    "length": len(source)
                },
                metadata={"action": "get_page_source"}
            )
            
        except Exception as e:
            logger.error(f"Failed to get page source: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_title(self) -> MCPToolResult:
        """Get page title"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            title = self.driver.title
            
            return MCPToolResult(
                success=True,
                data={"title": title},
                metadata={"action": "get_title"}
            )
            
        except Exception as e:
            logger.error(f"Failed to get title: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _get_current_url(self) -> MCPToolResult:
        """Get current URL"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            url = self.driver.current_url
            
            return MCPToolResult(
                success=True,
                data={"url": url},
                metadata={"action": "get_current_url"}
            )
            
        except Exception as e:
            logger.error(f"Failed to get current URL: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    # Advanced Operations
    def _screenshot(self, filename: str = None, element_selector: str = None) -> MCPToolResult:
        """Take screenshot"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            if element_selector:
                # Screenshot of specific element
                by_type = self._get_by_type("css")
                element = self.driver.find_element(by_type, element_selector)
                success = element.screenshot(filename)
            else:
                # Full page screenshot
                success = self.driver.save_screenshot(filename)
            
            if success:
                return MCPToolResult(
                    success=True,
                    data={
                        "filename": filename,
                        "element_selector": element_selector
                    },
                    metadata={"action": "screenshot"}
                )
            else:
                return MCPToolResult(success=False, error="Failed to save screenshot")
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _execute_script(self, script: str, args: List = None) -> MCPToolResult:
        """Execute JavaScript"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            if args is None:
                args = []
            
            result = self.driver.execute_script(script, *args)
            
            return MCPToolResult(
                success=True,
                data={
                    "result": result,
                    "script_length": len(script)
                },
                metadata={"action": "execute_script"}
            )
            
        except Exception as e:
            logger.error(f"Failed to execute script: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _scroll_to(self, selector: str, by: str = "css", timeout: int = 10) -> MCPToolResult:
        """Scroll to element"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by_type, selector)))
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            
            return MCPToolResult(
                success=True,
                data={"message": f"Scrolled to element: {selector}"},
                metadata={"action": "scroll_to", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to scroll to element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _wait_for_element(self, selector: str, by: str = "css", 
                         timeout: int = 10, condition: str = "presence") -> MCPToolResult:
        """Wait for element with different conditions"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            
            condition_map = {
                "presence": EC.presence_of_element_located,
                "visible": EC.visibility_of_element_located,
                "clickable": EC.element_to_be_clickable,
                "invisible": EC.invisibility_of_element_located
            }
            
            if condition not in condition_map:
                return MCPToolResult(
                    success=False,
                    error=f"Invalid condition: {condition}. Use: {list(condition_map.keys())}"
                )
            
            element = wait.until(condition_map[condition]((by_type, selector)))
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Element condition '{condition}' met: {selector}",
                    "condition": condition
                },
                metadata={"action": "wait_for_element", "selector": selector, "by": by}
            )
            
        except TimeoutException:
            return MCPToolResult(
                success=False,
                error=f"Element condition '{condition}' not met: {selector} within {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to wait for element: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _submit_form(self, selector: str, by: str = "css", timeout: int = 15, 
                     wait_for_page_load: bool = True) -> MCPToolResult:
        """Submit form with proper waiting and error handling"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type(by)
            wait = WebDriverWait(self.driver, timeout)
            
            # Form elementini bul - submit buton veya form kendisi olabilir
            element = wait.until(EC.element_to_be_clickable((by_type, selector)))
            
            # Scroll to element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Mevcut URL'yi kaydet
            current_url = self.driver.current_url
            
            # Form submit yöntemini belirle
            if element.tag_name.lower() == "form":
                # Form elementiyse submit() kullan
                element.submit()
            elif element.tag_name.lower() in ["input", "button"]:
                # Submit butonuysa click kullan
                try:
                    element.click()
                except Exception:
                    # Normal click çalışmazsa JavaScript kullan
                    self.driver.execute_script("arguments[0].click();", element)
            else:
                # Diğer elementler için click dene
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
            
            # Sayfa yüklenmesini bekle
            if wait_for_page_load:
                try:
                    # URL değişimini bekle veya timeout
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.current_url != current_url
                    )
                except TimeoutException:
                    logger.warning("Page URL didn't change after form submit")
                
                # Sayfa yüklenmesini bekle
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Form submitted: {selector}",
                    "previous_url": current_url,
                    "current_url": self.driver.current_url,
                    "url_changed": self.driver.current_url != current_url
                },
                metadata={"action": "submit_form", "selector": selector, "by": by}
            )
            
        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _wait_for_url_change(self, timeout: int = 10, expected_url: str = None) -> MCPToolResult:
        """Wait for URL to change"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            current_url = self.driver.current_url
            
            if expected_url:
                # Belirli bir URL'yi bekle
                wait = WebDriverWait(self.driver, timeout)
                wait.until(lambda driver: driver.current_url == expected_url)
            else:
                # Herhangi bir URL değişimini bekle
                wait = WebDriverWait(self.driver, timeout)
                wait.until(lambda driver: driver.current_url != current_url)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": "URL changed successfully",
                    "previous_url": current_url,
                    "current_url": self.driver.current_url
                },
                metadata={"action": "wait_for_url_change"}
            )
            
        except TimeoutException:
            return MCPToolResult(
                success=False,
                error=f"URL did not change within {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to wait for URL change: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _wait_for_text(self, text: str, timeout: int = 10, selector: str = "body") -> MCPToolResult:
        """Wait for specific text to appear on page"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            by_type = self._get_by_type("css")
            wait = WebDriverWait(self.driver, timeout)
            
            # Text'in görünmesini bekle
            element = wait.until(EC.presence_of_element_located((by_type, selector)))
            wait.until(lambda driver: text in element.text)
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Text '{text}' found in {selector}",
                    "found_text": text,
                    "selector": selector
                },
                metadata={"action": "wait_for_text"}
            )
            
        except TimeoutException:
            return MCPToolResult(
                success=False,
                error=f"Text '{text}' not found within {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed to wait for text: {e}")
            return MCPToolResult(success=False, error=str(e))
    
    def _smart_wait(self, condition: str, timeout: int = 10, selector: str = None, 
                    text: str = None, url: str = None) -> MCPToolResult:
        """Smart wait with multiple condition options"""
        try:
            if not self._check_session():
                return MCPToolResult(success=False, error="No active browser session")
            
            wait = WebDriverWait(self.driver, timeout)
            
            if condition == "page_load":
                # Sayfa yüklenmesini bekle
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                
            elif condition == "ajax_complete":
                # AJAX isteklerinin bitmesini bekle (jQuery varsa)
                wait.until(lambda driver: driver.execute_script("return jQuery.active == 0") if 
                          driver.execute_script("return typeof jQuery != 'undefined'") else True)
                
            elif condition == "element_disappear" and selector:
                # Element'in kaybolmasını bekle
                by_type = self._get_by_type("css")
                wait.until(EC.invisibility_of_element_located((by_type, selector)))
                
            elif condition == "element_count" and selector:
                # Belirli sayıda element'in yüklenmesini bekle
                by_type = self._get_by_type("css")
                count = int(text) if text else 1
                wait.until(lambda driver: len(driver.find_elements(by_type, selector)) >= count)
                
            elif condition == "url_contains" and url:
                # URL'nin belirli bir metni içermesini bekle
                wait.until(EC.url_contains(url))
                
            elif condition == "title_contains" and text:
                # Sayfa başlığının belirli metni içermesini bekle
                wait.until(EC.title_contains(text))
                
            elif condition == "custom_js" and text:
                # Özel JavaScript koşulunun true dönmesini bekle
                wait.until(lambda driver: driver.execute_script(text))
                
            else:
                return MCPToolResult(
                    success=False,
                    error=f"Unknown condition: {condition}. Available: page_load, ajax_complete, element_disappear, element_count, url_contains, title_contains, custom_js"
                )
            
            return MCPToolResult(
                success=True,
                data={
                    "message": f"Smart wait condition '{condition}' met",
                    "condition": condition,
                    "selector": selector,
                    "text": text,
                    "url": url
                },
                metadata={"action": "smart_wait"}
            )
            
        except TimeoutException:
            return MCPToolResult(
                success=False,
                error=f"Smart wait condition '{condition}' not met within {timeout} seconds"
            )
        except Exception as e:
            logger.error(f"Failed smart wait: {e}")
            return MCPToolResult(success=False, error=str(e))

def register_tool(registry):
    """Register the Selenium Browser tool with the registry"""
    tool = SeleniumBrowser()
    return registry.register_tool(tool)

if __name__ == "__main__":
    # Test the tool
    tool = SeleniumBrowser()
    print(f"Selenium Browser MCP Tool initialized: {tool.name}")
    print(f"Available actions: {list(tool.actions.keys())}")