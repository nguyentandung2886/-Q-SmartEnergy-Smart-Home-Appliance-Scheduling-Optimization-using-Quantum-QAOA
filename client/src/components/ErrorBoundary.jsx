import { Component } from "react";

/**
 * Catches render-time errors anywhere below it so a single component crash
 * shows a friendly fallback instead of white-screening the whole app.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Render error caught by ErrorBoundary:", error, info);
  }

  handleReload = () => {
    this.setState({ hasError: false });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <h2>Đã xảy ra lỗi hiển thị</h2>
          <p>Ứng dụng gặp sự cố không mong muốn. Vui lòng tải lại trang.</p>
          <button className="primary" onClick={this.handleReload}>
            Tải lại
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
