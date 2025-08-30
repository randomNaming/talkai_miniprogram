// pages/vocab/vocab.js
const app = getApp();
const api = require('../../services/api');

Page({
  data: {
    vocabList: [],
    searchText: '',
    totalWords: 0,
    masteredWords: 0,
    learningWords: 0,
    progressPercentage: 0,
    // 学习进度统计
    weeklyProgress: [],
    monthlyStats: {
      newWords: 0,
      reviewWords: 0,
      masteredWords: 0
    }
  },

  onLoad: function (options) {
    this.loadVocabList();
    // 加载学习进度数据
    this.loadLearningProgress();
  },

  onShow: function () {
    this.loadVocabList();
    // 每次显示时刷新学习进度
    this.loadLearningProgress();
  },

  loadVocabList: function() {
    // 开发环境使用模拟数据
    const isDevelopment = wx.getSystemInfoSync && wx.getSystemInfoSync().platform === 'devtools';
    
    if (isDevelopment) {
      console.log('[VocabPage] 开发环境：使用本地缓存数据，过滤最近词汇');
      
      // 使用app全局数据中的词汇列表，过滤出改错和查词的词汇
      const cachedVocab = app.globalData.vocabList || [];
      const recentVocab = cachedVocab.filter(item => {
        return item.source === 'chat_correction' || item.source === 'lookup';
      });
      
      this.setData({
        vocabList: recentVocab,
        totalWords: 441,
        masteredWords: 15,
        learningWords: 426,
        progressPercentage: 3
      });
      
      console.log('[VocabPage] 开发环境显示最近词汇数量:', recentVocab.length);
      return;
    }
    
    // 生产环境正常加载
    this.loadRecentVocabulary();
    
    const vocabStats = app.globalData.vocabStats;
    const totalWords = vocabStats ? vocabStats.total_vocab_count : 0;
    const masteredWords = vocabStats ? vocabStats.mastered_vocab_count : 0;
    const learningWords = vocabStats ? vocabStats.unmastered_vocab_count : 0;
    const progressPercentage = totalWords > 0 ? Math.round((masteredWords / totalWords) * 100) : 0;
    
    this.setData({
      totalWords: totalWords,
      masteredWords: masteredWords,
      learningWords: learningWords,
      progressPercentage: progressPercentage
    });
    
    if (!vocabStats || this.shouldRefreshData()) {
      this.refreshVocabData();
    }
  },

  // 加载最近添加的词汇（AI改错和词典查词）
  loadRecentVocabulary: function() {
    // 开发环境直接使用模拟数据，避免认证问题
    const isDevelopment = wx.getSystemInfoSync && wx.getSystemInfoSync().platform === 'devtools';
    
    if (isDevelopment) {
      console.log('[VocabPage] 开发环境：使用模拟词汇数据');
      this.setData({
        vocabList: [
          { word: 'example', source: 'chat_correction', added_date: '2025-08-30', isMastered: false },
          { word: 'development', source: 'lookup', added_date: '2025-08-30', isMastered: false }
        ]
      });
      return;
    }
    
    console.log('[VocabPage] 加载最近词汇（AI改错和词典查词）');
    
    // 生产环境使用真实API
    api.learningVocab.getList({
      source: 'chat_correction,lookup',
      limit: 5
    }).then(recentVocab => {
      const filteredVocab = recentVocab.filter(item => {
        return item.source === 'chat_correction' || item.source === 'lookup';
      }).map(item => {
        return {
          word: item.word,
          source: item.source,
          added_date: item.added_date,
          isMastered: item.is_mastered,
          right_use_count: item.right_use_count,
          wrong_use_count: item.wrong_use_count,
          last_used: item.last_used
        };
      });
      
      this.setData({
        vocabList: filteredVocab
      });
      
    }).catch(error => {
      console.error('[VocabPage] 加载最近词汇失败:', error);
      this.setData({ vocabList: [] });
    });
  },

  // 检查是否需要刷新数据
  shouldRefreshData: function() {
    const lastSyncTime = app.globalData.lastSyncTime;
    if (!lastSyncTime) return true;
    
    // 如果超过5分钟没有同步，强制刷新
    const fiveMinutes = 5 * 60 * 1000;
    return (Date.now() - lastSyncTime) > fiveMinutes;
  },

  // 获取详细学习进度数据
  loadLearningProgress: async function() {
    try {
      const response = await api.getLearningProgress();
      if (response.success) {
        this.setData({
          weeklyProgress: response.weekly_progress || [],
          monthlyStats: response.monthly_stats || {
            newWords: 0,
            reviewWords: 0,
            masteredWords: 0
          }
        });
      }
    } catch (error) {
      console.error('获取学习进度失败:', error);
    }
  },

  // 跳转到详细进度页面
  goToProgressView: function() {
    wx.navigateTo({
      url: '/pages/vocab/progress-view'
    });
  },

  // 刷新词汇数据
  refreshVocabData: function() {
    const vocabSyncManager = app.globalData.vocabSyncManager;
    if (vocabSyncManager) {
      console.log('[VocabPage] 触发词汇数据同步');
      vocabSyncManager.syncVocabulary('manual').then(success => {
        if (success) {
          // 同步成功，重新加载数据
          this.loadVocabList();
        }
      }).catch(error => {
        console.error('[VocabPage] 数据同步失败:', error);
      });
    }
  },

  // 手动强制刷新（下拉刷新）
  onPullDownRefresh: function() {
    console.log('[VocabPage] 用户下拉刷新');
    
    this.refreshVocabData();
    
    // 延迟停止下拉刷新动画
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  },

  onSearchInput: function(e) {
    this.setData({
      searchText: e.detail.value
    });
  },

  onSearch: function() {
    // Implement search functionality
  },

  onVocabTap: function(e) {
    const vocab = e.currentTarget.dataset.vocab;
    // Navigate to vocab detail page
  },

  onAddVocab: function() {
    wx.showModal({
      title: '添加词汇',
      content: '请在对话中练习英语，遇到生词时系统会自动添加到词汇表',
      showCancel: false
    });
  }
});