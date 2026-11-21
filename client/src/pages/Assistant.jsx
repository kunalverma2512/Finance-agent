import React, { useState, useEffect, useRef } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  Bot,
  User,
  Send,
  Sparkles,
  Zap,
  CheckCircle2,
  Clock,
  RotateCcw,
  ShieldCheck,
  HelpCircle,
  MessageSquare,
  ArrowRight,
  Loader2,
} from "lucide-react";

export default function Assistant({ onOpenAuthModal }) {
  const { isAuthenticated, quickDemoLogin } = useAuth();
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm your Personal Finance Intelligence Agent. Ask me anything about your spending, budgets, anomalous transactions, or personalized savings advice. All numbers come directly from your verified ledger data.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const starterPrompts = [
    "How can I save money and reduce my expenses in October?",
    "How much did I spend this month?",
    "Why did my spending increase?",
    "Am I close to my food budget?",
    "Which transaction looks unusual?",
    "How much do I need to save for my goal?",
    "Create a $500 food budget.",
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (messageText) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || loading) return;

    if (!isAuthenticated) {
      alert("Please sign in or use the demo account to chat with the agent.");
      return;
    }

    const userMsg = {
      id: Date.now().toString(),
      role: "user",
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.agent.chat(textToSend.trim());
      const agentMsg = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.response || "I processed your request.",
        intent: res.intent || res.metadata?.intent,
        tool: res.tool || res.metadata?.tool_executed,
        executionTime: res.execution_time_ms || res.metadata?.latency_ms,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err) {
      const errorMsg = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        isError: true,
        content: `Error: ${err.message || "Could not reach agent service"}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleResetChat = () => {
    setMessages([
      {
        id: "welcome",
        role: "assistant",
        content:
          "Hi! I'm your Personal Finance Intelligence Agent. Ask me anything about your spending, budgets, anomalous transactions, or personalized savings advice. All numbers come directly from your verified ledger data.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <Bot className="w-12 h-12 text-blue-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Connect to AI Finance Assistant</h2>
        <p className="text-gray-600 text-sm max-w-md mx-auto mb-6">
          Sign in or explore our verified pre-seeded dataset to chat with the multi-turn LangGraph agent.
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
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-950 tracking-tight flex items-center gap-2">
              <span>AI Finance Assistant</span>
              <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                Gemini 2.5 Flash Lite + LangGraph
              </span>
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Deterministic routing, zero hallucinations, verified SQL calculations.
            </p>
          </div>
        </div>

        <button
          onClick={handleResetChat}
          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg text-xs font-medium flex items-center gap-1 transition-colors"
          title="Reset conversation"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Clear Chat</span>
        </button>
      </div>

      {/* Chat Messages Container */}
      <div className="rounded-2xl bg-white border border-gray-200/80 shadow-xs flex flex-col h-[580px] overflow-hidden">
        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.map((m) => {
            const isUser = m.role === "user";
            return (
              <div
                key={m.id}
                className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div className={`max-w-[85%] sm:max-w-[75%] space-y-1.5`}>
                  <div
                    className={`p-4 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      isUser
                        ? "bg-blue-600 text-white rounded-tr-xs shadow-xs"
                        : m.isError
                        ? "bg-rose-50 text-rose-800 border border-rose-200 rounded-tl-xs"
                        : "bg-gray-50/90 text-gray-800 border border-gray-200/70 rounded-tl-xs"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  </div>

                  {/* Metadata Tag for AI Assistant */}
                  {!isUser && (m.intent || m.tool || m.executionTime) && (
                    <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-gray-400 pl-1 font-mono">
                      {m.intent && (
                        <span className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded border border-indigo-100">
                          intent: {m.intent}
                        </span>
                      )}
                      {m.tool && (
                        <span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-100">
                          tool: {m.tool}
                        </span>
                      )}
                      {m.executionTime && (
                        <span className="flex items-center gap-0.5 text-gray-400">
                          <Clock className="w-3 h-3" />
                          {m.executionTime}ms
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center shrink-0 mt-1">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100 mt-1">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200/70 text-xs text-gray-500 rounded-tl-xs flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                <span>LangGraph router executing RAG tools...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Starter Prompts */}
        <div className="px-4 py-2.5 bg-gray-50/70 border-t border-gray-100 overflow-x-auto flex items-center gap-2 scrollbar-none">
          <span className="text-[11px] font-semibold text-gray-400 shrink-0 uppercase tracking-wider flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-blue-500" />
            Try:
          </span>
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              disabled={loading}
              onClick={() => handleSend(prompt)}
              className="px-2.5 py-1 text-xs text-gray-600 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-gray-200 rounded-full shrink-0 shadow-2xs transition-all cursor-pointer whitespace-nowrap"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-gray-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              disabled={loading}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about spending, budgets, savings goals, or anomalies..."
              className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-gray-300 focus:outline-hidden focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-xl text-xs sm:text-sm font-semibold shadow-sm shadow-blue-500/20 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
