import React from "react";
import { Link } from "react-router-dom";
import { GithubIcon } from "./Icons";
import { Sparkles, ExternalLink, ShieldCheck, Cpu, Database, Brain } from "lucide-react";

export default function Footer() {
  return (
    <footer className="w-full border-t border-gray-200 bg-white pt-14 pb-8 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-12 border-b border-gray-100">
          {/* Col 1: Brand & Mission */}
          <div className="space-y-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold tracking-tight text-gray-900">
                Finance<span className="text-blue-600">Agent</span>
              </span>
            </Link>
            <p className="text-sm text-gray-600 leading-relaxed">
              Production-grade Autonomous Personal Finance Intelligence system.
              Empowering proactive financial autonomy via vector embeddings,
              LangGraph deterministic execution, and grounded RAG synthesis.
            </p>
            <div className="flex items-center gap-2 text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-md w-fit border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              FastAPI + Neon Cloud Connected
            </div>
          </div>

          {/* Col 2: Capabilities */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-900 mb-4">
              Intelligence Engine
            </h4>
            <ul className="space-y-2.5 text-sm text-gray-600">
              <li className="flex items-center gap-1.5 hover:text-blue-600 transition-colors">
                <Brain className="w-3.5 h-3.5 text-blue-500" />
                <Link to="/transactions">Semantic Embeddings (`all-MiniLM-L6-v2`)</Link>
              </li>
              <li className="flex items-center gap-1.5 hover:text-blue-600 transition-colors">
                <Cpu className="w-3.5 h-3.5 text-indigo-500" />
                <Link to="/assistant">LangGraph Deterministic Router</Link>
              </li>
              <li className="flex items-center gap-1.5 hover:text-blue-600 transition-colors">
                <Database className="w-3.5 h-3.5 text-emerald-500" />
                <Link to="/analytics">RAG Context Grounding</Link>
              </li>
              <li className="flex items-center gap-1.5 hover:text-blue-600 transition-colors">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-500" />
                <Link to="/budgets">Outlier Anomaly Guardrails</Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Navigation */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-900 mb-4">
              Application
            </h4>
            <ul className="space-y-2.5 text-sm text-gray-600">
              <li>
                <Link to="/dashboard" className="hover:text-blue-600 transition-colors">
                  Financial Dashboard
                </Link>
              </li>
              <li>
                <Link to="/transactions" className="hover:text-blue-600 transition-colors">
                  Transaction Ledger & Import
                </Link>
              </li>
              <li>
                <Link to="/budgets" className="hover:text-blue-600 transition-colors">
                  Budgets & Milestone Goals
                </Link>
              </li>
              <li>
                <Link to="/assistant" className="hover:text-blue-600 transition-colors">
                  AI Financial Assistant
                </Link>
              </li>
              <li>
                <Link to="/about" className="hover:text-blue-600 transition-colors">
                  Architecture & Theory
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Connect & Links */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-900 mb-4">
              Connect & Source
            </h4>
            <p className="text-sm text-gray-600 mb-3">
              Crafted by <strong>Kunal Verma</strong>. Designed with modern open components, responsive layouts, and zero bloat.
            </p>
            <div className="flex flex-col gap-2">
              <a
                href="https://github.com/kunalverma2512"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900 hover:underline"
              >
                <GithubIcon className="w-4 h-4" />
                <span>github.com/kunalverma2512</span>
              </a>
              <Link
                to="/about"
                className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                <span>Read System Architecture</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-gray-500 gap-3">
          <p>© {new Date().getFullYear()} FinanceAgent. Production Personal Finance Intelligence.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Agent Evals 100% Passing (DeepEval)
            </span>
            <span>Local Python 3.11 Runtime</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
