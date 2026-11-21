import React, { useState } from "react";
import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import AuthModal from "./components/AuthModal";

// Pages
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Budgets from "./pages/Budgets";
import Assistant from "./pages/Assistant";
import Analytics from "./pages/Analytics";
import About from "./pages/About";

export default function App() {
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState("login");

  const handleOpenAuth = (mode = "login") => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  return (
    <AuthProvider>
      <HashRouter>
        <div className="min-h-screen flex flex-col bg-[#fafafa] text-gray-900 selection:bg-blue-100 selection:text-blue-900 font-sans antialiased">
          {/* Persistent Navbar across all routes */}
          <Navbar onOpenAuthModal={handleOpenAuth} />

          {/* Main content view */}
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<Home onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/dashboard" element={<Dashboard onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/transactions" element={<Transactions onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/budgets" element={<Budgets onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/assistant" element={<Assistant onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/analytics" element={<Analytics onOpenAuthModal={handleOpenAuth} />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Persistent Footer across all routes */}
          <Footer />

          {/* Auth Modal for Sign In / Registration */}
          <AuthModal
            isOpen={authModalOpen}
            onClose={() => setAuthModalOpen(false)}
            initialMode={authModalMode}
          />
        </div>
      </HashRouter>
    </AuthProvider>
  );
}
