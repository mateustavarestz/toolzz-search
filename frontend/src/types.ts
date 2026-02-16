export type ScrapeResponse = Record<string, unknown>;
export type DataMap = Record<string, unknown>;

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export const EXECUTION_STAGES = [
    "Preparando requisicao",
    "Navegando no site",
    "Capturando conteudo",
    "Processando com IA",
    "Validando e persistindo",
];

export const PROMPT_TEMPLATES: Record<string, string> = {
    products: "Liste os 10 principais produtos com nome, preco, disponibilidade e URL.",
    article:
        "Extraia titulo, autor, data e os principais pontos do conteudo em itens objetivos.",
    contacts: "Extraia contatos visiveis (email, telefone, formulario, redes sociais) com links.",
    offers: "Capture ofertas em destaque com titulo, preco, desconto e validade quando existir.",
    custom: "Busque os dados mais relevantes desta pagina e retorne itens estruturados.",
};
