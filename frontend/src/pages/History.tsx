import { useEffect, useState, useCallback } from "react";
import { API_BASE, ScrapeResponse } from "../types";
import ResultViewer from "../components/ResultViewer";
import { SkeletonCard } from "../components/Skeleton";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import "../history.css";
import toast from "react-hot-toast";
import { MapPin, Search, ChevronRight, ChevronDown, CheckCircle, XCircle, RefreshCw } from "lucide-react";


interface HistoryItemProps {
    item: ScrapeResponse;
}

function HistoryItem({ item }: HistoryItemProps) {
    const [expanded, setExpanded] = useState(false);
    const payload = (item.payload as Record<string, unknown>) || {};
    const success = payload.success === true;
    const meta = (payload.metadata as Record<string, unknown>) || {};
    const urlItem = (item.url as string) || (meta.url as string) || "-";

    const duration = typeof meta.duration_seconds === 'number'
        ? `${meta.duration_seconds.toFixed(2)}s`
        : "-";

    const recordId = item.id || payload.record_id || "-";
    const shortId = String(recordId).substring(0, 8);

    const source = (meta.source as string) || "scraper_manual";
    const isLibrary = source.includes("library");

    return (
        <article className={`historyRow ${expanded ? "expanded" : ""}`}>
            <div
                className="historyRowMain"
                onClick={() => setExpanded(!expanded)}
                role="button"
                tabIndex={0}
                aria-expanded={expanded}
                onKeyDown={(e) => e.key === 'Enter' && setExpanded(!expanded)}
            >
                {/* Expander Column */}
                <div className="col-expander" aria-hidden="true">
                    {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>

                {/* Main Content Column */}
                <div className="col-main">
                    <div className={`rowIcon ${isLibrary ? 'library' : 'manual'}`}>
                        {isLibrary ? <MapPin size={18} /> : <Search size={18} />}
                    </div>
                    <div className="rowText">
                        <strong className="rowTitle" title={String(urlItem)}>{String(urlItem)}</strong>
                        <span className="rowSubtitle">{isLibrary ? "Templates" : "Manual"}</span>
                    </div>
                </div>

                {/* Status Column */}
                <div className="col-status">
                    {success ? (
                        <span className="statusIcon success" title="Sucesso">
                            <CheckCircle size={18} />
                        </span>
                    ) : (
                        <span className="statusIcon error" title="Falha">
                            <XCircle size={18} />
                        </span>
                    )}
                </div>

                {/* Meta Columns */}
                <div className="col-meta font-mono text-secondary text-sm">
                    {duration}
                </div>
                <div className="col-meta font-mono text-tertiary text-xs">
                    #{shortId}
                </div>
            </div>

            {expanded && (
                <div className="historyRowDetails">
                    <div className="p-4">
                        <ResultViewer result={payload as ScrapeResponse} />
                    </div>
                </div>
            )}
        </article>
    );
}

export default function History() {
    const [history, setHistory] = useState<ScrapeResponse[]>([]);
    const [historyStatus, setHistoryStatus] = useState<"all" | "success" | "error">("all");
    const [historyDomain, setHistoryDomain] = useState("");
    const [loading, setLoading] = useState(false);

    const loadHistory = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            params.set("limit", "50");
            if (historyStatus === "success") params.set("success", "true");
            if (historyStatus === "error") params.set("success", "false");
            if (historyDomain.trim()) params.set("domain", historyDomain.trim());

            const response = await fetch(`${API_BASE}/api/history?${params.toString()}`);
            const data = (await response.json()) as { items?: ScrapeResponse[] };
            setHistory(data.items ?? []);

        } catch (_error) {
            toast.error("Não foi possível carregar o histórico.");
        } finally {
            setLoading(false);
        }
    }, [historyStatus, historyDomain]);

    useEffect(() => {
        void loadHistory();
    }, []);

    // Debounce: auto-reload when filters change
    useEffect(() => {
        const timer = setTimeout(() => {
            void loadHistory();
        }, 500);
        return () => clearTimeout(timer);
    }, [historyStatus, historyDomain, loadHistory]);

    return (
        <section className="card">
            <div className="sectionTitle">
                <h2>Histórico de Scraping</h2>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={loadHistory}
                    disabled={loading}
                    loading={loading}
                >
                    <RefreshCw size={14} /> Atualizar
                </Button>
            </div>

            {/* Filters */}
            <div className="historyFilters">
                <div className="filterGroup">
                    <Select
                        label="Status"
                        value={historyStatus}
                        onChange={(e) => setHistoryStatus(e.target.value as "all" | "success" | "error")}
                        options={[
                            { value: "all", label: "Todas" },
                            { value: "success", label: "Sucesso" },
                            { value: "error", label: "Falha" },
                        ]}
                    />
                </div>

                <div className="filterGroup full">
                    <label htmlFor="history-domain-search">Buscar Domínio</label>
                    <div className="input-with-icon">
                        <span className="input-icon"><Search size={18} /></span>
                        <input
                            id="history-domain-search"
                            value={historyDomain}
                            onChange={(e) => setHistoryDomain(e.target.value)}
                            placeholder="Ex: google.com"
                            style={{ paddingLeft: '44px' }}
                        />
                    </div>
                </div>
            </div>

            {loading ? (
                <div className="space-y-4" style={{ paddingTop: 'var(--space-4)' }}>
                    <SkeletonCard />
                    <SkeletonCard />
                    <SkeletonCard />
                </div>
            ) : history.length === 0 ? (
                <div className="emptyState">
                    <Search size={40} />
                    <p>Nenhum registro encontrado no histórico.</p>
                </div>
            ) : (
                <div className="historyTableContainer">
                    <div className="historyTableHeader">
                        <div className="col-expander"></div>
                        <div className="col-main">Domínio / Tarefa</div>
                        <div className="col-status">Status</div>
                        <div className="col-meta">Duração</div>
                        <div className="col-meta">Data/ID</div>
                    </div>

                    <div className="historyList">
                        {history.map((item, idx) => (
                            <HistoryItem key={idx} item={item} />
                        ))}
                    </div>
                </div>
            )}
        </section>
    );
}
