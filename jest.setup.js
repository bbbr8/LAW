import '@testing-library/jest-dom';
import React from 'react';

global.crypto = { randomUUID: () => '0000-0000' };

jest.mock('framer-motion', () => ({
  motion: {
    div: React.forwardRef(({children, ...props}, ref) => <div ref={ref} {...props}>{children}</div>),
  },
}));

jest.mock('lucide-react', () => new Proxy({}, { get: () => () => null }));
