// Increase timeout for all tests
jest.setTimeout(10000);

// Mock the logger to prevent console output during tests
jest.mock('../utils/logger', () => ({
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn()
}));

// Global setup
beforeAll(async () => {
    // Any global setup needed before running tests
});

// Global teardown
afterAll(async () => {
    // Any global cleanup needed after running tests
}); 