import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { AppDataProvider } from "../AppData";
import { useAuth } from "../AuthContext";
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
              {TABS.map((t) => (
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
