/**
 * Shared toast notification system for Clutsch.
 * Provides a showToast function and a ToastContainer component.
 * Usage: import { showToast } from '../utils/toast'; showToast("Message", "success");
 * Types: "success" | "error" | "info"
 */
let toastCallback = null;

export function registerToastHandler(callback) {
  toastCallback = callback;
}

export function showToast(message, type = "success") {
  if (toastCallback) {
    toastCallback(message, type);
  }
}

export function ToastContainer({ toast, onClear }) {
  if (!toast) return null;
  
  const typeClass = toast.type || "success";
  const bgColor = typeClass === "error" ? "#dc2626" : typeClass === "info" ? "#3b82f6" : "#059669";
  
  return (
    <div className="toast-container" role="alert" aria-live="polite">
      <div 
        className="toast" 
        style={{ backgroundColor: bgColor, color: "white", padding: "12px 24px", borderRadius: "8px", boxShadow: "0 4px 12px rgba(0,0,0,0.2)" }}
        onClick={onClear}
      >
        {toast.message}
      </div>
    </div>
  );
}