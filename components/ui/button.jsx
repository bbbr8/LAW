import React from "react";

export function Button({ className = "", ...props }) {
  return (
    <button
      {...props}
      className={`px-4 py-2 rounded-md border bg-white hover:bg-slate-50 ${className}`}
    />
  );
}
