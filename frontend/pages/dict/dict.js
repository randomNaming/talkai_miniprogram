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

    this.setData({ isSearching: true });
    
    api.searchDict(text, 10).then(result => {
      this.setData({
        searchResults: result.results || [],
        isSearching: false
      });
      this.saveRecentSearch(text);
    }).catch(err => {
      console.error('Dictionary search failed:', err);
      this.setData({ isSearching: false });
    });
  },

  saveRecentSearch: function(word) {
    let recent = this.data.recentSearches;
    recent = recent.filter(item => item !== word);
    recent.unshift(word);
    recent = recent.slice(0, 10);
    
    this.setData({ recentSearches: recent });
    wx.setStorageSync('recent_searches', recent);
  }
});