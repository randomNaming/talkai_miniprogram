// 词汇学习进度详情页面
const api = require('../../services/api');

Page({
  data: {
    basicStats: {
      total_vocab_count: 0,
      mastered_vocab_count: 0,
      unmastered_vocab_count: 0,
      mastery_percentage: 0
    },
    weeklyProgress: [],
    monthlyStats: {
      newWords: 0,
      reviewWords: 0,
      masteredWords: 0,
      month_name: ''
    },
    isLoading: false,
    maxNewWords: 1,
    maxMasteredWords: 1
  },

  onLoad: function (options) {
    this.loadProgressData();
  },

  onShow: function () {
    // 每次显示时刷新数据
    this.loadProgressData();
  },

  /**
   * 加载学习进度数据
   */
  loadProgressData: async function() {
    if (this.data.isLoading) return;
    
    this.setData({ isLoading: true });

    try {
      // 获取学习进度数据
      const response = await api.getLearningProgress();
      
      if (response.success) {
        const { basic_stats, weekly_progress, monthly_stats } = response;
        
        // 计算图表最大值（用于条形图高度计算）
        let maxNewWords = 1;
        let maxMasteredWords = 1;
        
        if (weekly_progress && weekly_progress.length > 0) {
          maxNewWords = Math.max(...weekly_progress.map(item => item.new_words || 0)) || 1;
          maxMasteredWords = Math.max(...weekly_progress.map(item => item.mastered_words || 0)) || 1;
        }

        this.setData({
          basicStats: basic_stats || this.data.basicStats,
          weeklyProgress: weekly_progress || [],
          monthlyStats: monthly_stats || this.data.monthlyStats,
          maxNewWords: maxNewWords,
          maxMasteredWords: maxMasteredWords
        });

        console.log('学习进度数据加载成功');
      } else {
        throw new Error('获取学习进度失败');
      }
    } catch (error) {
      console.error('加载学习进度数据失败:', error);
      
      // 显示错误提示
      wx.showToast({
        title: '数据加载失败',
        icon: 'none',
        duration: 2000
      });

      // 使用默认数据
      this.setDefaultData();
    } finally {
      this.setData({ isLoading: false });
    }
  },

  /**
   * 设置默认数据（网络错误时使用）
   */
  setDefaultData: function() {
    const now = new Date();
    const defaultWeeklyProgress = [];
    
    // 生成默认的7天数据
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      defaultWeeklyProgress.push({
        date: date.toISOString().split('T')[0],
        new_words: Math.floor(Math.random() * 5),
        mastered_words: Math.floor(Math.random() * 3),
        day_name: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][date.getDay()]
      });
    }

    this.setData({
      basicStats: {
        total_vocab_count: 0,
        mastered_vocab_count: 0,
        unmastered_vocab_count: 0,
        mastery_percentage: 0
      },
      weeklyProgress: defaultWeeklyProgress,
      monthlyStats: {
        newWords: 0,
        reviewWords: 0,
        masteredWords: 0,
        month_name: now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
      },
      maxNewWords: 5,
      maxMasteredWords: 3
    });
  },

  /**
   * 计算条形图高度百分比
   */
  getBarHeight: function(value, maxValue) {
    if (!value || !maxValue || maxValue === 0) return 0;
    return Math.max((value / maxValue) * 80, 5); // 最小高度5%，最大80%
  },

  /**
   * 刷新进度数据
   */
  refreshProgress: function() {
    this.loadProgressData();
    
    // 触发下拉刷新动画
    wx.showNavigationBarLoading();
    setTimeout(() => {
      wx.hideNavigationBarLoading();
    }, 1000);
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh: function() {
    this.refreshProgress();
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  }
});