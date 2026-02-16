import { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { API_BASE, EXECUTION_STAGES, ScrapeResponse } from "../types";
import ResultViewer from "../components/ResultViewer";
import { SkeletonCard } from "../components/Skeleton";
import { Input, Textarea } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import toast from "react-hot-toast";
import { Terminal, Rocket, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// URL validation regex
const URL_REGEX = /^https?:\/\/([\w-]+\.)+[\w-]+(\/[\w\-._~:/?#[\]@!$&'()*+,;=%]*)?$/i;

export default function Scraper() {
    const [url, setUrl] = useState("");
    const [userPrompt, setUserPrompt] = useState(
        "Busque os dados mais relevantes desta pagina e retorne itens estruturados.",
    );
    const [loading, setLoading] = useState(false);
    const [executionStage, setExecutionStage] = useState<string>("Pronto");
    const [result, setResult] = useState<ScrapeResponse | null>(null);
    const [apiHealth, setApiHealth] = useState<"checking" | "ok" | "down">("checking");
    const [outputFormat, setOutputFormat] = useState("list");
    const [systemPrompt, setSystemPrompt] = useState("generic");

    const [source, setSource] = useState("scraper_manual");
    const [logs, setLogs] = useState<string[]>([]);
    const logsEndRef = useRef<HTMLDivElement>(null);

    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
        if (location.state) {
            const { url: stateUrl, prompt: statePrompt, userPrompt: stateUserPrompt, source: stateSource, autoRun } = location.state as any;
            if (stateUrl) setUrl(stateUrl);
            if (statePrompt) setSystemPrompt(statePrompt);
            if (stateUserPrompt) setUserPrompt(stateUserPrompt);
            if (stateSource) setSource(stateSource);

            if (autoRun) {
                setTimeout(() => {
                    void runScrape(stateUrl, statePrompt, stateUserPrompt, stateSource);
                }, 500);
            }

            window.history.replaceState({}, document.title);
        }
    }, [location]);



    useEffect(() => {
        if (!url) return;
        const lowerUrl = url.toLowerCase();

        // Auto-detect site type for prompt selection
        if (lowerUrl.includes("amazon") || lowerUrl.includes("mercadolivre") || lowerUrl.includes("shop") || lowerUrl.includes("store")) {
            setSystemPrompt("ecommerce");
            toast("Modo E-commerce ativado", { icon: '🛍️', duration: 2000 });
        } else if (lowerUrl.includes("news") || lowerUrl.includes("g1") || lowerUrl.includes("cnn") || lowerUrl.includes("bbc")) {
            setSystemPrompt("news");
            toast("Modo Notícias ativado", { icon: '📰', duration: 2000 });
        }
    }, [url]);

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
    }, []);

    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs]);

    const addLog = (msg: string) => {
        setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
    };

    useEffect(() => {
        if (!loading) return;
        let idx = 0;
        const timer = setInterval(() => {
            idx = (idx + 1) % EXECUTION_STAGES.length;
            setExecutionStage(EXECUTION_STAGES[idx]);
            addLog(`Executando: ${EXECUTION_STAGES[idx]}...`);
        }, 2500);
        return () => clearInterval(timer);
    }, [loading]);

    async function runScrape(
        overrideUrl?: string,
        overrideSystemPrompt?: string,
        overrideUserPrompt?: string,
        overrideSource?: string
    ) {
        const targetUrl = overrideUrl || url;
        const targetSystemPrompt = overrideSystemPrompt || systemPrompt;
        const targetUserPrompt = overrideUserPrompt || userPrompt;
        const targetSource = overrideSource || source;

        if (!targetUrl.trim()) {
            toast.error("Por favor, informe uma URL válida.");
            return;
        }

        // URL format validation
        if (!URL_REGEX.test(targetUrl.trim())) {
            toast.error("URL inválida. Use o formato: https://example.com");
            return;
        }

        setLoading(true);
        setLogs([]);
        addLog(`Iniciando tarefa para: ${targetUrl}`);
        addLog(`Prompt do Sistema: ${targetSystemPrompt}`);

        const toastId = toast.loading("Iniciando scraping...");
        setExecutionStage(EXECUTION_STAGES[0]);
        setResult(null);

        try {
            addLog("Conectando ao backend...");
            const endpoint = "/api/scrape";
            const apiKey = localStorage.getItem("toolzz_openai_key") || undefined;

            const response = await fetch(`${API_BASE}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: targetUrl.trim(),
                    schema: "guided_extract",
                    prompt: targetSystemPrompt,
                    user_prompt: targetUserPrompt,
                    wait_until: "networkidle",
                    timeout: 30000,
                    screenshot_quality: 70,
                    full_page: false,
                    auto_scroll: true,
                    scroll_steps: 6,
                    output_format: outputFormat,
                    api_key: apiKey,
                    source: targetSource,
                }),
            });

            addLog("Resposta recebida. Processando dados...");
            const data = (await response.json()) as ScrapeResponse;
            setResult(data);

            if (data.success) {
                toast.success(`Scraping concluído!`, { id: toastId });
                setExecutionStage("Concluído");
                addLog("Sucesso! Dados extraídos.");
                addLog(`Tokens usados: ${data.metadata?.tokens_used?.total || 0}`);
            } else {
                toast.error(`Falha no scraping: ${data.error || "Erro desconhecido"}`, { id: toastId });
                setExecutionStage("Falha");
                addLog(`Erro: ${data.error}`);
            }

        } catch (error) {
            setResult({
                success: false,
                error: `Falha de conexão com API: ${String(error)}`,
            });
            toast.error("Erro de conexão com o servidor.", { id: toastId });
            setExecutionStage("Falha");
            addLog(`Erro Crítico: ${String(error)}`);
        } finally {
            setLoading(false);
            addLog("Processo finalizado.");
        }
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <header className="hero" style={{ marginTop: 0 }}>
                <p>Scraping inteligente com URL + instrução para IA.</p>
                <div className={`apiStatus ${apiHealth}`}>
                    API: {apiHealth === "ok" ? "conectada" : apiHealth === "down" ? "inacessível" : "checando..."}
                </div>
            </header>

            <motion.section
                className="card"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.1 }}
            >
                <div className="sectionTitle">
                    <h2>Novo scraping</h2>
                </div>

                <div className="layout-grid">
                    <div className="full">
                        <Input
                            label="URL Alvo"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://example.com"
                            type="url"
                        />
                    </div>

                    <div>
                        <Select
                            label="Formato de Saída"
                            value={outputFormat}
                            onChange={(e) => setOutputFormat(e.target.value)}
                            options={[
                                { value: "list", label: "Lista (Padrão)" },
                                { value: "summary", label: "Resumo" },
                                { value: "report", label: "Relatório Completo" },
                            ]}
                        />
                    </div>



                    <div className="full">
                        <Textarea
                            label="Instrução para a IA"
                            value={userPrompt}
                            onChange={(e) => setUserPrompt(e.target.value)}
                            placeholder="Ex.: Liste nome, preço e link dos 10 produtos em destaque."
                            rows={3}
                        />
                    </div>
                </div>

                <div className="actions">
                    <Button
                        variant="primary"
                        size="lg"
                        onClick={() => runScrape()}
                        disabled={loading}
                        loading={loading}
                    >
                        {loading ? "Processando..." : (
                            <>
                                <Rocket size={18} /> Executar Scraping
                            </>
                        )}
                    </Button>
                </div>

                <AnimatePresence>
                    {(loading || logs.length > 0) && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="terminal-panel animate-pulse-border"
                            role="log"
                            aria-label="Terminal de execução"
                            aria-live="polite"
                        >
                            <div className="terminal-header">
                                <Terminal size={14} />
                                <span>Terminal de Execução</span>
                                {executionStage && <span className="terminal-stage">{executionStage}</span>}
                            </div>
                            <div className="terminal-logs">
                                {logs.map((log, i) => (
                                    <div key={i} className="log-entry">{log}</div>
                                ))}
                                <div ref={logsEndRef} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.section>

            {/* Only show result section when there's data */}
            <AnimatePresence>
                {(loading || result) && (
                    <motion.section
                        className="card"
                        style={{ marginTop: 'var(--space-6)' }}
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.4, delay: 0.2 }}
                    >
                        <h2 style={{ marginBottom: 'var(--space-4)' }}>Resultado</h2>
                        {loading ? (
                            <SkeletonCard />
                        ) : result ? (
                            <ResultViewer result={result} />
                        ) : null}
                    </motion.section>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
