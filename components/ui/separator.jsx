import React from "react";

export function Separator({ className = "", ...props }) {
  return <hr {...props} className={className} />;
}
