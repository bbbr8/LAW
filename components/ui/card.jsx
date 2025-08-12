import React from "react";

export function Card({ className = "", ...props }) {
  return <div {...props} className={`rounded-md border bg-white ${className}`} />;
}

export function CardContent({ className = "", ...props }) {
  return <div {...props} className={className} />;
}
