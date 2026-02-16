# Toolzz Search 🔍🤖

Sistema de scraping inteligente que combina **Playwright** (navegador headless) com **GPT-5 mini** (visão + texto) para extrair dados estruturados de qualquer página web.

---

## Como Funciona

```
URL + Prompt do Usuário
        │
        ▼
┌─────────────────────┐
│   Playwright Browser │  ← Stealth mode, anti-bot, smart scroll
│   (Chromium headless) │
└────────┬────────────┘
         │  Screenshot + HTML + Texto + Accessibility Tree + Image URLs
         ▼
┌─────────────────────┐
│   GPT-5 mini (IA)    │  ← Visão multimodal + contexto semântico
│   Extração com schema │
└────────┬────────────┘
         │  JSON estruturado
         ▼
┌─────────────────────┐
│   Validação + SQLite │  ← Persistência automática
└─────────────────────┘
```

**Pipeline completo:**
1. O usuário informa uma **URL** e um **prompt** descrevendo o que quer extrair.
2. O **Playwright** navega até a página com stealth (anti-detecção de bot).
3. O **Smart Scroll** rola a página detectando carregamento dinâmico.
4. O browser captura: **screenshot**, **HTML**, **texto renderizado**, **árvore de acessibilidade** e **URLs de imagens**.
5. Tudo é enviado ao **GPT-5 mini** que extrai dados estruturados em JSON.
6. Os dados são **validados** contra um schema Pydantic.
7. O resultado é **salvo no SQLite** e retornado ao frontend.

---

## Requisitos

- Python 3.11+
- Node.js 18+
- Chave de API da OpenAI (`OPENAI_API_KEY`)

---

## Setup Rápido

### Backend

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Instalar navegador do Playwright
playwright install chromium

