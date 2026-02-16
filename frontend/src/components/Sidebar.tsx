import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Search, History, Settings, Library, Menu, X } from "lucide-react";
import { useState, useEffect } from "react";

interface SidebarProps {
    isOpen: boolean;
    onToggle: () => void;
}

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
    const location = useLocation();
    const path = location.pathname;

    // Close sidebar on mobile when navigating
    useEffect(() => {
        if (window.innerWidth < 768) {
            onToggle();
        }
    }, [path]);

    const navItems = [
        { to: "/", icon: <LayoutDashboard size={20} />, label: "Dashboard" },
        { to: "/scrape", icon: <Search size={20} />, label: "Scraping" },
        { to: "/library", icon: <Library size={20} />, label: "Biblioteca" },
        { to: "/history", icon: <History size={20} />, label: "Histórico" },
        { to: "/settings", icon: <Settings size={20} />, label: "Configurações" },
    ];

    return (
        <>
            {/* Mobile hamburger */}
            <button
                className="sidebar-toggle"
                onClick={onToggle}
                aria-label={isOpen ? "Fechar menu" : "Abrir menu"}
            >
                {isOpen ? <X size={22} /> : <Menu size={22} />}
            </button>

            {/* Overlay for mobile */}
            {isOpen && (
                <div
                    className="sidebar-overlay"
                    onClick={onToggle}
                    aria-hidden="true"
                />
            )}

            <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
                <div className="sidebarHeader">
                    <img
                        src="https://www.toolzz.com.br/logotoolzz.svg"
                        alt="Toolzz Search"
                        className="sidebarLogo"
                    />
                </div>

                <nav className="sidebarNav" role="navigation" aria-label="Menu principal">
                    {navItems.map((item) => (
                        <Link
                            key={item.to}
                            to={item.to}
                            className={`navItem ${path === item.to ? "active" : ""}`}
                            aria-current={path === item.to ? "page" : undefined}
                        >
                            <span className="icon" aria-hidden="true">{item.icon}</span>
                            <span className="label">{item.label}</span>
                        </Link>
                    ))}
                </nav>

                <div className="sidebarFooter">
                    <p>Toolzz Search v1.0</p>
                </div>
            </aside>
        </>
    );
}
