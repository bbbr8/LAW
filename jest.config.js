module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/components/ui/(.*)$': '<rootDir>/__mocks__/ui/$1',
  },
  transform: {
    '^.+\\.[tj]sx?$': 'babel-jest',
  },
};
