import { Navigate, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "./ThemeContext";
import { AuthProvider, useAuth } from "./AuthContext";
import ErrorBoundary from "./components/ErrorBoundary";
import AppLayout from "./components/AppLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import History from "./pages/History";
import Landing from "./pages/Landing";
import InsightsTab from "./pages/InsightsTab";
import DevicesTab from "./pages/DevicesTab";
import ForecastTab from "./pages/ForecastTab";
import OptimizeTab from "./pages/OptimizeTab";
import "./App.css";

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/app" element={<RequireAuth><AppLayout /></RequireAuth>}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<InsightsTab />} />
              <Route path="devices" element={<DevicesTab />} />
              <Route path="forecast" element={<ForecastTab />} />
              <Route path="optimize" element={<OptimizeTab />} />
            </Route>

            {/* Back-compat: old single-page route → new app shell */}
            <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
            <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
