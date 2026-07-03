import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { AppDataProvider } from "../AppData";
import { useAuth } from "../AuthContext";
import { getMe } from "../api";
import ThemeToggle from "./ThemeToggle";
import NotificationCenter from "./NotificationCenter";

const TABS = [
  { to: "/app/dashboard", label: "Tổng quan" },
  { to: "/app/devices", label: "Thiết bị" },
  { to: "/app/forecast", label: "Dự báo" },
  { to: "/app/optimize", label: "Tối ưu hóa" },
  { to: "/app/guide", label: "Hướng dẫn" },
  { to: "/app/feedback", label: "Góp ý" },
  { to: "/app/profile", label: "Hồ sơ" },
];

export default function AppLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  // Role from the backend (GET /auth/me), the trusted source. Business accounts don't get the
  // Dự báo tab — duration forecasting only covers household appliances (see RequireHousehold in App.jsx).
  const [role, setRole] = useState(null);

  useEffect(() => {
    getMe()
      .then((me) => setRole(me.role))
      .catch(() => setRole(null));
  }, []);

  const tabs = TABS.filter((t) => t.to !== "/app/forecast" || role !== "business");

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <AppDataProvider>
      <div className="app-shell">
        <header className="navbar">
          <div className="navbar-inner">
            <div className="brand" onClick={() => navigate("/app/dashboard")}>
              <span className="brand-mark" />
              Q-SmartEnergy
            </div>

            <nav className="nav-tabs">
              {tabs.map((t) => (
                <NavLink
                  key={t.to}
                  to={t.to}
                  className={({ isActive }) => "nav-tab" + (isActive ? " nav-tab--active" : "")}
                >
                  {t.label}
                </NavLink>
              ))}
            </nav>

            <div className="navbar-actions">
              <NotificationCenter />
              <ThemeToggle />
              <button className="btn nav-ghost" onClick={() => navigate("/history")}>Lịch sử</button>
              <button className="btn nav-ghost" onClick={handleLogout}>Đăng xuất</button>
            </div>
          </div>
        </header>

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </AppDataProvider>
  );
}
