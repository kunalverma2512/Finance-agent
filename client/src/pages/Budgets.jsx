import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  PieChart,
  Target,
  Plus,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  TrendingUp,
  DollarSign,
  Calendar,
  Sparkles,
  Loader2,
} from "lucide-react";

export default function Budgets({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const [budgetStatuses, setBudgetStatuses] = useState([]);
  const [goals, setGoals] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal / Form states
  const [showAddBudget, setShowAddBudget] = useState(false);
  const [budgetCategory, setBudgetCategory] = useState("");
  const [budgetLimit, setBudgetLimit] = useState("");
  const [budgetMonth, setBudgetMonth] = useState(new Date().toISOString().slice(0, 7));
  const [budgetSaving, setBudgetSaving] = useState(false);

  const [showAddGoal, setShowAddGoal] = useState(false);
  const [goalName, setGoalName] = useState("");
  const [goalTarget, setGoalTarget] = useState("");
  const [goalDate, setGoalDate] = useState("");
  const [goalSaving, setGoalSaving] = useState(false);

  const [contributeGoalId, setContributeGoalId] = useState(null);
  const [contribAmount, setContribAmount] = useState("");

  const loadData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [bRes, gRes, cRes] = await Promise.allSettled([
        api.budgets.status(budgetMonth),
        api.goals.list(),
        api.categories.list(),
      ]);

      if (bRes.status === "fulfilled") setBudgetStatuses(bRes.value || []);
      if (gRes.status === "fulfilled") setGoals(gRes.value || []);
      if (cRes.status === "fulfilled") {
        setCategories(cRes.value || []);
        if (cRes.value?.length && !budgetCategory) {
          setBudgetCategory(cRes.value[0].id);
        }
      }
    } catch (err) {
      console.error("Budgets load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAuthenticated, budgetMonth]);

  const handleCreateBudget = async (e) => {
    e.preventDefault();
    if (!budgetCategory || !budgetLimit) return;
    setBudgetSaving(true);
    try {
      await api.budgets.create({
        category_id: budgetCategory,
        monthly_limit: Number(budgetLimit),
        month: budgetMonth,
      });
      setShowAddBudget(false);
      setBudgetLimit("");
      await loadData();
    } catch (err) {
      alert("Failed to save budget: " + err.message);
    } finally {
      setBudgetSaving(false);
    }
  };

  const handleCreateGoal = async (e) => {
    e.preventDefault();
    if (!goalName || !goalTarget) return;
    setGoalSaving(true);
    try {
      await api.goals.create({
        name: goalName,
        target_amount: Number(goalTarget),
        target_date: goalDate || null,
      });
      setShowAddGoal(false);
      setGoalName("");
      setGoalTarget("");
      setGoalDate("");
      await loadData();
    } catch (err) {
      alert("Failed to create goal: " + err.message);
    } finally {
      setGoalSaving(false);
    }
  };

  const handleContribute = async (e) => {
    e.preventDefault();
    if (!contributeGoalId || !contribAmount) return;
    try {
      await api.goals.contribute(contributeGoalId, Number(contribAmount));
      setContributeGoalId(null);
      setContribAmount("");
      await loadData();
    } catch (err) {
      alert("Failed to contribute to goal: " + err.message);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <PieChart className="w-12 h-12 text-blue-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect to Track Budgets</h2>
        <p className="text-gray-600 text-sm max-w-md mx-auto mb-6">
          Set monthly category limits and monitor your milestone goals with automated AI tracking.
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-950 tracking-tight">
            Budgets & Goals
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Proactive guardrails against discretionary overspending and goal milestone tracking.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <input
            type="month"
            value={budgetMonth}
            onChange={(e) => setBudgetMonth(e.target.value)}
            className="px-3 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-200 rounded-lg shadow-2xs"
          />

          <button
            onClick={() => setShowAddBudget(true)}
            className="px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Budget</span>
          </button>

          <button
            onClick={() => setShowAddGoal(true)}
            className="px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg shadow-2xs transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Target className="w-3.5 h-3.5 text-indigo-600" />
            <span>Add Goal</span>
          </button>
        </div>
      </div>

      {/* BUDGETS SECTION */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Monthly Category Budgets ({budgetMonth})
            </h2>
          </div>
        </div>

        {budgetStatuses.length === 0 ? (
          <div className="p-8 rounded-2xl bg-white border border-gray-200/80 text-center text-xs text-gray-500 space-y-2">
            <p>No budgets configured for {budgetMonth}.</p>
            <button
              onClick={() => setShowAddBudget(true)}
              className="text-blue-600 font-semibold hover:underline"
            >
              Set category spending limits
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {budgetStatuses.map((b) => {
              const limit = Number(b.monthly_limit) || 1;
              const spent = Number(b.spent) || 0;
              const remaining = limit - spent;
              const pct = Math.min(Math.round((spent / limit) * 100), 100);
              const isOver = spent > limit;

              return (
                <div
                  key={b.category_id || b.category_name}
                  className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3.5"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">
                        {b.category_name}
                      </h3>
                      <span className="text-[11px] text-gray-500 font-medium">
                        {isOver ? (
                          <span className="text-rose-600 font-semibold flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" />
                            Over by ${(spent - limit).toFixed(2)}
                          </span>
                        ) : (
                          <span>${remaining.toFixed(2)} remaining</span>
                        )}
                      </span>
                    </div>

                    <span
                      className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                        isOver
                          ? "bg-rose-50 text-rose-700 border border-rose-200"
                          : pct > 85
                          ? "bg-amber-50 text-amber-700 border border-amber-200"
                          : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      }`}
                    >
                      {pct}%
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full h-2.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isOver
                          ? "bg-rose-500"
                          : pct > 85
                          ? "bg-amber-500"
                          : "bg-blue-600"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-500 pt-1 border-t border-gray-50">
                    <span>Spent: ${spent.toFixed(2)}</span>
                    <span className="font-medium text-gray-700">Limit: ${limit.toFixed(2)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SAVINGS GOALS SECTION */}
      <div className="space-y-4 pt-6 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-gray-900">Savings & Milestone Goals</h2>
          </div>
        </div>

        {goals.length === 0 ? (
          <div className="p-8 rounded-2xl bg-white border border-gray-200/80 text-center text-xs text-gray-500 space-y-2">
            <p>No savings milestones added yet.</p>
            <button
              onClick={() => setShowAddGoal(true)}
              className="text-indigo-600 font-semibold hover:underline"
            >
              Add your first goal (e.g. Emergency Fund)
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {goals.map((goal) => {
              const current = Number(goal.current_amount) || 0;
              const target = Number(goal.target_amount) || 1;
              const pct = Math.min(Math.round((current / target) * 100), 100);

              return (
                <div
                  key={goal.id}
                  className="p-5 rounded-2xl bg-white border border-gray-200/80 shadow-xs space-y-3.5"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">{goal.name}</h3>
                      {goal.target_date && (
                        <span className="text-[11px] text-gray-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="w-3 h-3" />
                          Target: {goal.target_date}
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                      {pct}%
                    </span>
                  </div>

                  <div className="w-full h-2.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-500 pt-1">
                    <span>${current.toFixed(0)} saved</span>
                    <span className="font-semibold text-gray-900">
                      ${target.toFixed(0)} goal
                    </span>
                  </div>

                  <div className="pt-2">
                    <button
                      onClick={() => setContributeGoalId(goal.id)}
                      className="w-full py-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100/70 rounded-lg transition-colors cursor-pointer"
                    >
                      + Add Contribution
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ADD BUDGET MODAL */}
      {showAddBudget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900">Set Monthly Budget</h3>
            <form onSubmit={handleCreateBudget} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Category
                </label>
                <select
                  required
                  value={budgetCategory}
                  onChange={(e) => setBudgetCategory(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 bg-white"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Monthly Limit ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="e.g. 500"
                  value={budgetLimit}
                  onChange={(e) => setBudgetLimit(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Month
                </label>
                <input
                  type="month"
                  required
                  value={budgetMonth}
                  onChange={(e) => setBudgetMonth(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddBudget(false)}
                  className="px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={budgetSaving}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
                >
                  {budgetSaving ? "Saving..." : "Save Budget"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD GOAL MODAL */}
      {showAddGoal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900">Add Savings Goal</h3>
            <form onSubmit={handleCreateGoal} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Goal Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Emergency Fund"
                  value={goalName}
                  onChange={(e) => setGoalName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Amount ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="e.g. 5000"
                  value={goalTarget}
                  onChange={(e) => setGoalTarget(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Date (Optional)
                </label>
                <input
                  type="date"
                  value={goalDate}
                  onChange={(e) => setGoalDate(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddGoal(false)}
                  className="px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={goalSaving}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                >
                  {goalSaving ? "Creating..." : "Create Goal"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONTRIBUTE MODAL */}
      {contributeGoalId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-xs w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900">Add Funds to Goal</h3>
            <form onSubmit={handleContribute} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Contribution Amount ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  autoFocus
                  placeholder="e.g. 250"
                  value={contribAmount}
                  onChange={(e) => setContribAmount(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setContributeGoalId(null)}
                  className="px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                >
                  Save Deposit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
