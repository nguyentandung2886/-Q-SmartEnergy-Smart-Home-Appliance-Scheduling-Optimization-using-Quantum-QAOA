import { motion } from "framer-motion";

/**
 * Gemini storytelling: button to request a plain-language explanation of the
 * optimization result, with a streaming loading pulse and the result card.
 */
export default function ExplainSection({ explainText, explainLoading, onExplain }) {
  return (
    <div style={{ marginTop: "1rem" }}>
      <motion.button
        className="btn-explain"
        onClick={onExplain}
        disabled={explainLoading}
        whileHover={{ scale: explainLoading ? 1 : 1.03 }}
        whileTap={{ scale: explainLoading ? 1 : 0.97 }}
      >
        Hệ thống lấy insight
      </motion.button>

      {explainLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.2 }}
          style={{
            marginTop: "0.75rem",
            color: "var(--indigo)",
            fontSize: "0.85rem",
          }}
        >
          Hệ thống đang lấy insight và đưa ra khuyến nghị...
        </motion.div>
      )}

      {explainText && (
        <div className="explain-card">
          <strong>Phân tích kết quả</strong>
          <p style={{ marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
            {explainText}
          </p>
        </div>
      )}
    </div>
  );
}
