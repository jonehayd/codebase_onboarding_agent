import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import IngestionPage from "./pages/IngestionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route path="/sessions/:sessionId/ingesting" element={<IngestionPage />} />
      </Routes>
    </BrowserRouter>
  );
}
