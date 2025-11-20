import { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navigation from "./components/Navigation";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DocumentsPage = lazy(() => import("./pages/DocumentsPage"));
const DocumentChunksPage = lazy(() => import("./pages/DocumentChunksPage"));
const AccessCodePage = lazy(() => import("./pages/AccessCodePage"));
const AdminDebugPage = lazy(() => import("./pages/AdminDebugPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const StudentTokensPage = lazy(() => import("./pages/StudentTokensPage"));
const ChatPage = lazy(() => import("./pages/ChatPage"));
const AuthGuard = lazy(() => import("./components/AuthGuard"));
const AdminGuard = lazy(() => import("./components/AdminGuard"));
// Rimosso CSS legacy, sostituito da Tailwind in index.css

const RouteFallback = () => (
  <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
    Caricamento interfaccia...
  </div>
);

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        <Navigation />
        <main className="flex-1">
          <Suspense fallback={<RouteFallback />}>
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
          </Suspense>
        </main>
      </div>
    </Router>
  );
}

export default App;
