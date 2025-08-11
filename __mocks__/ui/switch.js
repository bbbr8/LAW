import React from 'react';
export const Switch = ({checked, onCheckedChange}) => (
  <input type="checkbox" checked={checked} onChange={e=>onCheckedChange?.(e.target.checked)} />
);
