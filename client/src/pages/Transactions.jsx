import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  Receipt,
  Upload,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Trash2,
  Brain,
  RefreshCw,
  Wallet,
  Loader2,
} from "lucide-react";

export default function Transactions({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedAccount, setSelectedAccount] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");

  // Modals state
  const [showImportModal, setShowImportModal] = useState(false);
  const [showAddAccountModal, setShowAddAccountModal] = useState(false);
  const [showAddTxModal, setShowAddTxModal] = useState(false);

  // Import form state
  const [importAccountId, setImportAccountId] = useState("");
  const [importSign, setImportSign] = useState("negative_is_expense");
  const [importFile, setImportFile] = useState(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult, setImportResult] = useState(null);

  // Add Account form state
  const [newAccName, setNewAccName] = useState("");
  const [newAccType, setNewAccType] = useState("checking");
  const [newAccBalance, setNewAccBalance] = useState("0");
  const [accLoading, setAccLoading] = useState(false);

  // Recategorizing state
  const [recatLoading, setRecatLoading] = useState(false);
  const [recatNotice, setRecatNotice] = useState(null);

  const loadData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [accRes, catRes, txRes] = await Promise.allSettled([
        api.accounts.list(),
        api.categories.list(),
        api.transactions.list({ limit: 200 }),
      ]);

      if (accRes.status === "fulfilled") {
        setAccounts(accRes.value || []);
        if (accRes.value?.length && !importAccountId) {
          setImportAccountId(accRes.value[0].id);
        }
      }
      if (catRes.status === "fulfilled") setCategories(catRes.value || []);
      if (txRes.status === "fulfilled") {
        setTransactions(txRes.value?.items || txRes.value || []);
      }
    } catch (err) {
      console.error("Error loading transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAuthenticated]);

  const handleImport = async (e) => {
    e.preventDefault();
    if (!importAccountId || !importFile) return;
    setImportLoading(true);
    setImportResult(null);
    try {
      const res = await api.transactions.importCsv(importAccountId, importFile, importSign);
      setImportResult({
        success: true,
        message: `Imported ${res.imported_count || res.count || 0} transactions (${res.duplicates_skipped || 0} duplicates skipped).`,
      });
      await loadData();
      setTimeout(() => setShowImportModal(false), 1800);
    } catch (err) {
      setImportResult({
        success: false,
        message: err.message || "Failed to import CSV",
      });
    } finally {
      setImportLoading(false);
    }
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    if (!newAccName.trim()) return;
    setAccLoading(true);
    try {
      await api.accounts.create({
        name: newAccName.trim(),
        account_type: newAccType,
        opening_balance: Number(newAccBalance) || 0,
      });
      setNewAccName("");
      setShowAddAccountModal(false);
      await loadData();
    } catch (err) {
      alert(err.message || "Failed to create account");
    } finally {
      setAccLoading(false);
    }
  };

  const handleRecategorize = async () => {
    setRecatLoading(true);
    setRecatNotice(null);
    try {
      const res = await api.transactions.recategorize();
      setRecatNotice(
        `Vector classification updated: ${res.categorized_count || 0} transactions updated with 'all-MiniLM-L6-v2' embeddings.`
      );
      await loadData();
    } catch (err) {
      setRecatNotice(`Recategorization failed: ${err.message}`);
    } finally {
      setRecatLoading(false);
      setTimeout(() => setRecatNotice(null), 5000);
    }
  };

  const handleDeleteTx = async (txId) => {
    if (!confirm("Are you sure you want to delete this transaction?")) return;
    try {
      await api.transactions.delete(txId);
      setTransactions((prev) => prev.filter((t) => t.id !== txId));
    } catch (err) {
      alert("Failed to delete transaction: " + err.message);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <Receipt className="w-12 h-12 text-blue-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect to View Transactions</h2>
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

  // Filtered transactions
  const filtered = transactions.filter((t) => {
    const descMatch = t.description?.toLowerCase().includes(search.toLowerCase());
    const accMatch = selectedAccount ? t.account_id === selectedAccount : true;
    const catMatch = selectedCategory ? t.category_id === selectedCategory : true;
    return descMatch && accMatch && catMatch;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-950 tracking-tight">
            Transactions Ledger
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Categorized via Local SentenceTransformers (`all-MiniLM-L6-v2`) & exact rule overrides.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleRecategorize}
            disabled={recatLoading}
            className="px-3.5 py-2 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg shadow-2xs transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Re-run Semantic Vector Embeddings across all transactions"
          >
            <Brain className="w-3.5 h-3.5 text-indigo-600" />
            <span>{recatLoading ? "Recategorizing..." : "Vector Recategorize"}</span>
          </button>

          <button
            onClick={() => setShowAddAccountModal(true)}
            className="px-3.5 py-2 text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg shadow-2xs transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Wallet className="w-3.5 h-3.5 text-blue-600" />
            <span>Add Account</span>
          </button>

          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm shadow-blue-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Statement</span>
          </button>
        </div>
      </div>

      {/* Recategorize Notification */}
      {recatNotice && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-xs text-indigo-900 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-indigo-600 shrink-0" />
          <span>{recatNotice}</span>
        </div>
      )}

      {/* Account Cards Bar */}
      {accounts.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {accounts.map((acc) => (
            <div
              key={acc.id}
              onClick={() =>
                setSelectedAccount(selectedAccount === acc.id ? "" : acc.id)
              }
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                selectedAccount === acc.id
                  ? "border-blue-600 bg-blue-50/50 shadow-xs"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span className="font-semibold text-gray-800">{acc.name}</span>
                <span className="uppercase text-[10px] tracking-wider font-mono">
                  {acc.account_type}
                </span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                ${(Number(acc.current_balance) || Number(acc.opening_balance) || 0).toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="p-4 rounded-2xl bg-white border border-gray-200/80 shadow-xs flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search merchant, description, notes..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-gray-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 text-xs rounded-lg border border-gray-200 bg-white text-gray-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>

          {(search || selectedAccount || selectedCategory) && (
            <button
              onClick={() => {
                setSearch("");
                setSelectedAccount("");
                setSelectedCategory("");
              }}
              className="text-xs text-gray-500 hover:text-gray-900 font-medium px-2 py-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Transactions Table */}
      <div className="rounded-2xl bg-white border border-gray-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-20 text-center text-gray-500 text-xs flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            <span>Loading transactions...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center text-gray-500 text-xs space-y-3">
            <FileSpreadsheet className="w-8 h-8 mx-auto text-gray-300" />
            <p>No transactions match your current search or filters.</p>
            <button
              onClick={() => setShowImportModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold"
            >
              Import CSV Statement
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50/70 border-b border-gray-100 text-gray-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Merchant / Description</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Classifier Source</th>
                  <th className="py-3 px-4 text-right">Amount</th>
                  <th className="py-3 px-4 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-gray-700">
                {filtered.map((tx) => {
                  const isExpense = Number(tx.amount) < 0;
                  const source = tx.category_source || "RULE";

                  return (
                    <tr key={tx.id} className="hover:bg-gray-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-mono text-gray-500 whitespace-nowrap">
                        {tx.date}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-gray-900">
                        {tx.description}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-100">
                          {tx.category_name || "Uncategorized"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                            source === "ML" || source === "EMBEDDING"
                              ? "bg-purple-50 text-purple-700 border border-purple-200"
                              : "bg-gray-100 text-gray-600"
                          }`}
                        >
                          {source === "ML" || source === "EMBEDDING" && (
                            <Brain className="w-3 h-3 text-purple-600" />
                          )}
                          {source === "ML" ? "EMBEDDING (MiniLM)" : source}
                        </span>
                      </td>
                      <td
                        className={`py-3.5 px-4 text-right font-bold whitespace-nowrap ${
                          isExpense ? "text-gray-900" : "text-emerald-600"
                        }`}
                      >
                        {isExpense ? "-" : "+"}$
                        {Math.abs(Number(tx.amount)).toFixed(2)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={() => handleDeleteTx(tx.id)}
                          className="p-1 text-gray-400 hover:text-rose-600 rounded-md transition-colors"
                          title="Delete transaction"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* IMPORT CSV MODAL */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-gray-900">Import CSV Statement</h3>
              </div>
              <button
                onClick={() => setShowImportModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {importResult && (
              <div
                className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
                  importResult.success
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : "bg-rose-50 text-rose-800 border border-rose-200"
                }`}
              >
                {importResult.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                )}
                <span>{importResult.message}</span>
              </div>
            )}

            <form onSubmit={handleImport} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Target Account
                </label>
                <select
                  required
                  value={importAccountId}
                  onChange={(e) => setImportAccountId(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 bg-white"
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.account_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Amount Sign Convention
                </label>
                <select
                  value={importSign}
                  onChange={(e) => setImportSign(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 bg-white"
                >
                  <option value="negative_is_expense">
                    Negative = expense (e.g. -45.00 is spent)
                  </option>
                  <option value="positive_is_expense">
                    Positive = expense (e.g. 45.00 is spent)
                  </option>
                </select>
                <p className="text-[11px] text-gray-500 mt-1">
                  Choose based on your bank or statement format.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  CSV File
                </label>
                <input
                  type="file"
                  required
                  accept=".csv"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-gray-700 border border-gray-300 rounded-lg file:mr-3 file:py-2 file:px-3 file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  Requires date, description, and amount (or debit/credit) columns. Re-importing
                  the same file never creates duplicates.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importLoading || !importFile}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  {importLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                  <span>{importLoading ? "Importing & Classifying..." : "Upload & Parse"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ADD ACCOUNT MODAL */}
      {showAddAccountModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <h3 className="text-base font-bold text-gray-900">Add Bank Account</h3>
            <form onSubmit={handleCreateAccount} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Account Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Primary Checking"
                  value={newAccName}
                  onChange={(e) => setNewAccName(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Type
                </label>
                <select
                  value={newAccType}
                  onChange={(e) => setNewAccType(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300 bg-white"
                >
                  <option value="checking">Checking</option>
                  <option value="savings">Savings</option>
                  <option value="credit">Credit Card</option>
                  <option value="investment">Investment</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Opening Balance ($)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={newAccBalance}
                  onChange={(e) => setNewAccBalance(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-300"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddAccountModal(false)}
                  className="px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={accLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
                >
                  {accLoading ? "Adding..." : "Add Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
