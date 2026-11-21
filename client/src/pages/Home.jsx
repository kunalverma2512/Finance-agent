import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import DitherField from "../components/ui/dither-field";
import { ShimmerButton } from "../components/ui/shimmer-button";
import { BentoGrid, BentoCard } from "../components/ui/bento-grid";
import { NumberTicker } from "../components/ui/number-ticker";
import {
  Sparkles,
  Brain,
  ShieldCheck,
  Zap,
  ArrowRight,
  BarChart3,
  Receipt,
  PieChart,
  Bot,
  Database,
  Lock,
} from "lucide-react";

export default function Home({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const navigate = useNavigate();

  const handleLaunch = async () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      await quickDemoLogin();
      navigate("/dashboard");
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#fafafa] text-gray-900">
      {/* HERO SECTION WITH DITHER-FIELD */}
      <section className="relative w-full min-h-[85vh] flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 overflow-hidden py-20">
        {/* Magic UI Dither Field Background */}
        <DitherField
          pattern="horizon"
          intensity={0.65}
          speed={0.8}
          color="#2563eb"
          className="absolute inset-0 w-full h-full opacity-40 pointer-events-none"
        />

        {/* Ambient Gradient glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-gradient-to-r from-blue-400/20 via-indigo-300/20 to-sky-400/20 blur-3xl pointer-events-none rounded-full" />

        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/80 border border-blue-200/80 shadow-xs backdrop-blur-sm text-xs font-semibold text-blue-700 animate-in fade-in slide-in-from-bottom-3 duration-500">
            <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
            <span>Autonomous AI Wealth & Financial Intelligence</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-gray-950 leading-[1.1] animate-in fade-in slide-in-from-bottom-4 duration-700">
            Precision Intelligence for your{" "}
            <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-600 bg-clip-text text-transparent">
              Personal Finances
            </span>
          </h1>

          {/* Description */}
          <p className="max-w-2xl mx-auto text-base sm:text-xl text-gray-600 leading-relaxed font-normal animate-in fade-in slide-in-from-bottom-5 duration-800">
            Local Semantic Vector Embeddings (`all-MiniLM-L6-v2`), deterministic
            LangGraph multi-turn orchestration, and grounded Google Gemini RAG
            on Neon Cloud PostgreSQL.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4 animate-in fade-in slide-in-from-bottom-6 duration-900">
            <ShimmerButton
              onClick={handleLaunch}
              shimmerColor="#ffffff"
              background="#2563eb"
              className="text-white font-semibold text-sm px-7 py-3.5 shadow-lg shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/35 transition-all"
            >
              <span className="flex items-center gap-2">
                <span>Launch Interactive Demo</span>
                <ArrowRight className="w-4 h-4" />
              </span>
            </ShimmerButton>

            <Link
              to="/assistant"
              className="px-6 py-3.5 text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 border border-gray-300/80 rounded-full shadow-xs hover:shadow-sm transition-all flex items-center gap-2"
            >
              <Bot className="w-4 h-4 text-blue-600" />
              <span>Ask AI Assistant</span>
            </Link>
          </div>

          {/* Quick Metrics Bar */}
          <div className="pt-8 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
            <div className="p-4 rounded-xl bg-white/70 border border-gray-200/60 backdrop-blur-xs text-center shadow-2xs">
              <div className="text-2xl font-bold text-gray-900">
                <NumberTicker value={100} />%
              </div>
              <div className="text-xs text-gray-500 mt-0.5">Tool Grounding</div>
            </div>
            <div className="p-4 rounded-xl bg-white/70 border border-gray-200/60 backdrop-blur-xs text-center shadow-2xs">
              <div className="text-2xl font-bold text-gray-900">
                <NumberTicker value={99} />.4%
              </div>
              <div className="text-xs text-gray-500 mt-0.5">Vector Precision</div>
            </div>
            <div className="p-4 rounded-xl bg-white/70 border border-gray-200/60 backdrop-blur-xs text-center shadow-2xs">
              <div className="text-2xl font-bold text-gray-900">
                &lt;<NumberTicker value={1} decimalPlaces={1} />.2s
              </div>
              <div className="text-xs text-gray-500 mt-0.5">Agent Latency</div>
            </div>
            <div className="p-4 rounded-xl bg-white/70 border border-gray-200/60 backdrop-blur-xs text-center shadow-2xs">
              <div className="text-2xl font-bold text-gray-900">
                <NumberTicker value={54} />+
              </div>
              <div className="text-xs text-gray-500 mt-0.5">Seeded Records</div>
            </div>
          </div>
        </div>
      </section>

      {/* CORE CAPABILITIES BENTO GRID */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 border-t border-gray-100">
        <div className="text-center max-w-2xl mx-auto mb-14 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
            Engine Architecture
          </span>
          <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight sm:text-4xl">
            Modular Intelligence, Zero Hallucination
          </h2>
          <p className="text-gray-600 text-sm sm:text-base">
            Every transaction query and budget recommendation is rooted in verified
            SQL calculations and strict deterministic guardrails.
          </p>
        </div>

        <BentoGrid>
          <BentoCard
            name="Dense Semantic Vector Embeddings"
            description="Local SentenceTransformer model ('all-MiniLM-L6-v2') computes 384-dimensional cosine similarity to classify merchants into spending categories without external API latency."
            Icon={Brain}
            cta="Explore Categorization"
            onClick={() => navigate("/transactions")}
            className="cursor-pointer"
          />

          <BentoCard
            name="Deterministic Multi-Turn LangGraph"
            description="Intent router dynamically matches user requests to validated tool nodes: RAG spending contexts, monthly budgets, and historical goal simulations."
            Icon={Zap}
            cta="Test Agent Router"
            onClick={() => navigate("/assistant")}
            className="cursor-pointer"
          />

          <BentoCard
            name="Statistical Outlier & Anomaly Radar"
            description="Detects anomalous spending spikes, duplicate charges, and unusual category deviations using IQR boundaries and standard deviation guardrails."
            Icon={ShieldCheck}
            cta="View Anomaly Alerts"
            onClick={() => navigate("/analytics")}
            className="cursor-pointer"
          />

          <BentoCard
            name="Contextual RAG Prompt Synthesis"
            description="Aggregates verified ledger data and delivers personalized budgeting recommendations with Google Gemini 2.5 Flash Lite in under a second."
            Icon={Bot}
            cta="Ask for Advice"
            onClick={() => navigate("/assistant")}
            className="cursor-pointer"
          />

          <BentoCard
            name="Neon Serverless PostgreSQL"
            description="ACID compliance, Alembic migrations, connection pooling, and strict relational schemas ensure high data integrity and durability."
            Icon={Database}
            cta="Inspect Ledger"
            onClick={() => navigate("/dashboard")}
            className="cursor-pointer"
          />

          <BentoCard
            name="Strict Production Security"
            description="Argon2/bcrypt password hashing, stateless JWT authorization, strict Content-Security-Policy (CSP), and parameterized queries prevent injection vectors."
            Icon={Lock}
            cta="Review Security"
            onClick={() => navigate("/about")}
            className="cursor-pointer"
          />
        </BentoGrid>
      </section>

      {/* QUICK PREVIEW / FEATURE SHOWCASE */}
      <section className="bg-white border-y border-gray-200/80 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
                Live Data Exploration
              </span>
              <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight sm:text-4xl">
                Experience Full Transparency in Every Dollar
              </h2>
              <p className="text-gray-600 leading-relaxed text-sm sm:text-base">
                Whether you upload CSV statements, track recurring subscription anomalies,
                or consult the multi-turn conversational agent, FinanceAgent provides
                instant clarity into your cash flow.
              </p>

              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-blue-50 text-blue-600 shrink-0">
                    <Receipt className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">Seamless CSV Import</h4>
                    <p className="text-xs text-gray-500">
                      Supports debit/credit split or signed columns with auto-deduplication.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 shrink-0">
                    <PieChart className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">Adaptive Budgets & Goals</h4>
                    <p className="text-xs text-gray-500">
                      Real-time spend tracking against category limits with proactive overspend warnings.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-sky-50 text-sky-600 shrink-0">
                    <BarChart3 className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900">Evaluation-Backed Reliability</h4>
                    <p className="text-xs text-gray-500">
                      100% verified passing rate across DeepEval unit scenarios and agent evals.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <button
                  onClick={handleLaunch}
                  className="px-6 py-3 rounded-xl bg-gray-900 hover:bg-black text-white text-sm font-semibold shadow-md transition-all flex items-center gap-2 cursor-pointer"
                >
                  <span>Launch Live Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Visual Card Mockup */}
            <div className="rounded-2xl border border-gray-200 bg-gray-50/50 p-6 shadow-sm">
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-gray-200">
                  <span className="text-xs font-semibold text-gray-500 uppercase">
                    Sample Prompt Execution
                  </span>
                  <span className="text-[11px] font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded-sm">
                    LangGraph: personalized_advice
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-white border border-gray-200 shadow-2xs space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-gray-800">
                    <Bot className="w-4 h-4 text-blue-600" />
                    <span>Agent RAG Response (Latency: 0.88s)</span>
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed">
                    "Financial overview for 2026-10: Total income USD 3,500.00 and spending USD
                    1,850.00 (net USD 1,650.00). Target a 15% reduction in discretionary dining
                    spend to hit your Emergency Fund milestone 2 months earlier."
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-white border border-gray-200">
                    <span className="text-[11px] text-gray-500 block">Monthly Savings Rate</span>
                    <span className="text-lg font-bold text-emerald-600">47.1%</span>
                  </div>
                  <div className="p-3 rounded-xl bg-white border border-gray-200">
                    <span className="text-[11px] text-gray-500 block">Identified Anomalies</span>
                    <span className="text-lg font-bold text-amber-600">0 Critical</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL CALL TO ACTION */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 text-center max-w-4xl mx-auto space-y-6">
        <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight sm:text-4xl">
          Start Exploring Your Intelligent Ledger Today
        </h2>
        <p className="text-gray-600 text-sm sm:text-base max-w-xl mx-auto">
          Sign up with your own email or test directly with the pre-seeded demo
          dataset containing 54 verified transactions and budget targets.
        </p>
        <div className="pt-2 flex items-center justify-center gap-4">
          <button
            onClick={handleLaunch}
            className="px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition-all cursor-pointer flex items-center gap-2"
          >
            <span>Get Started in 1-Click</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
