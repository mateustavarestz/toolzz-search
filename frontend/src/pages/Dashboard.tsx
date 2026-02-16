import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Activity,
    Search,
    Clock,
    ArrowRight,
    MapPin,
    Terminal,
    History,
    Settings,
    CheckCircle,
    XCircle,
    Calendar // Added Calendar import
} from "lucide-react";
import { motion } from "framer-motion";
import { API_BASE, ScrapeResponse } from "../types";
import { SkeletonCard } from "../components/Skeleton";

export default function Dashboard() {
    const navigate = useNavigate();
    const [stats, setStats] = useState({
        total: 0,
        successRate: 0,
        avgDuration: 0,
        totalLeads: 0
    });
    const [recentItems, setRecentItems] = useState<ScrapeResponse[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            try {
                const response = await fetch(`${API_BASE}/api/history?limit=100`);
                const data = await response.json();
                const items = data.items || [];

                setRecentItems(items.slice(0, 5));

                // Calculate stats
                const total = items.length;
                const successCount = items.filter((i: any) => i.payload?.success).length;
                const successRate = total > 0 ? (successCount / total) * 100 : 0;

                const durations = items
                    .map((i: any) => i.payload?.metadata?.duration_seconds)
                    .filter((d: any) => typeof d === 'number');
                const avgDuration = durations.length > 0
                    ? durations.reduce((a: any, b: any) => a + b, 0) / durations.length
                    : 0;

                setStats({
                    total,
                    successRate,
                    avgDuration,
                    totalLeads: 0 // Placeholder as we don't strictly track leads count in list yet
                });
            } catch (error) {
                console.error("Failed to load dashboard data", error);
            } finally {
                setLoading(false);
            }
        }
        void loadData();
    }, []);

    const quickAccess = [
        {
            title: "Templates",
            desc: "Extratores prontos (Maps, Search)",
            icon: <MapPin size={24} />,
            color: "var(--color-blue-500)",
            bg: "var(--color-blue-50)",
            path: "/library"
        },
        {
            title: "Scraper Manual",
            desc: "Expert Mode: URL + Prompt",
            icon: <Terminal size={24} />,
            color: "var(--color-violet-500)",
            bg: "var(--color-violet-50)",
            path: "/scrape"
        },
        {
            title: "Histórico",
            desc: "Ver todos os resultados",
            icon: <History size={24} />,
            color: "var(--color-emerald-500)",
            bg: "var(--color-emerald-50)",
            path: "/history"
        },
        {
            title: "Configurações",
            desc: "Chaves de API e preferências",
            icon: <Settings size={24} />,
            color: "var(--color-slate-500)",
            bg: "var(--color-slate-100)",
            path: "/settings"
        }
    ];

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <header className="mb-8">
                <h1>Visão Geral</h1>
                <p>Acompanhe suas métricas e acesse rapidamente suas ferramentas.</p>
            </header>

            {/* Quick Access Grid */}
            <section className="mb-8">
                <h3 className="section-label mb-4">Acesso Rápido</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {quickAccess.map((item, idx) => (
                        <div
                            key={idx}
                            className="card card-hover clickable"
                            onClick={() => navigate(item.path)}
                            style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', padding: 'var(--space-5)' }}
                        >
                            <div className="icon-box icon-box-lg" style={{ color: item.color, backgroundColor: item.bg }}>
                                {item.icon}
                            </div>
                            <div>
                                <h4 style={{ fontSize: 'var(--text-base)', marginBottom: '2px' }}>{item.title}</h4>
                                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', margin: 0 }}>{item.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Stats Grid */}
            <section className="mb-8">
                <h3 className="section-label mb-4">Performance (Últimos 100)</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="card stat-card">
                        <div className="stat-header">
                            <div>
                                <p className="stat-label">Total de Execuções</p>
                                <div className="stat-value">{loading ? "-" : stats.total}</div>
                            </div>
                            <div className="icon-box icon-box-md icon-box-blue rounded-xl">
                                <Search size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="card stat-card">
                        <div className="stat-header">
                            <div>
                                <p className="stat-label">Taxa de Sucesso</p>
                                <div className="stat-value">{loading ? "-" : `${stats.successRate.toFixed(1)}%`}</div>
                            </div>
                            <div className="icon-box icon-box-md icon-box-emerald rounded-xl">
                                <Activity size={20} />
                            </div>
                        </div>
                    </div>

                    <div className="card stat-card">
                        <div className="stat-header">
                            <div>
                                <p className="stat-label">Tempo Médio</p>
                                <div className="stat-value">{loading ? "-" : `${stats.avgDuration.toFixed(1)}s`}</div>
                            </div>
                            <div className="icon-box icon-box-md icon-box-indigo rounded-xl">
                                <Clock size={20} />
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Recent Activity */}
            <section>
                <div className="flex items-center justify-between mb-4">
                    <h3 className="section-label mb-0">Atividade Recente</h3>
                    <button
                        className="btn btn-ghost btn-sm text-primary"
                        onClick={() => navigate('/history')}
                    >
                        Ver tudo <ArrowRight size={16} />
                    </button>
                </div>

                <div className="card p-0 overflow-hidden">
                    {loading ? (
                        <div className="p-4 space-y-4">
                            <SkeletonCard />
                            <SkeletonCard />
                        </div>
                    ) : recentItems.length === 0 ? (
                        <div className="emptyState p-8">
                            <History size={32} />
                            <p>Nenhuma atividade recente encontrada.</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-100 dark:divide-gray-800">
                            {recentItems.map((item, i) => {
                                const success = item.payload?.success;
                                const url = item.payload?.metadata?.url || item.url || "URL desconhecida";
                                const date = item.timestamp ? new Date(item.timestamp).toLocaleDateString() : "-";
                                const source = item.payload?.metadata?.source || "manual";

                                return (
                                    <div
                                        key={i}
                                        className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                                        onClick={() => navigate('/history')}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className={`p-2 rounded-full ${success ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                                {success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                                            </div>
                                            <div>
                                                <p className="font-medium text-sm text-primary truncate max-w-[300px]" title={url as string}>
                                                    {url as string}
                                                </p>
                                                <p className="text-xs text-secondary flex items-center gap-2">
                                                    <span className="capitalize">{source as string}</span>
                                                    <span>•</span>
                                                    <span>{date}</span>
                                                </p>
                                            </div>
                                        </div>
                                        <ArrowRight size={14} className="text-tertiary" />
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </section>
        </motion.div>
    );
}

