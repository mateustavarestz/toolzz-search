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
        block_resources: bool = True,
        source: str | None = None, # New parameter
    ) -> tuple[str, str, str, str, list[str], dict[str, Any]]:
        """Navega para URL e retorna screenshot, html, texto, accessibility, imagens e metadata."""
        if not self.browser:
            raise RuntimeError("Browser nao inicializado")

        timeout = timeout or settings.BROWSER_TIMEOUT
        # Session Persistence Logic
        from urllib.parse import urlparse
        import os
        
        domain = urlparse(url).netloc.replace("www.", "")
        session_dir = "data/sessions"
        os.makedirs(session_dir, exist_ok=True)
        session_path = f"{session_dir}/{domain}.json"
        
        context_args = {
            "viewport": {"width": settings.VIEWPORT_WIDTH, "height": settings.VIEWPORT_HEIGHT},
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/133.0.0.0 Safari/537.36"
            ),
            "extra_http_headers": {
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
                "Sec-CH-UA-Platform": '"Windows"',
            },
        }
        
        if os.path.exists(session_path):
            logger.info(f"Carregando sessao existente para {domain}")
            context_args["storage_state"] = session_path

        context = await self.browser.new_context(**context_args)
        page = await context.new_page()
        await self._apply_stealth(page)
        
        if block_resources:
            await self._block_resources(page)  # OPTIMIZATION: Bloqueio de recursos conditionally

        try:
            try:
                response, resolved_wait_until = await self._goto_with_fallback(
                    page=page, url=url, preferred_wait_until=wait_until, timeout=timeout
                )
            except Exception as exc:
                # Se falhar com ERR_ABORTED, pode ser um download (ex: PDF)
                if "ERR_ABORTED" in str(exc) or "download" in str(exc):
                    logger.info(f"Navegacao abortada ({exc}), tentando fetch manual...")
                    response = await page.request.get(url)
                    resolved_wait_until = "fetch_fallback"
                else:
                    raise exc

            # Lógica Unificada de PDF
            if response:
                content_type = response.headers.get("content-type", "").lower()
                if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                    logger.info("PDF detectado. Baixando e extraindo texto...")
                    pdf_data = await response.body()
                    
                    import io
                    from pypdf import PdfReader
                    
                    try:
                        reader = PdfReader(io.BytesIO(pdf_data))
                        text_list = []
                        for page_num, pdf_page in enumerate(reader.pages):
                            text_list.append(pdf_page.extract_text() or "")
                        text_content = "\n".join(text_list)
                        html = f"<html><body><h1>Conteudo PDF: {url}</h1><pre>{text_content[:2000]}...</pre></body></html>"
                        screenshot_base64 = ""
                        
                        metadata = {
                            "requested_url": url,
                            "final_url": response.url,
                            "status": response.status,
                            "title": f"PDF: {url.split('/')[-1]}",
                            "auto_scroll": False,
                            "scroll_steps": 0,
                            "wait_until_used": resolved_wait_until,
                            "screenshot_mode": "pdf",
                            "content_type": "application/pdf",
                        }
                        return screenshot_base64, html, text_content, "", [], metadata
                    except Exception as exc:
                        logger.error(f"Erro ao ler PDF: {exc}")
                        if resolved_wait_until == "fetch_fallback":
                             raise NetworkScraperError(f"Falha ao ler PDF baixado: {exc}")

            # Se foi um fetch manual mas não era PDF (ou falhou leitura), e não temos page carregada...
            if resolved_wait_until == "fetch_fallback":
                 html = await response.text()
                 text_content = html[:5000]
                 metadata = {
                     "requested_url": url,
                     "final_url": response.url,
                     "status": response.status,
                     "title": "Fallback Fetch",
                     "auto_scroll": False,
                     "scroll_steps": 0,
                     "wait_until_used": "fetch_fallback",
                     "screenshot_mode": "none",
                 }
                 return "", html, text_content, "", [], metadata

            if auto_scroll:
                if source == "library:google_maps":
                     # Usa a nova logica de enriquecimento (Click & Connect)
                     # Limitamos a 10 itens para performance por padrao, ou passamos scroll_steps
                     await self._enrich_google_maps_list(page=page, max_items=10) # Hardcoded limit for safety/performance
                else:
                    await self._smart_scroll(page=page, max_steps=scroll_steps)  # OPTIMIZATION: Smart Scroll

            if execute_js:
                await page.evaluate(execute_js)
                await asyncio.sleep(1)
            
            # Save session state logic
            try:
                await context.storage_state(path=session_path)
                logger.info(f"Sessao salva para {domain}")
            except Exception as e:
                logger.warning(f"Nao foi possivel salvar sessao: {e}")

            screenshot_bytes, screenshot_mode = await self._capture_with_fallback(
                page=page,
                full_page=full_page,
                screenshot_quality=screenshot_quality,
            )
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            html = await page.content()
            
            # OPTIMIZATION: Accessibility Snapshot
            try:
                ax_tree = await page.accessibility.snapshot()
                import json
                accessibility_snapshot = json.dumps(ax_tree, ensure_ascii=False) if ax_tree else ""
            except Exception:
                accessibility_snapshot = ""

            # OPTIMIZATION: Extract Image URLs (Hybrid Approach)
            image_urls = await page.evaluate(
                """
                () => {
                    return Array.from(document.querySelectorAll('img'))
                        .map(img => img.src)
                        .filter(src => src && src.startsWith('http') && !src.includes('base64'))
                        .slice(0, 50); // Limit to 50 images
                }
                """
            )

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
            return screenshot_base64, html, text_content, accessibility_snapshot, image_urls, metadata

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
            r"\\bcaptcha\\b",
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

    async def _block_resources(self, page: Page) -> None:
        """Bloqueia recursos desnecessarios para economizar banda e tempo."""
        blocked_types = {"image", "font", "media", "stylesheet"}  # Stylesheet opcional, as vezes quebra layout visual
        # Para visao computacional, TALVEZ precisemos de imagens/css. 
        # Mas para velocidade, bloquear é melhor. 
        # Vamos bloquear imagens e fontes por enquanto.
        
        async def route_handler(route: Any) -> None:
            if route.request.resource_type in {"image", "media", "font"}:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

    async def _enrich_google_maps_list(self, page: Page, max_items: int = 10) -> None:
        """
        Scrolla a lista do Google Maps, clica nos itens para obter detalhes (Telefone, Site)
        e injeta esses dados de volta no item da lista para o LLM ler.
        """
        logger.info(f"Iniciando Enriquecimento do Google Maps (Click & Collect) - Top {max_items}...")
        
        # Seletor da Sidebar (Feed)
        sidebar_selector = "div[role='feed']"
        
        try:
            await page.wait_for_selector(sidebar_selector, timeout=5000)
        except PlaywrightTimeoutError:
            logger.warning("Google Maps Sidebar nao encontrada (div[role='feed']). Tentando scroll generico.")
            await self._smart_scroll(page, 10)
            return

        # 1. Scroll inicial para carregar batch de itens
        logger.info("Carregando itens iniciais...")
        # 1. Scroll inicial para carregar batch de itens
        logger.info("Carregando itens iniciais...")
        for _ in range(3):
            # Scrolla o elemento especifico usando argumentos para evitar erro de aspas
            await page.evaluate(
                "(selector) => { const el = document.querySelector(selector); if(el) el.scrollTop = el.scrollHeight; }", 
                sidebar_selector
            )
            await asyncio.sleep(1)

        # 2. Iterar e Enriquecer
        # Seleciona todos os artigos (itens da lista)
        # Nota: O seletor pode precisar de ajuste fino se o Maps mudar, mas div[role='article'] eh padrao.
        # Usamos locator.all() para pegar handles, mas cuidado com Stale Elements.
        # Melhor usar nth index para resilencia ao ir e voltar.
        
        # Contamos quantos temos agora (mas limitamos ao max_items)
        count = await page.locator(f"{sidebar_selector} > div[role='article']").count()
        limit = min(count, max_items)
        logger.info(f"Encontrados {count} itens. Enriquecendo os top {limit}...")

        for i in range(limit):
            try:
                # Re-seleciona item pelo indice (para evitar StaleElement se o DOM mudou)
                item_locator = page.locator(f"{sidebar_selector} > div[role='article']").nth(i)
                
                # Garante visibilidade
                if not await item_locator.is_visible():
                    await item_locator.scroll_into_view_if_needed()
                
                # Clica no item
                logger.info(f"Clicando no item {i+1}/{limit}...")
                await item_locator.click()
                
                # Espera painel de detalhes (role='main')
                # As vezes o Maps apenas abre um painel lateral maior, as vezes substitui.
                try:
                    await page.wait_for_selector("div[role='main']", timeout=4000)
                except PlaywrightTimeoutError:
                    logger.warning(f"Painel de detalhes nao abriu para item {i}. Tentando proximo.")
                    continue
                
                # Extrai dados do Painel de Detalhes via Python (Mais seguro que JS injection)
                try:
                    data = {"website": None, "phone": None, "address": None}
                    
                    # Website
                    website_loc = page.locator('a[data-item-id="authority"]')
                    if await website_loc.count() > 0 and await website_loc.is_visible():
                        data["website"] = await website_loc.get_attribute("href")

                    # Telefone (startswith phone)
                    phone_loc = page.locator('button[data-item-id^="phone"]')
                    if await phone_loc.count() > 0:
                        # Tenta aria-label primeiro, depois text
                        padding = await phone_loc.first.get_attribute("aria-label")
                        if not padding:
                            padding = await phone_loc.first.inner_text()
                        data["phone"] = padding

                    # Endereco
                    address_loc = page.locator('button[data-item-id="address"]')
                    if await address_loc.count() > 0:
                        padding = await address_loc.first.get_attribute("aria-label")
                        if not padding:
                            padding = await address_loc.first.inner_text()
                        data["address"] = padding

                    # Se nao achou nada, retorna null (nao injeta)
                    has_data = any(v is not None for v in data.values())
                    if not has_data:
                        enriched_html = None
                    else:
                        # Limpa dados
                        def clean(t):
                             return t.replace("\n", " ").strip() if t else "N/A"

                        website = data["website"] or "N/A"
                        phone = clean(data["phone"])
                        address = clean(data["address"])

                        enriched_html = (
                            f'<div class="toolzz-enriched-info" style="border: 2px solid #2AB17C; background: #e0ffee; color: #000; padding: 8px; margin-top: 5px; font-weight: bold; font-size: 13px; z-index: 9999;">'
                            f'[DADOS ENRIQUECIDOS]: '
                            f'WEBSITE: {website} '
                            f'TELEFONE: {phone} '
                            f'ENDERECO: {address}'
                            f'</div>'
                        )
                except Exception as e:
                    logger.warning(f"Erro na extracao Python do item {i}: {e}")
                    enriched_html = None
                
                # Volta para a lista
                # Procura botao voltar comum
                back_btn = page.locator("button[aria-label='Voltar'], button[aria-label='Back']")
                if await back_btn.count() > 0 and await back_btn.is_visible():
                    await back_btn.click()
                    # Espera lista reaparecer
                    await page.wait_for_selector(sidebar_selector, timeout=3000)
                
                # Injeta dados no item da lista
                if enriched_html:
                    # Precisa re-selecionar o item na lista pois o DOM pode ter sido recriado
                    item_locator_again = page.locator(f"{sidebar_selector} > div[role='article']").nth(i)
                    if await item_locator_again.is_visible():
                        await item_locator_again.evaluate(f"(el, html) => el.insertAdjacentHTML('beforeend', html)", enriched_html)
                        logger.info(f"Dados injetados no item {i+1}")
                
                await asyncio.sleep(0.5) # Throttle

            except Exception as e:
                logger.error(f"Erro ao enriquecer item {i}: {e}")
                # Tenta recuperar estado (clicar em voltar se estiver preso no detalhe)
                try:
                    back_btn = page.locator("button[aria-label='Voltar'], button[aria-label='Back']")
                    if await back_btn.is_visible():
                         await back_btn.click()
                         await asyncio.sleep(1)
                except:
                   pass

        logger.info("Enriquecimento finalizado.")

    async def _smart_scroll(self, page: Page, max_steps: int = 20) -> None:
        """Scroll inteligente que detecta carregamento de conteudo."""
        logger.info("Iniciando Smart Scroll...")
        last_height = await page.evaluate("document.body.scrollHeight")
        
        for i in range(max_steps):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            
            # Aguarda rede acalmar ou timeout curto
            try:
                await page.wait_for_load_state("networkidle", timeout=1500)
            except PlaywrightTimeoutError:
                pass # Rede ocupada, mas seguimos
            
            await asyncio.sleep(0.5) # Pequena pausa para JS reagir
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                # Tenta mais uma vez com espera maior para garantir
                await asyncio.sleep(1.0)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    logger.info(f"Smart Scroll finalizado no passo {i+1} (fim da pagina).")
                    break
            
            last_height = new_height
            
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
