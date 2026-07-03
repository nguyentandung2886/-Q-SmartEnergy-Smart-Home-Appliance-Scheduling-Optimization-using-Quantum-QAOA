import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "./ThemeContext";
import { AuthProvider, useAuth } from "./AuthContext";
import { getMe } from "./api";
import ErrorBoundary from "./components/ErrorBoundary";
import AppLayout from "./components/AppLayout";
import AdminLayout from "./components/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminFeedback from "./pages/admin/AdminFeedback";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminLogs from "./pages/admin/AdminLogs";
import Login from "./pages/Login";
import Register from "./pages/Register";
import History from "./pages/History";
import Landing from "./pages/Landing";
import InsightsTab from "./pages/InsightsTab";
import DevicesTab from "./pages/DevicesTab";
import ForecastTab from "./pages/ForecastTab";
import OptimizeTab from "./pages/OptimizeTab";
import FeedbackTab from "./pages/FeedbackTab";
import GuideTab from "./pages/GuideTab";
import ProfileTab from "./pages/ProfileTab";
import "./App.css";

function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return null;
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

// Gate for the admin area. Role is verified against the backend (GET /auth/me), the
// trusted source of truth — the backend also enforces admin on every /admin/* endpoint.
// Non-admins are redirected to the standard app.
function RequireAdmin({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const [role, setRole] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    getMe()
      .then((me) => setRole(me.role))
      .catch(() => setFailed(true));
  }, [isAuthenticated]);

  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (failed) return <Navigate to="/app/dashboard" replace />;
  if (!role) return null; // still resolving role
  return role === "admin" ? children : <Navigate to="/app/dashboard" replace />;
}

// Gate for the forecast feature. Role is verified against the backend (GET /auth/me), the
// trusted source of truth — never the client-controlled session metadata. Duration forecasting
// only covers the 3 household flexible appliances, so business accounts are redirected away
// (and the backend also returns 403 on /forecast for them). Admin is treated like household.
function RequireHousehold({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const [role, setRole] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    getMe()
      .then((me) => setRole(me.role))
      .catch(() => setFailed(true));
  }, [isAuthenticated]);

  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (failed) return <Navigate to="/app/dashboard" replace />;
  if (!role) return null; // still resolving role
  return role === "business" ? <Navigate to="/app/dashboard" replace /> : children;
}

// Post-login/registration landing. Role is fetched from the backend (GET /auth/me) —
// the trusted source of truth — never from the client-controlled session metadata.
function PostAuthRedirect() {
  const { isAuthenticated, loading } = useAuth();
  const [role, setRole] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    getMe()
      .then((me) => setRole(me.role))
      .catch(() => setFailed(true));
  }, [isAuthenticated]);

  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  // On failure, fall back to the standard app so users aren't stranded.
  if (failed) return <Navigate to="/app/dashboard" replace />;
  if (!role) return null; // still resolving role
  return <Navigate to={role === "admin" ? "/admin/dashboard" : "/app/dashboard"} replace />;
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
              <Route path="forecast" element={<RequireHousehold><ForecastTab /></RequireHousehold>} />
              <Route path="optimize" element={<OptimizeTab />} />
              <Route path="guide" element={<GuideTab />} />
              <Route path="feedback" element={<FeedbackTab />} />
              <Route path="profile" element={<ProfileTab />} />
            </Route>

            {/* Post-auth landing: routes by role (admin → /admin, others → /app). */}
            <Route path="/dashboard" element={<RequireAuth><PostAuthRedirect /></RequireAuth>} />

            {/* Admin area — role verified by RequireAdmin AND enforced on every backend route. */}
            <Route path="/admin" element={<RequireAdmin><AdminLayout /></RequireAdmin>}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<AdminDashboard />} />
              <Route path="feedback" element={<AdminFeedback />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="logs" element={<AdminLogs />} />
            </Route>

            <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
