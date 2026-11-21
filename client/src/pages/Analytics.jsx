import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  BarChart3,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  AlertOctagon,
  Sparkles,
  PieChart,
  Calendar,
  CheckCircle2,
  RefreshCw,
  Info,
} from "lucide-react";

export default function Analytics({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const [categories, setCategories] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [catRes, anomRes, monthRes, alertRes] = await Promise.allSettled([
        api.analytics.categories(),
        api.analytics.anomalies(),
        api.analytics.monthly(),
        api.alerts.list(),
      ]);

      if (catRes.status === "fulfilled") setCategories(catRes.value || []);
      if (anomRes.status === "fulfilled") setAnomalies(anomRes.value || []);
      if (monthRes.status === "fulfilled") setMonthlyData(monthRes.value || []);
      if (alertRes.status === "fulfilled") setAlerts(alertRes.value || []);
    } catch (err) {
      console.error("Analytics load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <BarChart3 className="w-12 h-12 text-blue-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect to View Analytics</h2>
        <p className="text-gray-600 text-sm max-w-md mx-auto mb-6">
          Sign in or explore our verified pre-seeded dataset to review your intelligent cash flow.
        </p>
        <button
          onClick={quickDemoLogin}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl"
        >
          Load Demo Account
        </button>
      </div>
    );
  }

  const totalCategorySpending = categories.reduce(
    (sum, c) => sum + Math.abs(Number(c.total_amount) || Number(c.amount) || 0),
    0
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-950 tracking-tight">
            Financial Analytics & Outliers
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Statistical IQR anomaly detection, category weightings, and net cash flow trends.
          </p>
        </div>

        <button
          onClick={loadData}
          className="p-2 text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-lg shadow-2xs transition-colors self-start sm:self-auto cursor-pointer"
          title="Refresh metrics"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* TOP SECTION: CATEGORY DISTRIBUTION + ANOMALIES RADAR */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Category Breakdown */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-blue-600" />
              <h2 className="text-base font-bold text-gray-900">Category Spending Distribution</h2>
            </div>
            <span className="text-xs font-semibold text-gray-500">
              Total: ${totalCategorySpending.toFixed(2)}
            </span>
          </div>

          {categories.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-400">
              No category spending recorded for this period.
            </div>
          ) : (
            <div className="space-y-4">
              {categories.slice(0, 8).map((cat) => {
                const amount = Math.abs(Number(cat.total_amount) || Number(cat.amount) || 0);
                const pct =
                  totalCategorySpending > 0
                    ? Math.round((amount / totalCategorySpending) * 100)
                    : 0;

                return (
                  <div key={cat.category_id || cat.name} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-gray-800">{cat.name}</span>
                      <span className="font-mono text-gray-500">
                        ${amount.toFixed(2)} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-600 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Statistical Outliers / Anomalies */}
        <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <h2 className="text-base font-bold text-gray-900">
                Statistical Anomaly Radar
              </h2>
            </div>
            <span className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full">
              {anomalies.length} Flagged
            </span>
          </div>

          <p className="text-xs text-gray-500 leading-relaxed">
            Transactions that diverge significantly from your rolling historical average (via IQR
            interquartile ranges and standard deviation bounds).
          </p>

          {anomalies.length === 0 ? (
            <div className="py-12 text-center text-xs text-gray-500 flex flex-col items-center gap-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-500" />
              <span>No abnormal spending spikes detected! Your transactions are within standard variance.</span>
            </div>
          ) : (
            <div className="space-y-3">
              {anomalies.map((anom, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/50 space-y-1"
                >
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-gray-900">{anom.description || anom.merchant}</span>
                    <span className="text-rose-600 font-mono font-bold">
                      ${Math.abs(Number(anom.amount)).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-gray-500">
                    <span>{anom.date}</span>
                    <span className="text-amber-700 font-medium">{anom.reason || "Outlier spend"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* SYSTEM ALERTS & INSIGHTS */}
      <div className="p-6 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-4">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-600" />
          <h2 className="text-base font-bold text-gray-900">Proactive Guardrail Notifications</h2>
        </div>

        {alerts.length === 0 ? (
          <div className="text-xs text-gray-400 py-4">No unread alerts. You are completely caught up.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {alerts.map((al) => (
              <div
                key={al.id}
                className="p-3.5 rounded-xl border border-gray-200 bg-gray-50/60 flex items-start gap-3"
              >
                <div className="p-1.5 rounded-lg bg-blue-100 text-blue-700 shrink-0 mt-0.5">
                  <Sparkles className="w-3.5 h-3.5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-gray-900">{al.title || al.message}</h4>
                  {al.details && <p className="text-[11px] text-gray-500 mt-0.5">{al.details}</p>}
                  <span className="text-[10px] text-gray-400 mt-1 block font-mono">
                    {al.created_at || "Recent"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
