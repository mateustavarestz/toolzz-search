"""Motor Selenium com acoes atomicas e captura de estado."""
import asyncio
import base64
import time
from dataclasses import dataclass
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class SeleniumActionResult:
    success: bool
    error: str | None
    elapsed_seconds: float


class SeleniumBrowser:
    """Encapsula webdriver e operacoes atomicas para agente."""

    def __init__(self, headless: bool = True, timeout_ms: int = 30000) -> None:
        self.headless = headless
        self.timeout_s = max(5, timeout_ms // 1000)
        self.driver: webdriver.Chrome | None = None

    async def __aenter__(self) -> "SeleniumBrowser":
        await asyncio.to_thread(self.start)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await asyncio.to_thread(self.stop)

    def start(self) -> None:
        opts = ChromeOptions()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--window-size=1920,1080")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opts)
        self.driver.set_page_load_timeout(self.timeout_s)
        self.driver.implicitly_wait(2)

    def stop(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    async def execute_action(self, action: dict[str, Any]) -> SeleniumActionResult:
        start = time.perf_counter()
        try:
            action_name = action.get("action")
            target = action.get("target")
            value = action.get("value")
            if action_name == "goto":
                await asyncio.to_thread(self.goto, str(value or target or ""))
            elif action_name == "click":
                await asyncio.to_thread(self.click, str(target or ""))
            elif action_name == "type":
                await asyncio.to_thread(self.type_text, str(target or ""), str(value or ""))
            elif action_name == "scroll":
                await asyncio.to_thread(self.scroll, str(value or "down"))
            elif action_name == "wait":
                await asyncio.sleep(float(value or 1))
            elif action_name == "back":
                await asyncio.to_thread(self.back)
            elif action_name == "open_new_tab":
                await asyncio.to_thread(self.open_new_tab, str(value or target or ""))
            elif action_name in {"extract", "stop"}:
                pass
            else:
                return SeleniumActionResult(False, f"Acao desconhecida: {action_name}", time.perf_counter() - start)
            return SeleniumActionResult(True, None, time.perf_counter() - start)
        except Exception as exc:  # noqa: BLE001
            return SeleniumActionResult(False, str(exc), time.perf_counter() - start)

    def goto(self, url: str) -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        self.driver.get(url)

    def click(self, css_selector: str) -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        el = WebDriverWait(self.driver, self.timeout_s).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
        el.click()

    def type_text(self, css_selector: str, value: str) -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        el = WebDriverWait(self.driver, self.timeout_s).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        el.clear()
        el.send_keys(value)
        el.send_keys(Keys.ENTER)

    def scroll(self, direction: str = "down") -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        delta = -900 if direction == "up" else 900
        self.driver.execute_script(f"window.scrollBy(0, {delta});")

    def back(self) -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        self.driver.back()

    def open_new_tab(self, url: str) -> None:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        self.driver.switch_to.new_window("tab")
        if url:
            self.driver.get(url)

    async def capture_state(self, step_index: int, last_error: str | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._capture_state_sync, step_index, last_error)

    def _capture_state_sync(self, step_index: int, last_error: str | None = None) -> dict[str, Any]:
        if not self.driver:
            raise RuntimeError("Driver nao iniciado")
        try:
            html = self.driver.page_source or ""
            text_content = self.driver.execute_script("return document.body ? document.body.innerText : ''") or ""
            screenshot = self.driver.get_screenshot_as_png()
            b64 = base64.b64encode(screenshot).decode("utf-8")
            return {
                "step_index": step_index,
                "current_url": self.driver.current_url,
                "title": self.driver.title,
                "html_excerpt": html[:10000],
                "text_excerpt": text_content[:6000],
                "screenshot_base64": b64,
                "last_error": last_error,
            }
        except TimeoutException:
            return {
                "step_index": step_index,
                "current_url": self.driver.current_url,
                "title": self.driver.title,
                "html_excerpt": "",
                "text_excerpt": "",
                "screenshot_base64": None,
                "last_error": "timeout_capturing_state",
            }

