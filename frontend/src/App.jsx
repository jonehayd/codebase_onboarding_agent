import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { Analytics } from "@vercel/analytics/react";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import AppPage from "./pages/AppPage";
import SharePage from "./pages/SharePage";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const analyticsMode = import.meta.env.PROD ? "production" : "development";

  return (
    <BrowserRouter>
      <Toaster theme="dark" position="bottom-right" richColors />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppPage />
            </ProtectedRoute>
          }
        />
        <Route path="/share/:token" element={<SharePage />} />
      </Routes>
      <Analytics mode={analyticsMode} />
    </BrowserRouter>
  );
}
