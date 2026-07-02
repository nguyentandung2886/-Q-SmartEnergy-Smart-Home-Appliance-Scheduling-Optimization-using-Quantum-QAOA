import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppData } from "../AppData";

// Bell + unread badge + dropdown, plus transient toasts for freshly-raised reminders.
// Styles are inline (self-contained) using the app's CSS custom properties so it themes with
// the rest of the shell. Every message is a *simulated* device reminder — no hardware control.
export default function NotificationCenter() {
  const { notifications, markAllRead } = useAppData();
  const [open, setOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  const seenRef = useRef(null); // ids already turned into toasts (null = not yet initialised)

  const unread = notifications.filter((n) => !n.read).length;

  // Surface each *new* notification as a toast that auto-dismisses. On first render we seed the
  // seen-set with existing history so a page load doesn't replay a burst of old toasts.
  useEffect(() => {
    if (seenRef.current === null) {
      seenRef.current = new Set(notifications.map((n) => n.id));
      return;
    }
    const fresh = notifications.filter((n) => !seenRef.current.has(n.id));
    if (!fresh.length) return;
    fresh.forEach((n) => seenRef.current.add(n.id));
    setToasts((prev) => [...fresh, ...prev]);
    fresh.forEach((n) =>
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== n.id)), 6000)
    );
  }, [notifications]);

  return (
    <div style={{ position: "relative" }}>
      <button
        className="theme-toggle"
        aria-label="Thông báo"
        onClick={() => setOpen((o) => !o)}
        style={{ position: "relative" }}
      >
        🔔
        {unread > 0 && (
          <span
            style={{
              position: "absolute", top: -6, right: -6, minWidth: 18, height: 18,
              padding: "0 5px", borderRadius: 9, background: "var(--accent)", color: "#fff",
              fontSize: "0.68rem", fontWeight: 600, lineHeight: "18px", textAlign: "center",
            }}
          >
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            style={{
              position: "absolute", right: 0, top: "calc(100% + 8px)", width: 320, zIndex: 50,
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: "var(--radius-sm)", boxShadow: "0 8px 28px rgba(0,0,0,0.14)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "0.7rem 0.9rem", borderBottom: "1px solid var(--border)",
              }}
            >
              <strong style={{ fontSize: "0.9rem", color: "var(--text-strong)" }}>Thông báo</strong>
              {unread > 0 && (
                <button
                  onClick={markAllRead}
                  style={{
                    background: "none", border: "none", cursor: "pointer",
                    color: "var(--accent)", fontSize: "0.78rem",
                  }}
                >
                  Đánh dấu đã đọc
                </button>
              )}
            </div>

            <div style={{ maxHeight: 320, overflowY: "auto" }}>
              {notifications.length === 0 ? (
                <p style={{ padding: "1.2rem 0.9rem", color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center" }}>
                  Chưa có thông báo nào.
                </p>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    style={{
                      padding: "0.65rem 0.9rem", borderBottom: "1px solid var(--border)",
                      fontSize: "0.83rem", lineHeight: 1.45,
                      color: n.read ? "var(--text-muted)" : "var(--text)",
                      background: n.read ? "transparent" : "var(--accent-soft)",
                    }}
                  >
                    {n.text}
                    <div style={{ marginTop: 3, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                      {n.at.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Transient toasts, anchored to the viewport corner */}
      <div style={{ position: "fixed", top: 76, right: 20, display: "flex", flexDirection: "column", gap: 8, zIndex: 60, pointerEvents: "none" }}>
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 40 }}
              transition={{ duration: 0.2 }}
              style={{
                width: 300, padding: "0.7rem 0.9rem", background: "var(--surface)",
                border: "1px solid var(--border)", borderLeft: "3px solid var(--accent)",
                borderRadius: "var(--radius-sm)", boxShadow: "0 8px 28px rgba(0,0,0,0.16)",
                fontSize: "0.83rem", lineHeight: 1.45, color: "var(--text)",
              }}
            >
              {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
