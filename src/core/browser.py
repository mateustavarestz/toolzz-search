"""Browser manager usando Playwright."""
import asyncio
import base64
import re
from typing import Any

from loguru import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from src.core.errors import BlockedScraperError, NetworkScraperError
from src.config.settings import settings


class BrowserManager:
    """Gerencia navegador para captura de paginas."""

    def __init__(self) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    async def __aenter__(self) -> "BrowserManager":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.close()

    async def initialize(self) -> None:
        """Inicializa Playwright e Chromium."""
        logger.info("Inicializando Playwright...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        logger.info("Browser inicializado")

    async def navigate_and_capture(
        self,
        url: str,
        wait_until: str = "networkidle",
        timeout: int | None = None,
        screenshot_quality: int = 70,
        full_page: bool = False,
        execute_js: str | None = None,
        auto_scroll: bool = True,
        scroll_steps: int = 6,
    ) -> tuple[str, str, str, dict[str, Any]]:
        """Navega para URL e retorna screenshot, html, texto e metadata."""
        if not self.browser:
            raise RuntimeError("Browser nao inicializado")

        timeout = timeout or settings.BROWSER_TIMEOUT
        context = await self.browser.new_context(
            viewport={"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
                "Sec-CH-UA-Platform": '"Windows"',
            },
        )
        page = await context.new_page()
        await self._apply_stealth(page)

        try:
            response, resolved_wait_until = await self._goto_with_fallback(
                page=page, url=url, preferred_wait_until=wait_until, timeout=timeout
            )

            if auto_scroll:
                await self._auto_scroll(page=page, steps=scroll_steps)

            if execute_js:
                await page.evaluate(execute_js)
                await asyncio.sleep(1)

            screenshot_bytes, screenshot_mode = await self._capture_with_fallback(
                page=page,
                full_page=full_page,
                screenshot_quality=screenshot_quality,
            )
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            html = await page.content()
            text_content = await page.evaluate(
                """
                () => {
                    const body = document.body.cloneNode(true);
                    body.querySelectorAll("script, style, noscript, iframe").forEach(el => el.remove());
                    return body.innerText || "";
                }
                """
            )
            title = await page.title()
            block_reason = self._detect_block_reason(
                html=html,
                text_content=text_content,
                title=title,
                final_url=page.url,
                status_code=response.status if response else None,
            )
            if block_reason:
                raise BlockedScraperError(block_reason)

            metadata = {
                "requested_url": url,
                "final_url": page.url,
                "status": response.status if response else None,
                "title": title,
                "auto_scroll": auto_scroll,
                "scroll_steps": scroll_steps,
                "wait_until_used": resolved_wait_until,
                "screenshot_mode": screenshot_mode,
            }
            return screenshot_base64, html, text_content, metadata
        except PlaywrightTimeoutError as exc:
            raise NetworkScraperError(f"Timeout navegando em {url}: {exc}") from exc
        finally:
            await context.close()

    async def _goto_with_fallback(
        self,
        page: Any,
        url: str,
        preferred_wait_until: str,
        timeout: int,
    ) -> tuple[Any, str]:
        wait_modes = [preferred_wait_until, "load", "domcontentloaded", "networkidle"]
        seen: set[str] = set()
        ordered_modes = [m for m in wait_modes if not (m in seen or seen.add(m))]

        last_error: Exception | None = None
        for mode in ordered_modes:
            try:
                logger.info(f"Navegando com wait_until={mode}")
                return await page.goto(url, wait_until=mode, timeout=timeout), mode
            except PlaywrightTimeoutError as exc:
                last_error = exc
                logger.warning(f"Timeout em wait_until={mode}. Tentando fallback...")
        if last_error:
            raise last_error
        return await page.goto(url, wait_until=preferred_wait_until, timeout=timeout), preferred_wait_until

    async def _capture_with_fallback(
        self,
        page: Page,
        full_page: bool,
        screenshot_quality: int,
    ) -> tuple[bytes, str]:
        normalized_quality = max(35, min(screenshot_quality, 100))
        attempts = [
            ("requested", full_page, normalized_quality),
            ("viewport_high", False, max(60, normalized_quality)),
            ("viewport_low", False, 45),
            ("full_low", True, 45),
        ]
        last_exc: Exception | None = None
        for mode_name, use_full_page, quality in attempts:
            try:
                image = await page.screenshot(
                    full_page=use_full_page,
                    type="jpeg",
                    quality=quality,
                )
                return image, mode_name
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(f"Falha screenshot ({mode_name}): {exc}")
        raise NetworkScraperError(f"Nao foi possivel capturar screenshot: {last_exc}")

    async def _apply_stealth(self, page: Page) -> None:
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            window.chrome = window.chrome || { runtime: {} };
            """
        )

    def _detect_block_reason(
        self,
        html: str,
        text_content: str,
        title: str,
        final_url: str,
        status_code: int | None,
    ) -> str | None:
        candidate = " ".join(
            [html[:8_000].lower(), text_content[:4_000].lower(), (title or "").lower(), final_url.lower()]
        )
        blockers = [
            r"\bcaptcha\b",
            r"cloudflare",
            r"access denied",
            r"attention required",
            r"verify you are human",
            r"incapsula",
            r"bot detection",
            r"unusual traffic",
        ]
        for pattern in blockers:
            if re.search(pattern, candidate):
                return f"Possivel bloqueio detectado ({pattern})"
        if status_code in {401, 403, 429, 503}:
            return f"Status HTTP indica bloqueio/protecao: {status_code}"
        return None

    async def _auto_scroll(self, page: Any, steps: int = 6) -> None:
        """Faz scroll incremental para carregar lazy-loading."""
        safe_steps = max(1, min(steps, 20))
        for _ in range(safe_steps):
            await page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 0.9));")
            await asyncio.sleep(0.35)
        await page.evaluate("window.scrollTo(0, 0);")

    async def close(self) -> None:
        """Fecha recursos."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Browser fechado")

