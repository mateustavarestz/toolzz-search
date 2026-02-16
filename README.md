# Web Scraper Universal com IA

Sistema de scraping inteligente com `Playwright + GPT-5 mini`, capaz de extrair dados estruturados (JSON) de sites dinâmicos sem depender de seletores rígidos.

## Requisitos

- Python 3.11+
- Conexão com internet
- Chave de API da OpenAI

## Setup rápido

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
# source venv/bin/activate

pip install -r requirements.txt
playwright install chromium

copy .env.example .env
# Edite o arquivo .env e configure OPENAI_API_KEY
```

## Rodar exemplo

```bash
python examples/example_custom.py
```

## Rodar API backend

```bash
uvicorn src.web.main:app --reload
# alternativa robusta:
# python run_backend.py
```

API disponível em:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`

## Rodar frontend React (Vite)

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Abra:

- `http://127.0.0.1:5173`

O frontend chama o backend em `POST /api/scrape`.
Todos os scrapings (sucesso e erro) sao salvos no SQLite.
Para consultar historico: `GET /api/history?limit=20`.

### Modo recomendado (URL + prompt livre)

No frontend, use:
- `Schema`: `Guiado por prompt (recomendado)`
- Campo `Prompt da IA`: descreva exatamente o que deseja extrair

Exemplo de prompt:
- `Liste os 10 principais produtos com nome, preco, disponibilidade e URL.`

Esse modo usa:
- extração guiada por objetivo do usuário
- fallback de `wait_until` no navegador
- auto-scroll para conteúdo lazy-loading

## Diagnóstico de conexão local

Se aparecer "falha de conexão" no navegador:

1) Garanta que backend e frontend estão em terminais separados
- Backend na raiz do projeto (`toolzz-search`)
- Frontend dentro de `toolzz-search/frontend`

2) Teste backend no navegador
- `http://127.0.0.1:8000/health` deve retornar `{"status":"ok"}`

3) Teste frontend no navegador
- `http://127.0.0.1:5173`

4) Erro comum
- Rodar `uvicorn` dentro de `frontend` causa `ModuleNotFoundError: No module named 'src.web'`

## Limites práticos

O sistema foi reforçado para funcionar na maioria dos sites abertos, mas não existe garantia 100% universal em casos de:
- bloqueio anti-bot agressivo (WAF, challenge, CAPTCHA)
- login obrigatório / conteúdo privado
- conteúdo carregado por scripts bloqueados no ambiente

## Estrutura principal

- `src/core/browser.py`: navegação e captura com Playwright
- `src/core/ai_processor.py`: extração multimodal via OpenAI
- `src/core/orchestrator.py`: orquestração ponta a ponta
- `src/core/validator.py`: validação e normalização
- `src/core/storage.py`: persistência em SQLite + JSON
- `src/web/main.py`: backend API FastAPI
- `frontend/`: frontend React + Vite

## Testes

```bash
pytest tests/
```
