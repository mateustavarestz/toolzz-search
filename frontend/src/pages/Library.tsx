import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { MapPin, Search, ArrowRight, X, Settings2, LayoutTemplate } from "lucide-react";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { motion, AnimatePresence } from "framer-motion";

export default function Library() {
    const navigate = useNavigate();
    const [selectedTool, setSelectedTool] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");

    const [loading, setLoading] = useState(false);

    const tools = [
        {
            id: "google_maps",
            category: "Negócios Locais",
            title: "Google Maps Leads",
            description: "Extraia dados completos (nome, telefone, endereço, site, avaliações) de empresas no Google Maps.",
            icon: <MapPin size={28} />,
            iconClass: "icon-box-red",
            disabled: false,
        },
        {
            id: "google_search",
            category: "Web Geral",
            title: "Google Search (SERP)",
            description: "Monitore resultados de busca, extraia títulos, descrições e links para palavras-chave.",
            icon: <Search size={28} />,
            iconClass: "icon-box-blue",
            disabled: true,
            badge: "Em Breve"
        },
        {
            id: "linkedin_profile",
            category: "Profissional",
            title: "LinkedIn Profiles",
            description: "Enriqueça dados de leads com informações públicas de perfis do LinkedIn.",
            icon: <LayoutTemplate size={28} />,
            iconClass: "icon-box-indigo",
            disabled: true,
            badge: "Em Breve"
        }
    ];

    const handleToolClick = (toolId: string) => {
        if (toolId === "google_maps") {
            setSelectedTool(toolId);
            setSearchTerm("");
            setSearchTerm("");
        }
    };

    const runMapsScraper = async () => {
        if (!searchTerm.trim()) {
            toast.error("Por favor, preencha o termo de busca.");
            return;
        }

        setLoading(true);
        const toastId = toast.loading("Configurando extrator...");

        try {
            const query = encodeURIComponent(searchTerm.trim());
            const mapsUrl = `https://www.google.com/maps/search/${query}`;

            const limitInstruction = "Limitar a aproximadamente 100 resultados.";
            const finalUserPrompt = `Extraia leads de TODAS as empresas visiveis na busca por '${searchTerm}'. ${limitInstruction}
Para CADA empresa, use o campo 'title' para o nome e preencha o campo 'extra' com: phone (telefone), website (URL do site), address (endereço completo), rating (nota), reviews_count (total de avaliações), category (categoria do negócio), hours (horário) e price_level (nível de preço).
Se um campo não estiver visível, use null. NÃO invente dados.`;

            navigate("/scrape", {
                state: {
                    autoRun: true,
                    url: mapsUrl,
                    prompt: "google_maps_leads",
                    source: "library:google_maps",
                    userPrompt: finalUserPrompt,
                }
            });

            toast.dismiss(toastId);
        } catch (error) {
            console.error(error);
            toast.error("Erro ao iniciar.", { id: toastId });
            setLoading(false);
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <div className="page-header">
                <h1>Templates de Extratores</h1>
                <p>
                    Escolha um extrator especializado para iniciar sua coleta de dados.
                    Nossas ferramentas já vêm configuradas com as melhores estratégias.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {tools.map((tool) => (
                    <motion.div
                        key={tool.id}
                        whileHover={!tool.disabled ? { y: -4 } : {}}
                        onClick={() => !tool.disabled && handleToolClick(tool.id)}
                        className={`tool-card ${tool.disabled ? 'tool-card-disabled' : ''}`}
                    >
                        {tool.badge && (
                            <span className="tool-badge badge badge-neutral">
                                {tool.badge}
                            </span>
                        )}

                        <div className={`icon-box icon-box-xl ${tool.iconClass} tool-icon`}>
                            {tool.icon}
                        </div>

                        <div className="mb-4">
                            <span className="tool-category">{tool.category}</span>
                            <h3 className="tool-title">{tool.title}</h3>
                            <p className="tool-description">{tool.description}</p>
                        </div>

                        {!tool.disabled && (
                            <div className="tool-cta">
                                CONFIGURAR EXTRATOR <ArrowRight size={16} />
                            </div>
                        )}
                    </motion.div>
                ))}
            </div>

            {/* Modal for Google Maps */}
            <AnimatePresence>
                {selectedTool === "google_maps" && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedTool(null)}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Configurar Google Maps Lead Extractor"
                    >
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 10 }}
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                        >
                            {/* Header */}
                            <div className="modal-header">
                                <button
                                    onClick={() => setSelectedTool(null)}
                                    className="modal-close"
                                    aria-label="Fechar modal"
                                >
                                    <X size={20} />
                                </button>
                                <div className="flex items-center gap-4">
                                    <div className="icon-box icon-box-lg icon-box-red">
                                        <MapPin size={24} />
                                    </div>
                                    <div>
                                        <h3>Google Maps Lead Extractor</h3>
                                        <p className="text-sm text-secondary" style={{ margin: 0 }}>Configure os parâmetros da sua busca.</p>
                                    </div>
                                </div>
                            </div>

                            {/* Body */}
                            <div className="modal-body space-y-6">
                                <div>
                                    <div className="input-with-icon">
                                        <span className="input-icon"><Search size={20} /></span>
                                        <input
                                            type="text"
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            placeholder="Ex: Restaurantes Italianos em Moema, SP"
                                            autoFocus
                                            onKeyDown={(e) => e.key === "Enter" && runMapsScraper()}
                                            id="maps-search-term"
                                            style={{ fontSize: 'var(--text-lg)', padding: '14px 14px 14px 44px' }}
                                        />
                                    </div>
                                    <label htmlFor="maps-search-term" style={{ marginTop: 'var(--space-2)', marginBottom: 0 }}>
                                        Termo de Busca e Localização
                                    </label>
                                    <p className="form-hint mt-2">
                                        <Settings2 size={12} /> Dica: Seja específico com o local para melhores resultados.
                                    </p>
                                </div>


                            </div>

                            {/* Footer */}
                            <div className="modal-footer">
                                <Button
                                    variant="ghost"
                                    onClick={() => setSelectedTool(null)}
                                >
                                    Cancelar
                                </Button>
                                <Button
                                    variant="primary"
                                    size="lg"
                                    onClick={runMapsScraper}
                                    disabled={loading}
                                    loading={loading}
                                >
                                    {loading ? "Iniciando..." : (
                                        <>Iniciar Extração <ArrowRight size={18} /></>
                                    )}
                                </Button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
