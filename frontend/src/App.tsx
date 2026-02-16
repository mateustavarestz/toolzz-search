import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";

type ScrapeResponse = Record<string, unknown>;
type DataMap = Record<string, unknown>;

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const EXECUTION_STAGES = [
  "Preparando requisicao",
  "Navegando no site",
  "Capturando conteudo",
  "Processando com IA",
  "Validando e persistindo",
];
const PROMPT_TEMPLATES: Record<string, string> = {
  products: "Liste os 10 principais produtos com nome, preco, disponibilidade e URL.",
  article:
    "Extraia titulo, autor, data e os principais pontos do conteudo em itens objetivos.",
  contacts: "Extraia contatos visiveis (email, telefone, formulario, redes sociais) com links.",
  offers: "Capture ofertas em destaque com titulo, preco, desconto e validade quando existir.",
  custom: "Busque os dados mais relevantes desta pagina e retorne itens estruturados.",
};

export default function App() {
  const [url, setUrl] = useState("");
  const [userPrompt, setUserPrompt] = useState(
    "Busque os dados mais relevantes desta pagina e retorne itens estruturados.",
  );
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [executionStage, setExecutionStage] = useState<string>("Pronto");
  const [result, setResult] = useState<ScrapeResponse | null>(null);
  const [history, setHistory] = useState<ScrapeResponse[]>([]);
  const [apiHealth, setApiHealth] = useState<"checking" | "ok" | "down">("checking");
  const [outputFormat, setOutputFormat] = useState("list");
  const [historyStatus, setHistoryStatus] = useState<"all" | "success" | "error">("all");
  const [historyDomain, setHistoryDomain] = useState("");


  const prettyResult = useMemo(
    () => (result ? JSON.stringify(result, null, 2) : "{}"),
    [result],
  );
  const resultSuccess = result?.success === true;
  const resultMeta = (result?.metadata as DataMap | undefined) ?? {};
  const resultData = (result?.data as DataMap | undefined) ?? {};
  const resultFindings = Array.isArray(resultData.findings)
    ? (resultData.findings as DataMap[])
    : Array.isArray(resultData.items)
      ? (resultData.items as DataMap[])
      : [];
  const resultSummary = (resultData.summary as string | undefined) ?? "";
  const qualityMeta = (resultMeta.quality as DataMap | undefined) ?? {};
  const tokens = (resultMeta.tokens_used as DataMap | undefined) ?? {};

  async function runScrape() {
    if (!url.trim()) {
      setStatus("Informe uma URL.");
      return;
    }

    setLoading(true);
    setStatus("Executando scraping...");
    setExecutionStage(EXECUTION_STAGES[0]);
    setResult(null);

    try {
      // Defaulting to standard scraping (Playwright) mostly
      const endpoint = "/api/scrape";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url.trim(),
          schema: "guided_extract",
          prompt: "generic",
          user_prompt: userPrompt,
          wait_until: "networkidle",
          timeout: 30000,
          screenshot_quality: 70,
          full_page: false,
          auto_scroll: true,
          scroll_steps: 6,
          output_format: outputFormat,
        }),
      });
      const data = (await response.json()) as ScrapeResponse;
      setResult(data);
      const recordId = data.record_id as number | undefined;
      setStatus(recordId ? `Concluido. Registro salvo #${recordId}.` : "Concluido.");
      setExecutionStage("Concluido");
      await loadHistory();
    } catch (error) {
      setResult({
        success: false,
        error: `Falha de conexao com API (${API_BASE || "proxy local /api"}). Detalhe: ${String(error)}`,
      });
      setStatus("Erro na requisicao. Verifique backend/CORS.");
      setExecutionStage("Falha");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
    try {
      const params = new URLSearchParams();
      params.set("limit", "20");
      if (historyStatus === "success") params.set("success", "true");
      if (historyStatus === "error") params.set("success", "false");
      if (historyDomain.trim()) params.set("domain", historyDomain.trim());
      const response = await fetch(`${API_BASE}/api/history?${params.toString()}`);
      const data = (await response.json()) as { items?: ScrapeResponse[] };
      setHistory(data.items ?? []);
    } catch (_error) {
      setStatus("Nao foi possivel carregar historico.");
    }
  }

  async function checkApi() {
    setApiHealth("checking");
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (!response.ok) {
        setApiHealth("down");
        return;
      }
      setApiHealth("ok");
    } catch (_error) {
      setApiHealth("down");
    }
  }

  useEffect(() => {
    void checkApi();
    void loadHistory();
  }, []);

  useEffect(() => {
    if (!loading) return;
    let idx = 0;
    const timer = setInterval(() => {
      idx = (idx + 1) % EXECUTION_STAGES.length;
      setExecutionStage(EXECUTION_STAGES[idx]);
    }, 1600);
    return () => clearInterval(timer);
  }, [loading]);

  return (
    <main className="page">
      <header className="hero">
        <h1>Toolzz Search</h1>
        <p>Scraping inteligente com URL + instrução para IA.</p>
        <div className={`apiStatus ${apiHealth}`}>
          API: {apiHealth === "ok" ? "conectada" : apiHealth === "down" ? "inacessivel" : "checando..."} ({API_BASE || "proxy local /api"})
        </div>
      </header>

      <section className="card glass">
        <div className="sectionTitle">
          <h2>Novo scraping</h2>
        </div>

        <p className="stageText">
          Etapa atual: <strong>{executionStage}</strong>
        </p>

        <div className="grid">
          <div className="full">
            <label>URL</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              type="url"
            />
          </div>

          <div>
            <label>Formato de Saída</label>
            <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
              <option value="list">Lista (Padrão)</option>
              <option value="summary">Resumo</option>
              <option value="report">Relatório Completo</option>
            </select>
          </div>

          <div className="full">
            <label>Prompt da IA (o que buscar)</label>
            <textarea
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              placeholder="Ex.: Liste nome, preco e link dos 10 produtos em destaque."
              rows={3}
            />
          </div>
        </div>

        <div className="actions">
          <button className="primary" onClick={runScrape} disabled={loading}>
            {loading ? "Executando..." : "Executar scraping"}
          </button>
          <button className="secondary" onClick={loadHistory} type="button">
            Atualizar historico
          </button>
          <button className="secondary" onClick={checkApi} type="button">
            Testar API
          </button>
          <span>{status}</span>
        </div>
      </section>

      <section className="card glass">
        <h2>Resultado</h2>
        {result ? (
          <div className="resultPanel">
            <div className="kpiGrid">
              <article className="kpiCard">
                <span>Status</span>
                <strong className={resultSuccess ? "okText" : "errorText"}>
                  {resultSuccess ? "Sucesso" : "Falha"}
                </strong>
              </article>
              <article className="kpiCard">
                <span>Registro</span>
                <strong>#{String(result.record_id ?? "-")}</strong>
              </article>
              <article className="kpiCard">
                <span>Duração</span>
                <strong>
                  {typeof resultMeta.duration_seconds === "number"
                    ? `${(resultMeta.duration_seconds as number).toFixed(2)}s`
                    : "-"}
                </strong>
              </article>
              <article className="kpiCard">
                <span>Custo</span>
                <strong>
                  {typeof resultMeta.cost_usd === "number"
                    ? `$${(resultMeta.cost_usd as number).toFixed(4)}`
                    : "$0.0000"}
                </strong>
              </article>
              <article className="kpiCard">
                <span>Qualidade</span>
                <strong>
                  {typeof qualityMeta.quality_score === "number"
                    ? `${((qualityMeta.quality_score as number) * 100).toFixed(0)}%`
                    : "-"}
                </strong>
              </article>
              <article className="kpiCard">
                <span>Tokens</span>
                <strong>{String(tokens.total ?? "-")}</strong>
              </article>
            </div>

            {!resultSuccess ? (
              <div className="errorPanel">
                <h3>Falha</h3>
                <p>{String(result.error ?? "Erro desconhecido")}</p>
                <p>
                  Tipo: <strong>{String(resultMeta.error_type ?? "unknown")}</strong>
                </p>
              </div>
            ) : (
              <>
                <article className="summaryBox">
                  <h3>Resumo da IA</h3>
                  <div className="markdown-body">
                    <ReactMarkdown>{resultSummary}</ReactMarkdown>
                  </div>
                </article>
                ) : null}
                {resultFindings.length > 0 ? (
                  <div className="findingList">
                    {resultFindings.map((item, idx) => {
                      const extra = (item.extra as DataMap | undefined) ?? {};
                      return (
                        <article className="findingCard" key={`f-${idx}`}>
                          <h3>{String(item.title ?? `Item ${idx + 1}`)}</h3>
                          {item.description ? <p>{String(item.description)}</p> : null}
                          {item.url ? (
                            <a href={String(item.url)} target="_blank" rel="noreferrer">
                              {String(item.url)}
                            </a>
                          ) : null}
                          {Object.keys(extra).length > 0 ? (
                            <div className="chipWrap">
                              {Object.entries(extra).slice(0, 8).map(([k, v]) => (
                                <span className="chip" key={`${idx}-${k}`}>
                                  {k}: {String(v)}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </article>
                      );
                    })}
                  </div>
                ) : (
                  <p className="hint">Nenhum item estruturado encontrado para exibir.</p>
                )}
              </>
            )}

            <details className="jsonBox">
              <summary>Ver JSON bruto</summary>
              <pre>{prettyResult}</pre>
            </details>
          </div>
        ) : (
          <p className="hint">Execute um scraping para ver o resultado visual aqui.</p>
        )}
      </section>

      <section className="card glass">
        <h2>Historico salvo no SQLite</h2>
        <div className="historyFilters">
          <select
            value={historyStatus}
            onChange={(e) => setHistoryStatus(e.target.value as "all" | "success" | "error")}
          >
            <option value="all">Todos</option>
            <option value="success">Sucesso</option>
            <option value="error">Falha</option>
          </select>
          <input
            value={historyDomain}
            onChange={(e) => setHistoryDomain(e.target.value)}
            placeholder="Filtrar por dominio (ex.: openai.com)"
          />
          <button className="secondary" type="button" onClick={loadHistory}>
            Aplicar filtros
          </button>
        </div>
        {history.length === 0 ? (
          <p className="hint">Clique em "Atualizar historico" para carregar.</p>
        ) : (
          <div className="historyList">
            {history.map((item, idx) => {
              const payload = (item.payload as Record<string, unknown>) || {};
              const success = payload.success === true;
              const meta = (payload.metadata as Record<string, unknown>) || {};
              const urlItem = (item.url as string) || (meta.url as string) || "-";
              const duration = meta.duration_seconds as number | undefined;
              const cost = meta.cost_usd as number | undefined;
              const errorType = (meta.error_type as string | undefined) ?? "none";
              return (
                <article className="historyItem" key={`h-${idx}`}>
                  <strong>{success ? "Sucesso" : "Falha"}</strong>
                  <span>{urlItem}</span>
                  <span>
                    {duration ? `${duration.toFixed(2)}s` : "-"} | ${cost ? cost.toFixed(4) : "0.0000"}
                  </span>
                  <span className="errorBadge">Erro: {errorType}</span>
                  <button
                    className="small"
                    onClick={() => {
                      setResult(payload as ScrapeResponse);
                      setExecutionStage("Histórico Carregado");
                      setStatus(`Visualizando registro #${item.id || "-"}`);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    Visualizar
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
