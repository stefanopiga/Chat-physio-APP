import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import Navigation from "./components/Navigation";
import AuthGuard from "./components/AuthGuard";
import AdminGuard from "./components/AdminGuard";

// Lazy load pages for code splitting
const LoginPage = lazy(() => import("./pages/LoginPage"));
const AccessCodePage = lazy(() => import("./pages/AccessCodePage"));
const ChatPage = lazy(() => import("./pages/ChatPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const DocumentsPage = lazy(() => import("./pages/DocumentsPage"));
const DocumentChunksPage = lazy(() => import("./pages/DocumentChunksPage"));
const AdminDebugPage = lazy(() => import("./pages/AdminDebugPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const StudentTokensPage = lazy(() => import("./pages/StudentTokensPage"));

// Loading fallback component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="text-muted-foreground">Caricamento...</div>
  </div>
);

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        <Navigation />
        <main className="flex-1">
          <Suspense fallback={<PageLoader />}>
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
