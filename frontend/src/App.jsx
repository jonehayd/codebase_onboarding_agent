import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import AppPage from "./pages/AppPage";
import SharePage from "./pages/SharePage";

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  return token ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
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
    </BrowserRouter>
  );
}
