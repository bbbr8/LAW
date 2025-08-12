import React from "react";

export function Textarea({ className = "", ...props }) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-md border px-3 py-2 text-sm ${className}`}
    />
  );
}
