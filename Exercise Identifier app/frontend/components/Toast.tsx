"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, CheckCircle, X } from "lucide-react";
import { useEffect } from "react";

interface ToastProps {
  message: string;
  visible: boolean;
  onDismiss: () => void;
  variant?: "error" | "success";
}

export default function Toast({
  message,
  visible,
  onDismiss,
  variant = "error",
}: ToastProps) {
  useEffect(() => {
    if (visible) {
      const timer = setTimeout(onDismiss, variant === "success" ? 3000 : 6000);
      return () => clearTimeout(timer);
    }
  }, [visible, onDismiss, variant]);

  const Icon = variant === "success" ? CheckCircle : AlertCircle;
  const iconColor =
    variant === "success" ? "text-emerald-400" : "text-red-400";
  const borderColor =
    variant === "success" ? "border-emerald-500/20" : "border-red-500/20";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed bottom-6 left-1/2 z-[60] -translate-x-1/2"
        >
          <div
            className={`glass-card flex items-center gap-3 rounded-2xl px-5 py-3.5 shadow-2xl ${borderColor}`}
          >
            <Icon className={`h-5 w-5 flex-shrink-0 ${iconColor}`} />
            <p className="text-sm text-neutral-300 max-w-sm">{message}</p>
            <button
              onClick={onDismiss}
              className="ml-2 flex-shrink-0 rounded-lg p-1 text-neutral-500 hover:text-neutral-300 hover:bg-white/5 transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
