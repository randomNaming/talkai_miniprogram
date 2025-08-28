
------------
  关键实现特点：

  - 错误类型过滤：只保存 "translation" 和 "vocabulary" 类型的错误，过滤掉 "grammar" 和
  "collocation"
  - 保守策略：如果输入有中文或有值得学习的单词，正确使用词汇列表为空
  - "right_use"不新增：right_use 类型不会添加新词汇，只更新现有词汇
  - 简单词过滤：过滤掉简单词汇，避免统计无意义的词汇
  - 完整的异步处理：支持异步词汇更新，不阻塞用户对话

后端使用SQLite数据库存储词汇，而talkai_py使用JSON文件
  数据库位置：/Users/pean/aiproject/talkai_mini/backend/data/db/talkai.db

  talkai_py JSON格式 ↔ 后端数据库格式:
  - word ↔ word
  - source ↔ source
  - level ↔ level
  - added_date ↔ created_at
  - last_used ↔ last_reviewed
  - wrong_use_count ↔ encounter_count - correct_count
  - right_use_count ↔ correct_count
  - isMastered ↔ is_mastered

    - 数据库查询确认包含不同来源的词汇：
    - lookup - 词典查询添加
    - wrong_use - AI改错添加
    - level_vocab - 等级词汇初始化

  词汇数据库位置和格式


   1.关于UI输出逻辑，不用等到自然AI回复、AI改错、词汇推荐一起输出，而是分线程独立输出，目的  │
│   是减少用户等待输出的时间，可参考talkai_py/ui.py中的class                                  │
│   MessageProcessingThread(QThread) 和def send_message(self)。2.现在词汇推荐在对话框重复输   │
│   出3次，修改为只输出一次即可。3.关于词典搜索，现在存在的问题是：a.没有实现“如果是中文输入  │
│   ，不添加到词汇管理器；如果是英文输入，则添加”;b.词典搜索框输入中文时没有显示相应的英文结  │
│   果格式。这两个词典搜索问题的解决方案请参考talkai_py/ui.py:def handle_word_lookup 函数。   


-----------------
📍 用户个人词汇数据库位置和查看方法

  🗄️ 数据库位置

  /Users/pean/aiproject/talkai_mini/backend/data/db/talkai.db

  📊 数据库表结构

  - 表名: vocab_items
  - 主要字段:
    - user_id - 用户ID
    - word - 单词
    - source - 词汇来源 (level_vocab, lookup, wrong_use)
    - level - 词汇等级
    - wrong_use_count - 错误使用次数
    - right_use_count - 正确使用次数
    - isMastered - 是否已掌握
    - is_active - 是否激活状态

  🔍 查看方法

  1. 查看词汇总数:
  sqlite3 data/db/talkai.db "SELECT COUNT(*) FROM vocab_items WHERE user_id='your_user_id'
   AND is_active=1;"

  2. 按来源分组统计:
  sqlite3 data/db/talkai.db "SELECT source, COUNT(*) FROM vocab_items WHERE 
  user_id='your_user_id' AND is_active=1 GROUP BY source;"

  3. 查看最近添加的词汇:
  sqlite3 data/db/talkai.db -header -column "SELECT word, source, wrong_use_count, 
  right_use_count FROM vocab_items WHERE user_id='your_user_id' ORDER BY added_date DESC 
  LIMIT 10;"

  📈 当前测试用户数据状态

  - 用户ID: dev_user_d6b32d98
  - 当前等级: CET4
  - 词汇总数: 4534个
  - 分布:
    - level_vocab: 4533个（CET4等级词汇）
    - lookup: 1个（词典查询添加的"fantastic"）

  你可以使用SQLite Browser工具或者命令行直接查看和管理这些词汇数据。

----------
当我使用词典查询单词时，后端terminal log显示更新词汇成功：更新词汇 cosmology for user     │
│   3ed4291004c12c2a: right=0, wrong=2, mastered=False, source=lookup                         │
│   2025-08-28 16:07:24.132 | INFO     | app.api.v1.dict:lookup_word_simple:230 -             │
│   Successfully added English word 'cosmology' to vocabulary (source: lookup)                │
│   --                                                                                        │
│   但是我查询数据可却没有发现词汇库+1：                                                      │
│   (base) pean@MacBook-Air backend % sqlite3 data/db/talkai.db "SELECT COUNT(*) FROM         │
│   vocab_items WHERE user_id='3ed4291004c12c2a'                                              │
│      AND is_active=1;"                                                                      │
│   458                                                                                       │
│   (base) pean@MacBook-Air backend % sqlite3 data/db/talkai.db "SELECT COUNT(*) FROM         │
│   vocab_items WHERE user_id='3ed4291004c12c2a'                                              │
│      AND is_active=1;"                                                                      │
│   458                                                                                       │
│   -----------                                                                               │
│   另外，458 这个词汇数量也和UI界面中的词汇统计的数量（440）不一致，而且440这里的这个数字页  │
│   没有因为词典查询单词而+1.UI界面中的词汇统计截图：/Users/pean/Desktop/词汇状态.png 

          <view class="progress-fill" style="width: {{progressPercentage}}%"></view>