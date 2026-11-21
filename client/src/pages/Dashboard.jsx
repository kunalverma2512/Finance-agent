import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  PiggyBank,
  Receipt,
  ArrowRight,
  AlertTriangle,
  Bot,
  PlusCircle,
  Upload,
  Calendar,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";

export default function Dashboard({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [budgetStatuses, setBudgetStatuses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);

  const loadDashboardData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    try {
      const [accs, txs, bStatuses, smry, alrts] = await Promise.allSettled([
        api.accounts.list(),
        api.transactions.list({ limit: 8 }),
        api.budgets.status(),
        api.analytics.summary(),
        api.alerts.list(),
      ]);

      if (accs.status === "fulfilled") setAccounts(accs.value || []);
      if (txs.status === "fulfilled") setTransactions(txs.value?.items || txs.value || []);
      if (bStatuses.status === "fulfilled") setBudgetStatuses(bStatuses.value || []);
      if (smry.status === "fulfilled") setSummary(smry.value || null);
      if (alrts.status === "fulfilled") setAlerts(alrts.value || []);
    } catch (err) {
      console.error("Dashboard data error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [isAuthenticated]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-6 shadow-xs">
          <Wallet className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect Your Account</h2>
        <p className="text-gray-600 text-sm max-w-md mx-auto mb-8">
          Sign in or explore our verified pre-seeded dataset to review your intelligent cash flow,
          budget progress, and vector-categorized transactions.
        </p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={quickDemoLogin}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-md transition-all cursor-pointer"
          >
            Load Demo Account
          </button>
          <button
            onClick={() => onOpenAuthModal("login")}
            className="px-6 py-2.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 text-sm font-semibold rounded-xl shadow-xs transition-all cursor-pointer"
          >
            Sign In with Email
          </button>
        </div>
      </div>
    );
  }

  const totalBalance = accounts.reduce(
    (sum, a) => sum + (Number(a.current_balance) || Number(a.opening_balance) || 0),
    0
  );

  const totalIncome = Number(summary?.total_income) || 0;
  const totalExpense = Math.abs(Number(summary?.total_spending) || Number(summary?.total_expense) || 0);
  const netSavings = totalIncome - totalExpense;
  const savingsRate = totalIncome > 0 ? ((netSavings / totalIncome) * 100).toFixed(1) : "0.0";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header with Title and Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-950 tracking-tight">
            Financial Dashboard
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time balance, vector-categorized cash flow, and budget compliance.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 text-gray-600 hover:text-gray-900 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg shadow-2xs transition-colors cursor-pointer"
            title="Refresh Ledger"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          </button>
          <Link
            to="/transactions"
            className="px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg shadow-2xs transition-all flex items-center gap-1.5"
          >
            <Upload className="w-3.5 h-3.5 text-blue-600" />
            <span>Import CSV</span>
          </Link>
          <Link
            to="/assistant"
            className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition-all flex items-center gap-1.5"
          >
            <Bot className="w-3.5 h-3.5" />
            <span>Ask Assistant</span>
          </Link>
        </div>
      </div>

      {/* METRIC OVERVIEW CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Balance */}
        <div className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Balance</span>
            <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            ${totalBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-gray-500 mt-1">Across {accounts.length} active account(s)</div>
        </div>

        {/* Total Income */}
        <div className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Income</span>
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            +${totalIncome.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-gray-500 mt-1">Current period inflows</div>
        </div>

        {/* Total Spending */}
        <div className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Expenses</span>
            <div className="p-1.5 rounded-lg bg-rose-50 text-rose-600">
              <TrendingDown className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-600">
            -${totalExpense.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-gray-500 mt-1">Vector-classified outflows</div>
        </div>

        {/* Net Savings & Rate */}
        <div className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Net Savings</span>
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <PiggyBank className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-2xl font-bold ${netSavings >= 0 ? "text-indigo-600" : "text-amber-600"}`}>
            ${netSavings.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-gray-500 mt-1">{savingsRate}% savings rate</div>
        </div>
      </div>

      {/* TWO-COLUMN SECTION: RECENT TRANSACTIONS + BUDGET PROGRESS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Transactions (2 cols) */}
        <div className="lg:col-span-2 rounded-2xl bg-white border border-gray-200/80 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Receipt className="w-4 h-4 text-blue-600" />
              <h2 className="text-base font-bold text-gray-900">Recent Transactions</h2>
            </div>
            <Link
              to="/transactions"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {transactions.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-xs">
              No transactions recorded yet. Click "Import CSV" to get started.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-100 text-gray-400 font-semibold uppercase tracking-wider">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3">Category</th>
                    <th className="py-2.5 px-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 text-gray-700">
                  {transactions.slice(0, 7).map((tx) => {
                    const isExpense = Number(tx.amount) < 0;
                    return (
                      <tr key={tx.id} className="hover:bg-gray-50/70 transition-colors">
                        <td className="py-3 px-3 font-mono text-gray-500 whitespace-nowrap">
                          {tx.date}
                        </td>
                        <td className="py-3 px-3 font-medium text-gray-900">
                          {tx.description}
                        </td>
                        <td className="py-3 px-3">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                            {tx.category_name || "General"}
                          </span>
                        </td>
                        <td
                          className={`py-3 px-3 text-right font-semibold whitespace-nowrap ${
                            isExpense ? "text-gray-900" : "text-emerald-600"
                          }`}
                        >
                          {isExpense ? "-" : "+"}$
                          {Math.abs(Number(tx.amount)).toFixed(2)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Budgets & Status (1 col) */}
        <div className="rounded-2xl bg-white border border-gray-200/80 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-gray-900">Monthly Budgets</h2>
            <Link
              to="/budgets"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700"
            >
              Manage
            </Link>
          </div>

          {budgetStatuses.length === 0 ? (
            <div className="text-center py-8 text-gray-500 text-xs">
              No budgets defined. Create category targets to stay on track.
            </div>
          ) : (
            <div className="space-y-4">
              {budgetStatuses.slice(0, 5).map((b) => {
                const limit = Number(b.monthly_limit) || 1;
                const spent = Number(b.spent) || 0;
                const pct = Math.min(Math.round((spent / limit) * 100), 100);
                const isOver = spent > limit;

                return (
                  <div key={b.category_id || b.category_name} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-gray-800">{b.category_name}</span>
                      <span className={`font-mono ${isOver ? "text-rose-600 font-bold" : "text-gray-500"}`}>
                        ${spent.toFixed(0)} / ${limit.toFixed(0)}
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isOver ? "bg-rose-500" : pct > 80 ? "bg-amber-500" : "bg-blue-600"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quick AI Tip Card */}
          <div className="mt-6 p-4 rounded-xl bg-blue-50/70 border border-blue-100 text-xs text-blue-900 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-blue-700">
              <Bot className="w-3.5 h-3.5" />
              <span>Agent Optimization</span>
            </div>
            <p className="text-gray-600">
              Your discretionary spending accounts for 34% of outflows. Ask the agent for an
              immediate savings plan in the AI Assistant tab.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
