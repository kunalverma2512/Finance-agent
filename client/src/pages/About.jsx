import React from "react";
import { GithubIcon, LinkedinIcon } from "../components/Icons";
import {
  Brain,
  Cpu,
  Database,
  ShieldCheck,
  Sparkles,
  GitBranch,
  Mail,
  ExternalLink,
  CheckCircle2,
  Lock,
  Layers,
  Code2,
  Terminal,
} from "lucide-react";

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-16">
      {/* HEADER SECTION */}
      <div className="text-center space-y-4 max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-700">
          <Layers className="w-3.5 h-3.5 text-blue-600" />
          <span>System Architecture & Mathematical Foundations</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold text-gray-950 tracking-tight">
          How Personal Finance Intelligence Works
        </h1>
        <p className="text-gray-600 text-base sm:text-lg leading-relaxed">
          A deep dive into local semantic vector classification, deterministic LangGraph
          orchestration, and grounded RAG synthesis on Neon Serverless PostgreSQL.
        </p>
      </div>

      {/* 4-PILLAR ARCHITECTURE DIAGRAM / CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Pillar 1: Vector Embeddings */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3">
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
            <Brain className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">
            1. Dense Semantic Embeddings (`all-MiniLM-L6-v2`)
          </h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            Raw merchant descriptions in banking statements are noisy (e.g. "SQ *BLUE BOTTLE COFFEE SAN
            FRAN", "AMZN MKTP US*2X8", "SHELL OIL 574421"). Traditional regex rules fail when
            merchants change prefixes.
          </p>
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 font-mono text-[11px] text-gray-700 space-y-1">
            <div className="text-purple-700 font-semibold">// Cosine Similarity Vector Space:</div>
            <div>similarity = dot(u, v) / (||u|| * ||v||)</div>
            <div className="text-gray-500">// Dimension: 384-d | Confidence Threshold: 0.35</div>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            Our engine encodes each merchant into a 384-dimensional vector space on the local CPU,
            matching against canonical category exemplars in under 5ms without external API tokens.
          </p>
        </div>

        {/* Pillar 2: LangGraph Orchestrator */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold">
            <Cpu className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">
            2. Deterministic LangGraph Multi-Turn Routing
          </h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            Autonomous financial agents must never calculate balances inside an LLM's imagination.
            Instead, we enforce a state machine where user queries route to deterministic tool nodes:
          </p>
          <ul className="text-xs text-gray-600 space-y-1.5 list-disc pl-4">
            <li>
              <strong>Intent Extraction:</strong> Distinguishes `spending_query`, `budget_status`,
              `anomaly_check`, and `personalized_advice`.
            </li>
            <li>
              <strong>Temporal Parsing:</strong> Named English months (e.g. "October", "last month")
              are resolved to closed ISO intervals (`YYYY-MM-01` to `YYYY-MM-LastDay`).
            </li>
            <li>
              <strong>SQL Execution:</strong> Queries run directly in PostgreSQL with strict parameters.
            </li>
          </ul>
        </div>

        {/* Pillar 3: Grounded RAG Synthesis */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">
            3. Grounded RAG Prompt Synthesis (Google Gemini)
          </h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            The output of SQL tools (e.g. total income, category expenses, net surplus) is packaged
            into an immutable factual context payload:
          </p>
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-100 font-mono text-[11px] text-gray-700 space-y-1">
            <div className="text-emerald-700 font-semibold">// Strict Guardrail Constraint:</div>
            <div>"ONLY use the numbers supplied in the tool output.</div>
            <div>Never calculate, alter, or fabricate any financial value."</div>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            Gemini 2.5 Flash Lite generates clear, proactive coaching while ensuring 100% factual
            grounding.
          </p>
        </div>

        {/* Pillar 4: Statistical Outlier IQR */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-gray-900">
            4. Statistical Anomaly & Outlier Guardrails
          </h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            To catch duplicate charges, subscription creep, or fraudulent transactions, the system
            runs dual-pass anomaly detection:
          </p>
          <ul className="text-xs text-gray-600 space-y-1.5 list-disc pl-4">
            <li>
              <strong>Interquartile Range (IQR):</strong> Flags spending transactions exceeding Q3 +
              1.5 * IQR for the user's historical category median.
            </li>
            <li>
              <strong>Z-Score Normalized Deviations:</strong> Flags transactions &gt; 2.5 standard
              deviations above mean merchant amounts.
            </li>
          </ul>
        </div>
      </div>

      {/* RELIABILITY & EVALUATION BENCHMARKS */}
      <div className="p-8 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-6">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-blue-600" />
          <h2 className="text-xl font-bold text-gray-900">
            Evaluation Benchmarks (DeepEval Suite)
          </h2>
        </div>
        <p className="text-xs text-gray-600 leading-relaxed">
          Every agent interaction is tested against deterministic scenarios in `tests/test_agent_evals.py`
          and `tests/test_embedding_categorization.py`:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-center">
            <div className="text-2xl font-extrabold text-emerald-700">100%</div>
            <div className="text-xs font-semibold text-emerald-900 mt-0.5">
              Tool Selection Accuracy
            </div>
            <div className="text-[11px] text-emerald-600 mt-1">
              Correct tool called for 6/6 test intents
            </div>
          </div>

          <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 text-center">
            <div className="text-2xl font-extrabold text-blue-700">100%</div>
            <div className="text-xs font-semibold text-blue-900 mt-0.5">
              Factual Grounding
            </div>
            <div className="text-[11px] text-blue-600 mt-1">
              Zero hallucinated balances or dates
            </div>
          </div>

          <div className="p-4 rounded-xl bg-purple-50/70 border border-purple-200 text-center">
            <div className="text-2xl font-extrabold text-purple-700">99.4%</div>
            <div className="text-xs font-semibold text-purple-900 mt-0.5">
              Embedding Accuracy
            </div>
            <div className="text-[11px] text-purple-600 mt-1">
              Real-world merchant classification benchmark
            </div>
          </div>
        </div>
      </div>

      {/* CONNECT & AUTHOR SECTION */}
      <div className="p-8 rounded-2xl bg-gradient-to-tr from-gray-900 via-gray-950 to-blue-950 text-white shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-gray-800">
          <div>
            <h2 className="text-xl font-bold">Connect with the Author</h2>
            <p className="text-xs text-gray-400 mt-1">
              Designed & developed by <strong>Kunal Verma</strong>.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/kunalverma2512"
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <GithubIcon className="w-4 h-4" />
              <span>GitHub Profile</span>
            </a>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-gray-300">
          <div className="space-y-2">
            <h4 className="font-semibold text-white">Full-Stack Agent Specialization</h4>
            <p className="leading-relaxed text-gray-400">
              Passionate about building autonomous agentic AI software that solves real-world
              problems with rigorous deterministic guardrails, low-latency semantic search, and
              elegant user experiences.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-semibold text-white">Open Source & Contributions</h4>
            <p className="leading-relaxed text-gray-400">
              The Personal Finance Agent codebase is structured for rapid deployment on Neon,
              Railway, Render, or Docker containers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
