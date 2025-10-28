import React from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";

const Navigation: React.FC = () => {
  const location = useLocation();

  const navLinks = [
    { path: "/chat", label: "Chat Studente" },
    { path: "/admin/dashboard", label: "Dashboard Admin" },
    { path: "/login", label: "Admin Login" },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="border-b bg-background">
      <div className="mx-auto max-w-7xl px-8">
        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center justify-around h-24">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              className={cn(
                "px-8 py-4 rounded-md text-xl font-bold transition-colors",
                isActive(link.path)
                  ? "bg-accent text-accent-foreground"
                  : "text-foreground/60 hover:text-foreground hover:bg-accent/50"
              )}
              aria-current={isActive(link.path) ? "page" : undefined}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Mobile Navigation - Simplified */}
        <div className="md:hidden flex items-center justify-between h-20">
          <span className="font-semibold text-lg">
            {navLinks.find((l) => isActive(l.path))?.label || "FisioRAG"}
          </span>
          {/* Mobile menu: Può essere esteso con Sheet component se necessario */}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
