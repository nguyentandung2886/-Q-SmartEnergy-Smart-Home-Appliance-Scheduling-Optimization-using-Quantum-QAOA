import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";

window.onerror = function(msg, url, line, col, error) {
  document.body.innerHTML += `<div style="color:red; background:white; position:fixed; top:0; left:0; z-index:9999; padding:20px; border:2px solid red;">${msg} <br/> ${error?.stack}</div>`;
};
window.addEventListener("unhandledrejection", function(e) {
  document.body.innerHTML += `<div style="color:red; background:white; position:fixed; top:200px; left:0; z-index:9999; padding:20px; border:2px solid red;">Unhandled Rejection: ${e.reason?.message} <br/> ${e.reason?.stack}</div>`;
});

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
