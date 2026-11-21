import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { GithubIcon } from "./Icons";
import {
  Sparkles,
  LayoutDashboard,
  Receipt,
  PieChart,
  Bot,
  BarChart3,
  BookOpen,
  LogIn,
  LogOut,
  Menu,
  X,
  User,
  ShieldCheck,
} from "lucide-react";

export default function Navbar({ onOpenAuthModal }) {
  const { user, isAuthenticated, logout, quickDemoLogin } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Transactions", path: "/transactions", icon: Receipt },
    { name: "Budgets & Goals", path: "/budgets", icon: PieChart },
    { name: "AI Assistant", path: "/assistant", icon: Bot, highlight: true },
    { name: "Analytics", path: "/analytics", icon: BarChart3 },
    { name: "Theory & Architecture", path: "/about", icon: BookOpen },
  ];

  const isActive = (path) => {
    if (path === "/" && location.pathname === "/") return true;
    if (path !== "/" && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200/80 bg-white/90 backdrop-blur-md transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight text-gray-900 group-hover:text-blue-600 transition-colors">
                Finance<span className="text-blue-600">Agent</span>
              </span>
              <span className="text-[10px] font-medium text-emerald-600 flex items-center gap-1 -mt-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                Vector AI Active
              </span>
            </div>
          </Link>

          {/* Desktop Nav Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => {
              const active = isActive(link.path);
              const Icon = link.icon;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    active
                      ? "text-blue-600 bg-blue-50/80 shadow-xs"
                      : "text-gray-600 hover:text-gray-900 hover:bg-gray-100/70"
                  } ${link.highlight && !active ? "text-indigo-600 bg-indigo-50/40" : ""}`}
                >
                  {Icon && <Icon className="w-4 h-4" />}
                  <span>{link.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Action Buttons */}
          <div className="hidden lg:flex items-center gap-2.5">
            {/* GitHub Repo Link */}
            <a
              href="https://github.com/kunalverma2512"
              target="_blank"
              rel="noreferrer"
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="GitHub Repository"
            >
              <GithubIcon className="w-5 h-5" />
            </a>

            {isAuthenticated ? (
              <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-medium text-gray-700">
                  <User className="w-3.5 h-3.5 text-blue-600" />
                  <span className="truncate max-w-[130px]">{user?.email || "User"}</span>
                </div>
                <button
                  onClick={logout}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-all"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={quickDemoLogin}
                  className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Demo Login</span>
                </button>
                <button
                  onClick={() => onOpenAuthModal("login")}
                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition-all flex items-center gap-1"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </button>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center gap-2 lg:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-gray-600 hover:text-gray-900 hover:bg-gray-100"
              aria-label="Toggle Navigation"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-gray-200 bg-white/95 px-4 pt-3 pb-5 space-y-2 animate-in slide-in-from-top-2">
          {navLinks.map((link) => {
            const active = isActive(link.path);
            const Icon = link.icon;
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-base font-medium transition-all ${
                  active ? "text-blue-600 bg-blue-50" : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {Icon && <Icon className="w-5 h-5" />}
                <span>{link.name}</span>
              </Link>
            );
          })}

          <div className="pt-3 border-t border-gray-200 flex flex-col gap-2">
            {isAuthenticated ? (
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">{user?.email}</span>
                <button
                  onClick={() => {
                    logout();
                    setMobileMenuOpen(false);
                  }}
                  className="text-xs font-medium text-rose-600 hover:underline flex items-center gap-1"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Logout
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    quickDemoLogin();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full py-2 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg text-center"
                >
                  Demo Login
                </button>
                <button
                  onClick={() => {
                    onOpenAuthModal("login");
                    setMobileMenuOpen(false);
                  }}
                  className="w-full py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg text-center"
                >
                  Sign In
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
