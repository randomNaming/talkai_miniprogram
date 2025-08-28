// pages/dict/dict.js
const api = require('../../services/api');

Page({
  data: {
    searchText: '',
    searchResults: [],
    isSearching: false,
    recentSearches: []
  },

  onLoad: function (options) {
    this.loadRecentSearches();
    
    // Handle word parameter from vocabulary suggestions
    if (options.word) {
      const word = decodeURIComponent(options.word);
      this.setData({
        searchText: word
      });
      // Automatically search for the word
      this.searchWord(word);
    }
  },

  loadRecentSearches: function() {
    const recent = wx.getStorageSync('recent_searches') || [];
    this.setData({ recentSearches: recent });
  },

  onSearchInput: function(e) {
    this.setData({ searchText: e.detail.value });
  },

  onSearch: function() {
    const text = this.data.searchText.trim();
    if (!text) return;
    this.searchWord(text);
  },

  searchWord: function(word) {
    if (!word) return;
    
    this.setData({ 
      isSearching: true,
      searchResults: []
    });
    
    api.dict.query(word).then(result => {
      // Handle both single word and multiple results
      let results = [];
      if (result.definition) {
        // Single word result format
        results = [{
          word: word,
          definition: result.definition,
          phonetic: result.phonetic || '',
          translation: result.translation || ''
        }];
      } else if (result.results && Array.isArray(result.results)) {
        // Multiple results format  
        results = result.results;
      }
      
      this.setData({
        searchResults: results,
        isSearching: false
      });
      this.saveRecentSearch(word);
    }).catch(err => {
      console.error('Dictionary search failed:', err);
      this.setData({ 
        isSearching: false,
        searchResults: []
      });
      
      wx.showToast({
        title: '查询失败，请重试',
        icon: 'none',
        duration: 2000
      });
    });
  },

  saveRecentSearch: function(word) {
    let recent = this.data.recentSearches;
    recent = recent.filter(item => item !== word);
    recent.unshift(word);
    recent = recent.slice(0, 10);
    
    this.setData({ recentSearches: recent });
    wx.setStorageSync('recent_searches', recent);
  },

  onRecentSearchTap: function(e) {
    const word = e.currentTarget.dataset.word;
    if (word) {
      this.setData({ searchText: word });
      this.searchWord(word);
    }
  },

  onClearRecentSearches: function() {
    wx.showModal({
      title: '清空记录',
      content: '确定要清空所有搜索记录吗？',
      confirmText: '清空',
      confirmColor: '#DC3545',
      success: (res) => {
        if (res.confirm) {
          this.setData({ recentSearches: [] });
          wx.removeStorageSync('recent_searches');
          wx.showToast({
            title: '记录已清空',
            icon: 'success'
          });
        }
      }
    });
  },

  onAddToVocab: function(e) {
    const word = e.currentTarget.dataset.word;
    if (word) {
      console.log('Adding word to vocabulary:', word);
      
      // Show loading
      wx.showLoading({
        title: '添加中...',
        mask: true
      });
      
      // Call backend to add word to database
      this.addWordToDatabase(word).then(result => {
        wx.hideLoading();
        
        if (result.added_to_vocab) {
          // Also add to frontend global data to update statistics immediately
          const app = getApp();
          app.addVocabWord({
            word: word,
            source: 'lookup',
            level: 'none',
            wrong_use_count: 1,      // talkai_py兼容字段名
            right_use_count: 0,      // talkai_py兼容字段名
            isMastered: false,       // talkai_py兼容字段名
            added_date: new Date().toISOString(),  // talkai_py兼容字段名
            last_used: new Date().toISOString(),   // talkai_py兼容字段名
            definition: result.definition || ''
          });
          
          // 触发profile页面数据刷新 - 通过设置标志来通知需要刷新
          wx.setStorageSync('vocab_status_needs_refresh', true);
          
          wx.showToast({
            title: '已添加到词汇表',
            icon: 'success',
            duration: 1500
          });
          
          console.log('Vocabulary added successfully, profile data refresh triggered');
        } else {
          wx.showToast({
            title: result.message || '添加失败',
            icon: 'none',
            duration: 2000
          });
        }
      }).catch(err => {
        wx.hideLoading();
        console.error('Add to vocab failed:', err);
        wx.showToast({
          title: '添加失败，请重试',
          icon: 'none',
          duration: 2000
        });
      });
    }
  },

  /**
   * Add word to database using lookup endpoint
   */
  addWordToDatabase: function(word) {
    return new Promise((resolve, reject) => {
      const envConfig = require('../../config/env');
      const config = envConfig.getConfig();
      const apiUrl = `${config.API_BASE_URL}/dict/lookup-simple?word=${encodeURIComponent(word)}`;
      
      wx.request({
        url: apiUrl,
        method: 'GET',
        header: {
          'Content-Type': 'application/json'
        },
        success: (res) => {
          console.log('Dict lookup response:', res.statusCode, res.data);
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(new Error(res.data?.detail || 'Request failed'));
          }
        },
        fail: (err) => {
          console.error('Dict lookup request failed:', err);
          reject(new Error(err.errMsg || 'Network request failed'));
        }
      });
    });
  }
});