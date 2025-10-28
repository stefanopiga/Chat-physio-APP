import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import DocumentsPage from "./pages/DocumentsPage";
import DocumentChunksPage from "./pages/DocumentChunksPage";
import AccessCodePage from "./pages/AccessCodePage";
import AdminDebugPage from "./pages/AdminDebugPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import StudentTokensPage from "./pages/StudentTokensPage";
import AuthGuard from "./components/AuthGuard";
import AdminGuard from "./components/AdminGuard";
import ChatPage from "./pages/ChatPage";
import Navigation from "./components/Navigation";
// Rimosso CSS legacy, sostituito da Tailwind in index.css

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        <Navigation />
        <main className="flex-1">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<AccessCodePage />} />
            <Route
              path="/admin/dashboard"
              element={
                <AdminGuard>
                  <DashboardPage />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/documents"
              element={
                <AdminGuard>
                  <DocumentsPage />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/documents/:documentId/chunks"
              element={
                <AdminGuard>
                  <DocumentChunksPage />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/debug"
              element={
                <AdminGuard>
                  <AdminDebugPage />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/analytics"
              element={
                <AdminGuard>
                  <AnalyticsPage />
                </AdminGuard>
              }
            />
            <Route
              path="/admin/student-tokens"
              element={
                <AdminGuard>
                  <StudentTokensPage />
                </AdminGuard>
              }
            />
            <Route
              path="/chat"
              element={
                <AuthGuard>
                  <ChatPage />
                </AuthGuard>
              }
            />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
