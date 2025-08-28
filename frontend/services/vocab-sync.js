/**
 * 词汇数据同步管理器
 * 功能：
 * 1. 前端集成：将API集成到前端，替代现有缓存机制
 * 2. 定期同步：实现前端与后端的定期数据同步
 * 3. 缓存策略：词汇更新后主动刷新缓存
 */

const api = require('./api');
const storage = require('../utils/storage');
const { SYNC_CONFIG, initConfig } = require('../config/sync');

class VocabSyncManager {
  constructor() {
    this.isInitialized = false;
    this.syncTimer = null;
    this.lastSyncTime = null;
    this.syncInProgress = false;
    this.retryCount = 0;
    
    // 初始化配置
    initConfig();
    
    console.log('[VocabSync] 词汇同步管理器初始化');
  }

  /**
   * 初始化同步管理器
   */
  init() {
    if (this.isInitialized) {
      console.log('[VocabSync] 同步管理器已初始化');
      return;
    }

    try {
      // 读取上次同步时间
      this.lastSyncTime = storage.getLastSyncTime();
      
      // 启动定期同步
      if (SYNC_CONFIG.SYNC_TRIGGERS.PERIODIC) {
        this.startPeriodicSync();
      }
      
      this.isInitialized = true;
      console.log('[VocabSync] 同步管理器初始化完成');
      
      // 如果启用了应用启动同步，立即执行一次同步
      if (SYNC_CONFIG.SYNC_TRIGGERS.APP_LAUNCH) {
        this.syncVocabulary('app_launch');
      }
      
    } catch (error) {
      console.error('[VocabSync] 初始化失败:', error);
    }
  }

