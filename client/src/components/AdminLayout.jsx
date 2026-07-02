import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import ThemeToggle from "./ThemeToggle";

const TABS = [
  { to: "/admin/dashboard", label: "Tổng quan" },
  { to: "/admin/feedback", label: "Đánh giá" },
  { to: "/admin/users", label: "Người dùng" },
  { to: "/admin/logs", label: "Nhật ký" },
];

export default function AdminLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="navbar">
        <div className="navbar-inner">
          <div className="brand" onClick={() => navigate("/admin/dashboard")}>
            <span className="brand-mark" />
            Q-SmartEnergy · Quản trị
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
            <ThemeToggle />
            <button className="btn nav-ghost" onClick={handleLogout}>Đăng xuất</button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
