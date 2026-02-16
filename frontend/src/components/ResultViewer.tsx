import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import ReactJson from "react-json-view";
import { Download, FileJson, FileText, CheckCircle, XCircle, Clock, DollarSign, Activity, Phone, Globe, MapPin, Star, MessageSquare, Tag } from "lucide-react";
import { ScrapeResponse, DataMap } from "../types";
import { Button } from "./ui/Button";
import toast from "react-hot-toast";
import { motion } from "framer-motion";

interface ResultViewerProps {
    result: ScrapeResponse;
}

/**
 * Detects if the result data is from a Google Maps Library extraction
 * by checking the source metadata.
 */
function isMapSource(result: ScrapeResponse): boolean {
    const meta = (result?.metadata as DataMap | undefined) ?? {};
    const source = String(meta.source ?? "");
    return source.includes("library:google_maps");
}

/**
 * Maps-specific lead card with formatted fields
 */
function MapsLeadCard({ item, index }: { item: DataMap; index: number }) {
    const extra = (item.extra as DataMap | undefined) ?? {};
    const phone = extra.phone ?? item.phone ?? null;
    const website = extra.website ?? item.website ?? null;
    const address = extra.address ?? item.address ?? null;
    const rating = extra.rating ?? item.rating ?? null;
    const reviewsCount = extra.reviews_count ?? extra.reviewsCount ?? item.reviews_count ?? null;
    const category = extra.category ?? item.category ?? null;
    const hours = extra.hours ?? item.hours ?? null;
    const priceLevel = extra.price_level ?? extra.priceLevel ?? item.price_level ?? null;

    return (
        <motion.article
            className="card"
            style={{ padding: 'var(--space-6)' }}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
        >
            {/* Header row */}
            <div className="flex items-start justify-between gap-4 mb-4">
                <div style={{ flex: 1, minWidth: 0 }}>
                    <h3 style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-1)' }}>
                        {String(item.title ?? `Lead ${index + 1}`)}
                    </h3>
                    {category && (
                        <span className="flex items-center gap-1 text-xs text-tertiary">
                            <Tag size={12} /> {String(category)}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    {rating != null && (
                        <span className="badge badge-warning" style={{ gap: '4px' }}>
                            <Star size={12} /> {String(rating)}
                        </span>
                    )}
                    {priceLevel && (
                        <span className="badge badge-neutral">
                            {String(priceLevel)}
                        </span>
                    )}
                </div>
            </div>

            {/* Description */}
            {item.description && (
                <p className="text-sm text-secondary" style={{ marginBottom: 'var(--space-4)' }}>
                    {String(item.description)}
                </p>
            )}

            {/* Data grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="flex items-center gap-3" style={{ padding: '10px 14px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)' }}>
                    <Phone size={16} style={{ color: phone ? 'var(--status-success)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                    <div style={{ minWidth: 0 }}>
                        <div className="text-xs text-tertiary font-semibold uppercase tracking-wider">Telefone</div>
                        {phone ? (
                            <a href={`tel:${String(phone)}`} className="text-sm font-medium" style={{ color: 'var(--text-primary)', textDecoration: 'none' }}>
                                {String(phone)}
                            </a>
                        ) : (
                            <span className="text-sm text-tertiary">Não disponível</span>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3" style={{ padding: '10px 14px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)' }}>
                    <Globe size={16} style={{ color: website ? 'var(--primary)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                    <div style={{ minWidth: 0, overflow: 'hidden' }}>
                        <div className="text-xs text-tertiary font-semibold uppercase tracking-wider">Website</div>
                        {website ? (
                            <a href={String(website)} target="_blank" rel="noreferrer" className="text-sm font-medium truncate block" style={{ color: 'var(--primary)' }}>
                                {String(website).replace(/^https?:\/\/(www\.)?/, '').slice(0, 40)}
                            </a>
                        ) : (
                            <span className="text-sm text-tertiary">Não disponível</span>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3" style={{ padding: '10px 14px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)' }}>
                    <MapPin size={16} style={{ color: address ? 'var(--status-warning)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                    <div style={{ minWidth: 0 }}>
                        <div className="text-xs text-tertiary font-semibold uppercase tracking-wider">Endereço</div>
                        <span className={`text-sm ${address ? 'text-primary font-medium' : 'text-tertiary'}`}>
                            {address ? String(address) : 'Não disponível'}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-3" style={{ padding: '10px 14px', background: 'var(--bg-muted)', borderRadius: 'var(--radius-md)' }}>
                    <MessageSquare size={16} style={{ color: reviewsCount ? 'var(--color-indigo-500)' : 'var(--text-tertiary)', flexShrink: 0 }} />
                    <div style={{ minWidth: 0 }}>
                        <div className="text-xs text-tertiary font-semibold uppercase tracking-wider">Avaliações</div>
                        <span className={`text-sm ${reviewsCount ? 'text-primary font-medium' : 'text-tertiary'}`}>
                            {reviewsCount ? `${String(reviewsCount)} avaliações` : 'Não disponível'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Hours */}
            {hours && (
                <div className="flex items-center gap-2 mt-3" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                    <Clock size={12} /> {String(hours)}
                </div>
            )}

            {/* Maps link */}
            {item.url && (
                <div className="mt-3">
                    <a href={String(item.url)} target="_blank" rel="noreferrer" className="text-xs font-medium" style={{ color: 'var(--primary)' }}>
                        Ver no Google Maps →
                    </a>
                </div>
            )}
        </motion.article>
    );
}


export default function ResultViewer({ result }: ResultViewerProps) {
    const resultSuccess = result?.success === true;
    const resultMeta = (result?.metadata as DataMap | undefined) ?? {};
    const resultData = (result?.data as DataMap | undefined) ?? {};
    const resultFindings = Array.isArray(resultData.findings)
        ? (resultData.findings as DataMap[])
        : Array.isArray(resultData.items)
            ? (resultData.items as DataMap[])
            : [];
    const resultSummary = (resultData.summary as string | undefined) ?? "";
    const tokens = (resultMeta.tokens_used as DataMap | undefined) ?? {};
    const isMaps = isMapSource(result);

    const handleDownloadJson = () => {
        const jsonString = JSON.stringify(result, null, 2);
        const blob = new Blob([jsonString], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `scrape_result_${result.id || "data"}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success("JSON baixado!");
    };

    const handleDownloadCsv = () => {
        if (!resultFindings.length) {
            toast.error("Nenhum dado estruturado para exportar em CSV.");
            return;
        }

        // For Maps data, flatten the extra field into top-level columns
        const flatFindings = resultFindings.map(item => {
            const extra = (item.extra as DataMap | undefined) ?? {};
            const flat: Record<string, unknown> = { ...item };
            delete flat.extra;
            // Merge extra fields into top level
            Object.entries(extra).forEach(([k, v]) => {
                if (!(k in flat)) flat[k] = v;
            });
            return flat;
        });

        const keys = new Set<string>();
        flatFindings.forEach(item => {
            Object.keys(item).forEach(k => keys.add(k));
        });
        const headers = Array.from(keys);
        const csvRows = [headers.join(",")];

        flatFindings.forEach(item => {
            const values = headers.map(header => {
                const val = item[header];
                const escaped = String(val ?? "").replace(/"/g, '""');
                return `"${escaped}"`;
            });
            csvRows.push(values.join(","));
        });

        const csvString = csvRows.join("\n");
        const blob = new Blob([csvString], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `scrape_data_${result.id || "data"}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success("CSV baixado!");
    };

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.08 }
        }
    };

    const itemAnim = {
        hidden: { opacity: 0, y: 15 },
        show: { opacity: 1, y: 0 }
    };

    return (
        <div className="resultPanel">
            {/* Header: KPIs + Download Buttons */}
            <div className="result-header">
                <div className="kpiGrid" style={{ flex: 1 }}>
                    <article className="kpiCard">
                        <span className="kpi-label"><Activity size={12} /> Status</span>
                        <strong className={`kpi-value ${resultSuccess ? 'okText' : 'errorText'}`}>
                            {resultSuccess ? <CheckCircle size={18} /> : <XCircle size={18} />}
                            {resultSuccess ? "Sucesso" : "Falha"}
                        </strong>
                    </article>
                    <article className="kpiCard">
                        <span className="kpi-label"><Clock size={12} /> Duração</span>
                        <strong className="kpi-value">
                            {typeof resultMeta.duration_seconds === "number"
                                ? `${(resultMeta.duration_seconds as number).toFixed(2)}s`
                                : "-"}
                        </strong>
                    </article>
                    <article className="kpiCard">
                        <span className="kpi-label"><DollarSign size={12} /> Custo</span>
                        <strong className="kpi-value">
                            {typeof resultMeta.cost_usd === "number"
                                ? `$${(resultMeta.cost_usd as number).toFixed(4)}`
                                : "$0.0000"}
                        </strong>
                    </article>
                    {isMaps && resultFindings.length > 0 && (
                        <article className="kpiCard">
                            <span className="kpi-label"><MapPin size={12} /> Leads</span>
                            <strong className="kpi-value">{resultFindings.length}</strong>
                        </article>
                    )}
                </div>
                <div className="result-actions">
                    <Button variant="secondary" size="sm" onClick={handleDownloadJson} aria-label="Baixar JSON">
                        <FileJson size={14} /> JSON
                    </Button>
                    <Button variant="secondary" size="sm" onClick={handleDownloadCsv} aria-label="Baixar CSV">
                        <FileText size={14} /> CSV
                    </Button>
                </div>
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
                    {resultSummary ? (
                        <article className="summaryBox">
                            <h3>Resumo da IA</h3>
                            <div className="markdown-body">
                                <ReactMarkdown>{resultSummary}</ReactMarkdown>
                            </div>
                        </article>
                    ) : null}

                    {resultFindings.length > 0 ? (
                        isMaps ? (
                            /* MAPS-SPECIFIC: Rendered lead cards with all fields */
                            <div className="space-y-4">
                                {resultFindings.map((item, idx) => (
                                    <MapsLeadCard key={`lead-${idx}`} item={item} index={idx} />
                                ))}
                            </div>
                        ) : (
                            /* GENERIC: Standard findings list */
                            <motion.div
                                className="findingList"
                                variants={container}
                                initial="hidden"
                                animate="show"
                            >
                                {resultFindings.map((item, idx) => {
                                    const extra = (item.extra as DataMap | undefined) ?? {};
                                    return (
                                        <motion.article
                                            className="findingCard"
                                            key={`f-${idx}`}
                                            variants={itemAnim}
                                        >
                                            <h3>{String(item.title ?? `Item ${idx + 1}`)}</h3>
                                            {item.description ? <p>{String(item.description)}</p> : null}
                                            {item.url ? (
                                                <a href={String(item.url)} target="_blank" rel="noreferrer">
                                                    {String(item.url)}
                                                </a>
                                            ) : null}
                                            {Object.keys(extra).length > 0 ? (
                                                <div className="chipWrap" style={{ marginTop: 'var(--space-3)' }}>
                                                    {Object.entries(extra).slice(0, 8).map(([k, v]) => (
                                                        <span className="chip" key={`${idx}-${k}`}>
                                                            {k}: {String(v)}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : null}
                                        </motion.article>
                                    );
                                })}
                            </motion.div>
                        )
                    ) : (
                        <p className="hint">Nenhum item estruturado encontrado para exibir.</p>
                    )}
                </>
            )}

            <div className="jsonBox">
                <h3>JSON Bruto</h3>
                <ReactJson
                    src={result}
                    theme="ocean"
                    displayDataTypes={false}
                    collapsed={1}
                    enableClipboard={true}
                    style={{ backgroundColor: 'transparent', fontSize: '13px' }}
                />
            </div>
        </div>
    );
}
