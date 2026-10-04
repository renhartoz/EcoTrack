import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "@/context/AuthContext";
import { AppShell } from "@/components/layout/AppShell";
import { PrivateRoute } from "@/components/layout/PrivateRoute";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { UploadPage } from "@/features/upload/pages/UploadPage";
import { UploadHistoryPage } from "@/features/upload/pages/UploadHistoryPage";
import { ReviewPage } from "@/features/review/pages/ReviewPage";
import { DepositsPage } from "@/features/deposits/pages/DepositsPage";
import { NasabahPage } from "@/features/nasabah/pages/NasabahPage";
import { ReportsPage } from "@/features/reports/pages/ReportsPage";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<PrivateRoute />}>
              <Route element={<AppShell />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/uploads" element={<UploadHistoryPage />} />
                <Route path="/uploads/:id" element={<ReviewPage />} />
                <Route path="/deposits" element={<DepositsPage />} />
                <Route path="/nasabah" element={<NasabahPage />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