# Configurar variáveis de ambiente
copy .env.example .env
# Edite .env e configure OPENAI_API_KEY
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
```

---

## Rodar

### Backend (API)

```bash
python run_backend.py
```

- API: `http://127.0.0.1:8000`
- Docs (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### Frontend (React + Vite)

```bash
cd frontend
npm run dev
```

- Interface: `http://127.0.0.1:5173`

---

## Formatos de Saída

O sistema oferece **3 formatos** que alteram como a IA processa e retorna os dados:

| Formato | Campo `summary` | Campo `findings` | Uso ideal |
|---|---|---|---|
| **Lista** | Contexto breve | Muitos itens estruturados (título, descrição, URL, extras) | Produtos, links, contatos |
| **Resumo** | Parágrafo denso com pontos-chave em **negrito** | Poucos tópicos cruciais | Visão geral rápida |
| **Relatório Completo** | Documento Markdown rico com títulos, listas e imagens | Extração extensa e analítica | Análise profunda |

### Exemplo de uso

1. **Lista**: "Liste os 10 principais produtos com nome, preço e link"
2. **Resumo**: "Resuma o conteúdo principal desta página"
3. **Relatório**: "Faça uma análise completa desta página com todos os detalhes"

No modo **Relatório Completo**, a IA inclui automaticamente as imagens encontradas na página dentro do texto Markdown.

---

## Otimizações do Browser

O sistema implementa diversas otimizações para performance e stealth:

### 🛡️ Anti-Detecção (Stealth)
- Remove `navigator.webdriver`
- Define `navigator.languages`, `platform`, `hardwareConcurrency`
- Injeta `window.chrome.runtime`
- User-Agent realista (Chrome 133, Windows)
- Headers `Accept-Language`, `Sec-CH-UA-Platform`

### ⚡ Resource Blocking
- Bloqueia carregamento de **imagens**, **fontes** e **mídia** por padrão
- Economiza banda e acelera carregamento
- Desativável por estratégia de fallback

### 📜 Smart Scroll
- Rola a página incrementalmente
- Detecta quando o conteúdo parou de carregar (compara `scrollHeight`)
- Aguarda `networkidle` entre scrolls
- Para automaticamente quando atinge o fim da página

### 💾 Session Persistence
- Salva cookies e storage state por domínio em `data/sessions/`
- Reutiliza sessões em scrapes futuros do mesmo domínio
- Útil para sites que lembram preferências ou aceitação de cookies

### 🌳 Accessibility Tree
- Captura a árvore de acessibilidade do Chrome
- Envia para a IA como contexto semântico (muito menor que HTML bruto)
- Reduz tokens consumidos e melhora precisão

### 🖼️ Image URL Extraction
- Extrai URLs de até 50 imagens da página
- As URLs são passadas para a IA
- No modo **Relatório**, a IA inclui imagens relevantes no texto Markdown

---

## API Endpoints

### `POST /api/scrape`

Executa um scraping completo.

```json
{
  "url": "https://example.com",
  "schema": "guided_extract",
  "prompt": "generic",
  "user_prompt": "Liste os produtos com nome e preço",
  "output_format": "list",
  "wait_until": "networkidle",
  "timeout": 30000,
  "screenshot_quality": 70,
  "full_page": false,
  "auto_scroll": true,
  "scroll_steps": 6
}
```

**Resposta:**

```json
{
  "success": true,
  "data": {
    "summary": "Resumo gerado pela IA...",
    "findings": [
      {
        "title": "Produto X",
        "description": "Descrição...",
        "url": "https://...",
        "extra": { "preco": "99.90" }
      }
    ]
  },
  "metadata": {
    "url": "https://example.com",
    "model_used": "gpt-5-mini-2025-08-07",
    "tokens_used": { "prompt": 1500, "completion": 300, "total": 1800 },
    "cost_usd": 0.0012,
    "duration_seconds": 8.5,
    "quality": { "quality_score": 0.95 }
  },
  "record_id": 42
}
```

### `GET /api/history`

Consulta histórico de scrapes salvos no SQLite.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `limit` | int | Quantidade de registros (padrão: 20) |
| `success` | bool | Filtrar por sucesso/falha |
| `domain` | string | Filtrar por domínio |

### `GET /health`

Retorna `{"status": "ok"}` se o backend está rodando.

---

## Variáveis de Ambiente (.env)

```env
# Obrigatória
OPENAI_API_KEY=sk-...

# Opcionais (valores padrão mostrados)
OPENAI_MODEL=gpt-5-mini-2025-08-07
HEADLESS=true
BROWSER_TIMEOUT=30000
VIEWPORT_WIDTH=1920
VIEWPORT_HEIGHT=1080
MAX_CONCURRENT_TASKS=3
RETRY_ATTEMPTS=3
RETRY_DELAY=2
DATABASE_URL=sqlite+aiosqlite:///./data/scraper_data.db
LOG_LEVEL=INFO
```

---

## Estrutura do Projeto

```
toolzz-search/
├── run_backend.py              # Entry point do servidor
├── requirements.txt            # Dependências Python
├── .env                        # Variáveis de ambiente
│
├── src/
│   ├── config/
│   │   ├── settings.py         # Configurações (Pydantic Settings)
│   │   └── prompts.py          # System prompts da IA
│   │
│   ├── core/
│   │   ├── browser.py          # Playwright: stealth, scroll, captura
│   │   ├── ai_processor.py     # GPT-5 mini: extração multimodal
│   │   ├── orchestrator.py     # Pipeline: browser → IA → validação
│   │   ├── validator.py        # Validação de dados extraídos
│   │   ├── storage.py          # Persistência SQLite + JSON
│   │   └── errors.py           # Exceções customizadas
│   │
│   ├── models/
│   │   └── schemas.py          # Schemas Pydantic (GuidedExtract, etc.)
│   │
│   ├── utils/
│   │   ├── helpers.py          # clean_html, utilitários
│   │   ├── cost_tracker.py     # Cálculo de custo por request
│   │   └── logger.py           # Configuração do Loguru
│   │
│   └── web/
│       └── main.py             # FastAPI: rotas /api/scrape, /api/history
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Componente principal React
│   │   └── index.css           # Estilos globais
│   ├── package.json
│   └── vite.config.ts
│
├── data/
│   ├── scraper_data.db         # SQLite (gerado automaticamente)
│   ├── sessions/               # Cookies salvos por domínio
│   └── screenshots/            # Screenshots salvos
│
└── logs/
    └── scraper.log             # Logs estruturados (Loguru)
```

---

## Limites Conhecidos

- **Anti-bot agressivo**: WAFs como Cloudflare Challenge, CAPTCHAs visuais e Incapsula podem bloquear.
- **Login obrigatório**: Conteúdo atrás de autenticação não é acessível automaticamente.
- **Sites muito pesados**: Páginas com muitos MBs de JavaScript podem causar timeout.
- **Rate limiting**: Scrapes frequentes no mesmo domínio podem ser bloqueados.

O sistema detecta automaticamente bloqueios (CAPTCHA, 403, 429) e reporta no resultado.

---

## Testes

```bash
pytest tests/
```
