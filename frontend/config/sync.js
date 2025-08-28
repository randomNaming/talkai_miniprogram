// 词汇数据同步配置文件
// 用于管理前端与后端数据同步的各项参数设置

const SYNC_CONFIG = {
  // 定期同步间隔（毫秒）- 默认1分钟
  VOCAB_SYNC_INTERVAL: 60 * 1000, // 1分钟
  
  // 同步重试配置
  MAX_RETRY_ATTEMPTS: 3,           // 最大重试次数
  RETRY_DELAY: 5000,               // 重试间隔（毫秒）
  
  // 缓存失效时间（毫秒）- 如果超过此时间没有同步，强制刷新
  CACHE_EXPIRE_TIME: 5 * 60 * 1000, // 5分钟
  
  // 数据变化检测阈值 - 当词汇数量变化超过此值时立即同步
  CHANGE_THRESHOLD: 5,
  
  // 同步触发条件
  SYNC_TRIGGERS: {
    APP_LAUNCH: true,              // 应用启动时同步
    APP_RESUME: true,              // 应用从后台恢复时同步
    VOCAB_OPERATION: true,         // 词汇操作后同步
    PERIODIC: true,                // 定期自动同步
    MANUAL: true                   // 手动触发同步
  },
  
  // 同步日志配置
  ENABLE_SYNC_LOG: true,           // 是否启用同步日志
  LOG_LEVEL: 'info',               // 日志级别: debug, info, warn, error
  
  // 离线模式配置
  OFFLINE_MODE: {
    ENABLE_OFFLINE_CACHE: true,    // 启用离线缓存
    MAX_OFFLINE_OPERATIONS: 100    // 最大离线操作数
  },
  
  // API端点配置
  API_ENDPOINTS: {
    VOCAB_LIST: '/user/vocab-list-simple',           // 获取词汇列表
    VOCAB_STATUS: '/user/profile/vocab-status-simple' // 获取词汇状态统计
  }
};

// 根据环境或用户设置动态调整配置
const adjustConfigForEnvironment = () => {
  try {
    // 检查是否在开发环境
    const isDevelopment = wx.getSystemInfoSync().platform === 'devtools';
    
    if (isDevelopment) {
      // 开发环境下缩短同步间隔以便调试
      SYNC_CONFIG.VOCAB_SYNC_INTERVAL = 30 * 1000; // 30秒
      SYNC_CONFIG.ENABLE_SYNC_LOG = true;
      SYNC_CONFIG.LOG_LEVEL = 'debug';
      
      console.log('[SyncConfig] 开发环境配置已启用');
    }
  } catch (e) {
    console.warn('[SyncConfig] 环境检测失败:', e);
  }
};

// 从本地存储读取用户自定义配置
const loadUserConfig = () => {
  try {
    const userConfig = wx.getStorageSync('talkai_sync_config');
    if (userConfig) {
      // 合并用户自定义配置
      Object.assign(SYNC_CONFIG, JSON.parse(userConfig));
      console.log('[SyncConfig] 用户配置已加载');
    }
  } catch (e) {
    console.warn('[SyncConfig] 用户配置加载失败:', e);
  }
};

// 保存用户自定义配置
const saveUserConfig = (config) => {
  try {
    wx.setStorageSync('talkai_sync_config', JSON.stringify(config));
    Object.assign(SYNC_CONFIG, config);
    console.log('[SyncConfig] 用户配置已保存');
  } catch (e) {
    console.error('[SyncConfig] 用户配置保存失败:', e);
  }
};

// 初始化配置
const initConfig = () => {
  adjustConfigForEnvironment();
  loadUserConfig();
  
  console.log('[SyncConfig] 配置初始化完成:', {
    syncInterval: SYNC_CONFIG.VOCAB_SYNC_INTERVAL / 1000 + 's',
    enableLog: SYNC_CONFIG.ENABLE_SYNC_LOG,
    triggers: SYNC_CONFIG.SYNC_TRIGGERS
  });
};

// 导出配置和方法
module.exports = {
  SYNC_CONFIG,
  saveUserConfig,
  initConfig
};