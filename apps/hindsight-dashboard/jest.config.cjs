/** @type {import('jest').Config} */
module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/src'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  transform: {
    '^.+\\.[jt]sx?$': 'babel-jest',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  testMatch: ['**/?(*.)+(test|spec).[jt]s?(x)'],
  extensionsToTreatAsEsm: ['.jsx', '.tsx'],
  coverageReporters: ['text', 'html'],
  coveragePathIgnorePatterns: [
    '<rootDir>/src/api/authService.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 0.80,
      functions: 0.90,
      lines: 1.0,
      statements: 0.90,
    },
  },
};
