import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { Key, Save, CheckCircle } from "lucide-react";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { motion } from "framer-motion";

export default function Settings() {
    const [apiKey, setApiKey] = useState("");
    const [saved, setSaved] = useState(true);

    useEffect(() => {
        const key = localStorage.getItem("toolzz_openai_key");
        if (key) setApiKey(key);
    }, []);

    const handleSaveApiKey = () => {
        localStorage.setItem("toolzz_openai_key", apiKey.trim());
        toast.success("Chave de API salva com sucesso!");
        setSaved(true);
    };

    const handleChange = (value: string) => {
        setApiKey(value);
        setSaved(false);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{ maxWidth: '42rem', margin: '0 auto' }}
        >
            <header className="page-header select-none">
                <h1>Configurações</h1>
                <p>Gerencie suas credenciais de acesso.</p>
            </header>

            <section className="card">
                <div className="flex items-center gap-4 mb-6">
                    <div className="icon-box icon-box-lg icon-box-blue rounded-xl">
                        <Key size={22} />
                    </div>
                    <div>
                        <h2 style={{ fontSize: 'var(--text-xl)' }}>Chave de API</h2>
                        <p className="text-sm text-secondary" style={{ margin: 0 }}>Conexão com OpenAI (GPT-4o/Mini)</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <Input
                        label="OpenAI API Key"
                        type="password"
                        value={apiKey}
                        onChange={(e) => handleChange(e.target.value)}
                        placeholder="sk-..."
                        hint="Sua chave é armazenada localmente no navegador por segurança. Se definida aqui, ela terá prioridade sobre a configuração do servidor."
                        style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}
                    />

                    <div className="flex justify-end items-center gap-3" style={{ paddingTop: 'var(--space-4)' }}>
                        {saved && apiKey && (
                            <span className="flex items-center gap-1 text-sm text-success font-medium">
                                <CheckCircle size={14} /> Salvo
                            </span>
                        )}
                        <Button
                            variant="dark"
                            onClick={handleSaveApiKey}
                            disabled={saved}
                        >
                            <Save size={16} /> Salvar Alterações
                        </Button>
                    </div>
                </div>
            </section>
        </motion.div>
    );
}