  /**
   * 启动定期同步
   */
  startPeriodicSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
    }

    this.syncTimer = setInterval(() => {
      if (SYNC_CONFIG.SYNC_TRIGGERS.PERIODIC && !this.syncInProgress) {
        this.syncVocabulary('periodic');
      }
    }, SYNC_CONFIG.VOCAB_SYNC_INTERVAL);

    console.log(`[VocabSync] 定期同步已启动，间隔: ${SYNC_CONFIG.VOCAB_SYNC_INTERVAL / 1000}秒`);
  }

  /**
   * 停止定期同步
   */
  stopPeriodicSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
      console.log('[VocabSync] 定期同步已停止');
    }
  }

  /**
   * 检查是否需要同步
   */
  shouldSync(trigger = 'manual') {
    // 如果同步正在进行中，跳过
    if (this.syncInProgress) {
      return false;
    }

    // 检查触发条件是否启用
    if (!SYNC_CONFIG.SYNC_TRIGGERS[trigger.toUpperCase()]) {
      return false;
    }

    // 检查缓存是否过期
    const now = Date.now();
    if (this.lastSyncTime) {
      const timeSinceLastSync = now - this.lastSyncTime;
      if (timeSinceLastSync < SYNC_CONFIG.CACHE_EXPIRE_TIME && trigger === 'periodic') {
        return false;
      }
    }

    return true;
  }

  /**
   * 执行词汇同步
   */
  async syncVocabulary(trigger = 'manual') {
    if (!this.shouldSync(trigger)) {
      if (SYNC_CONFIG.ENABLE_SYNC_LOG) {
        console.log(`[VocabSync] 跳过同步，触发器: ${trigger}`);
      }
      return false;
    }

    this.syncInProgress = true;
    const startTime = Date.now();
    
    try {
      if (SYNC_CONFIG.ENABLE_SYNC_LOG) {
        console.log(`[VocabSync] 开始同步，触发器: ${trigger}`);
      }

      // 获取最新的词汇列表和状态
      const [vocabListResult, vocabStatusResult] = await Promise.all([
        api.getVocabList(),
        api.getVocabStatus()
      ]);

      // 更新本地缓存
      const app = getApp();
      if (vocabListResult && vocabListResult.vocabulary) {
        // 更新全局数据
        app.globalData.vocabList = vocabListResult.vocabulary;
        
        // 保存到本地存储
        storage.setVocabList(vocabListResult.vocabulary);
        
        if (SYNC_CONFIG.ENABLE_SYNC_LOG) {
          console.log(`[VocabSync] 词汇列表已更新: ${vocabListResult.total_count}个词汇`);
        }
      }

      // 更新词汇状态统计
      if (vocabStatusResult) {
        app.globalData.vocabStats = vocabStatusResult;
        
        if (SYNC_CONFIG.ENABLE_SYNC_LOG) {
          console.log(`[VocabSync] 词汇统计已更新:`, vocabStatusResult);
        }
      }

      // 记录同步时间
      this.lastSyncTime = Date.now();
      storage.setLastSyncTime(this.lastSyncTime);
      
      // 重置重试计数
      this.retryCount = 0;
      
      const duration = Date.now() - startTime;
      console.log(`[VocabSync] 同步完成，耗时: ${duration}ms，触发器: ${trigger}`);
      
      // 触发同步完成事件
      this.onSyncComplete(trigger, true, vocabListResult);
      
      return true;

    } catch (error) {
      console.error(`[VocabSync] 同步失败，触发器: ${trigger}`, error);
      
      // 处理重试逻辑
      this.retryCount++;
      if (this.retryCount < SYNC_CONFIG.MAX_RETRY_ATTEMPTS) {
        setTimeout(() => {
          console.log(`[VocabSync] 重试同步 (${this.retryCount}/${SYNC_CONFIG.MAX_RETRY_ATTEMPTS})`);
          this.syncVocabulary(trigger);
        }, SYNC_CONFIG.RETRY_DELAY);
      } else {
        console.error('[VocabSync] 同步重试次数已达上限');
        this.retryCount = 0;
      }
      
      this.onSyncComplete(trigger, false, null, error);
      return false;
      
    } finally {
      this.syncInProgress = false;
    }
  }

  /**
   * 词汇操作后的缓存刷新
   */
  async refreshAfterVocabOperation(operation = 'unknown') {
    if (!SYNC_CONFIG.SYNC_TRIGGERS.VOCAB_OPERATION) {
      return false;
    }

    console.log(`[VocabSync] 词汇操作后刷新缓存: ${operation}`);
    
    // 延迟一小段时间以确保后端处理完成
    setTimeout(async () => {
      await this.syncVocabulary('vocab_operation');
    }, 1000);
    
    return true;
  }

  /**
   * 应用从后台恢复时的同步
   */
  async syncOnAppResume() {
    if (!SYNC_CONFIG.SYNC_TRIGGERS.APP_RESUME) {
      return false;
    }

    console.log('[VocabSync] 应用恢复，检查同步');
    return await this.syncVocabulary('app_resume');
  }

  /**
   * 强制同步（忽略所有限制）
   */
  async forceSync() {
    console.log('[VocabSync] 强制同步');
    const originalSyncInProgress = this.syncInProgress;
    this.syncInProgress = false; // 临时清除同步标志
    
    try {
      const result = await this.syncVocabulary('manual');
      return result;
    } finally {
      this.syncInProgress = originalSyncInProgress;
    }
  }

  /**
   * 获取同步状态信息
   */
  getSyncStatus() {
    return {
      isInitialized: this.isInitialized,
      syncInProgress: this.syncInProgress,
      lastSyncTime: this.lastSyncTime,
      nextSyncTime: this.lastSyncTime ? this.lastSyncTime + SYNC_CONFIG.VOCAB_SYNC_INTERVAL : null,
      retryCount: this.retryCount,
      config: SYNC_CONFIG
    };
  }

  /**
   * 同步完成回调（可被重写）
   */
  onSyncComplete(trigger, success, data, error) {
    // 可以在此处添加自定义的同步完成处理逻辑
    if (SYNC_CONFIG.ENABLE_SYNC_LOG) {
      if (success) {
        console.log(`[VocabSync] 同步成功回调，触发器: ${trigger}`, data?.total_count || 0);
      } else {
        console.error(`[VocabSync] 同步失败回调，触发器: ${trigger}`, error);
      }
    }

    // 发送自定义事件，供其他组件监听
    try {
      wx.getApp && wx.getApp().emitVocabSyncEvent && wx.getApp().emitVocabSyncEvent({
        type: success ? 'sync_success' : 'sync_error',
        trigger,
        data,
        error
      });
    } catch (e) {
      // 忽略事件发送失败
    }
  }

  /**
   * 销毁同步管理器
   */
  destroy() {
    this.stopPeriodicSync();
    this.syncInProgress = false;
    this.isInitialized = false;
    console.log('[VocabSync] 同步管理器已销毁');
  }
}

// 创建全局单例
const vocabSyncManager = new VocabSyncManager();

module.exports = {
  VocabSyncManager,
  vocabSyncManager
};