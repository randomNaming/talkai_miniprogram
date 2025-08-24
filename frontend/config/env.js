// Environment configuration for TalkAI Mini Program
// This file handles different API endpoints for development and production

// Get current environment
// In WeChat Mini Program, we can check if running in development tools
function getEnvironment() {
  // Check if running in WeChat Developer Tools
  const systemInfo = wx.getSystemInfoSync();
  const isDevelopment = systemInfo.platform === 'devtools' || 
                       systemInfo.environment === 'dev' ||
                       wx.canIUse('getAccountInfoSync') && 
                       wx.getAccountInfoSync().miniProgram.envVersion === 'develop';
  
  return isDevelopment ? 'development' : 'production';
}

// Environment configurations
const ENV_CONFIG = {
  development: {
    API_BASE_URL: 'http://localhost:8000/api/v1',
    DEBUG: true,
    USE_MOCK: false, // Set to true to use mock responses in development
    LOG_LEVEL: 'debug'
  },
  production: {
    API_BASE_URL: 'https://api.jimingge.net/api/v1',
    DEBUG: false,
    USE_MOCK: false,
    LOG_LEVEL: 'error'
  }
};

// Get current environment config
function getConfig() {
  const env = getEnvironment();
  const config = ENV_CONFIG[env];
  
  console.log(`[ENV] Current environment: ${env}`);
  console.log(`[ENV] API Base URL: ${config.API_BASE_URL}`);
  
  return {
    ...config,
    ENVIRONMENT: env
  };
}

// Export configuration
module.exports = {
  getConfig,
  getEnvironment,
  ENV_CONFIG
};