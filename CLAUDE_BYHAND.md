
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
  sqlite3 data/db/talkai.db "SELECT COUNT(*) FROM vocab_items WHERE user_id='3ed4291004c12c2a'
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


-------------
 📊 数据库结构详解

  用户表 (users)

  - id (VARCHAR, 主键): 用户唯一标识符
  - openid (VARCHAR, 唯一): 微信OpenID
  - nickname (VARCHAR): 用户昵称
  - grade (VARCHAR): 学习级别 (Primary School, CET4等)
  - age, gender: 用户基本信息
  - created_at, last_login_at: 时间戳
  - total_usage_time, chat_history_count: 使用统计

  词汇表 (vocab_items)

  - id (INTEGER, 主键): 词汇条目ID
  - user_id (VARCHAR, 外键): 关联用户ID
  - word (VARCHAR): 单词
  - source (VARCHAR): 来源 ('chat_correction', 'lookup', 'level_vocab')
  - level (VARCHAR): 难度级别
  - wrong_use_count, right_use_count: 使用统计
  - isMastered (BOOLEAN): 是否已掌握
  - added_date, last_used: 时间戳

  数据库查询示例

  查询用户信息和词汇统计:
  sqlite3 data/db/talkai.db "
  SELECT u.id, u.nickname, u.grade, 
         COUNT(v.id) as total_vocab,
         SUM(CASE WHEN v.isMastered = 1 THEN 1 ELSE 0 END) as mastered_vocab
  FROM users u 
  LEFT JOIN vocab_items v ON u.id = v.user_id 
  GROUP BY u.id 
  LIMIT 5;"

  查询特定用户的词汇:
  # 查询用户所有词汇
  sqlite3 data/db/talkai.db "
  SELECT word, source, wrong_use_count, right_use_count, isMastered 
  FROM vocab_items 
  WHERE user_id = 'USER_ID_HERE' 
  ORDER BY added_date DESC;"

  # 查询特定单词
  sqlite3 data/db/talkai.db "
  SELECT * FROM vocab_items 
  WHERE user_id = 'USER_ID_HERE' AND word = 'WORD_HERE';"

  # 查询最近学习词汇（AI改错+词典查词）
  sqlite3 data/db/talkai.db "
  SELECT word, source, added_date 
  FROM vocab_items 
  WHERE user_id = 'USER_ID_HERE' 
  AND source IN ('chat_correction', 'lookup') 
  ORDER BY added_date DESC 
  LIMIT 20;"

  当前数据库状态:
  - 总用户数: 93个
  - 测试用户 c697fcdff9a3ae31: 439个词汇（全部为级别词汇）
  - 最活跃用户有5756个词汇

  数据库完整实现了talkai_py的功能，支持词汇来源追踪、掌握度统计和学习进度管理。
--------------

 问题原因：
  1. 开发环境特性：微信开发者工具每次生成不同的js_code
  2. 动态OpenID生成：后端根据js_code动态生成dev_openid_xxxx
  3. 多用户创建：每次登录都创建新用户，导致数据分散

  数据库当前状态：
  - ef30cdb5499ebed6: 439个词汇（level_vocab）
  - 73c19ed6d8bedc6d: 2755个词汇
  - 总共93个开发用户

  修复方案：
  ✅ 固定开发环境用户ID - 修改auth.py:55使用固定openid

  查询数据库的正确方法：

  # 1. 查看当前JWT token对应的用户
  # token中的"sub"字段就是真实的user_id

  # 2. 查询特定用户的词汇库
  sqlite3 data/db/talkai.db "
  SELECT u.id, u.nickname, u.grade, 
         COUNT(v.id) as total_vocab,
         COUNT(CASE WHEN v.source='chat_correction' THEN 1 END) as ai_corrections,
         COUNT(CASE WHEN v.source='lookup' THEN 1 END) as lookups
  FROM users u 
  LEFT JOIN vocab_items v ON u.id = v.user_id 
  WHERE u.id = 'USER_ID_FROM_JWT_TOKEN'
  GROUP BY u.id;"

  # 3. 查询具体词汇信息
  sqlite3 data/db/talkai.db "
  SELECT word, source, wrong_use_count, right_use_count, isMastered, added_date 
  FROM vocab_items 
  WHERE user_id = 'USER_ID_FROM_JWT_TOKEN' AND word = 'cosmology';"

  下次登录时：现在所有开发环境登录都会使用同一个用户ID，避免数据分散问题。

  -------------

⏺ 🔍 Console 问题分析

  问题1: Console 滚动刷屏

  原因： 词汇同步管理器在重试失败的同步请求，每次失败都会再次重试，形成循环

  问题2: 403 Forbidden 错误

  根本原因： Token认证失败
  - api.js:67 - 请求 /user/vocab-list 返回403
  - api.js:67 - 请求 /user/profile/vocab-status 返回403
  - 错误信息：{detail: "Not authenticated"}

  调用链分析：
  app.js:33 onLaunch
  → app.js:93 initVocabSync
  → vocab-sync.js:50 init
  → vocab-sync.js:133 api.user.getVocabList()
  → api.js:248 getVocabList()
  → api.js:45 request()
  → 403 Forbidden

  问题核心：
  1. Token过期/无效 - 前端存储的token已失效
  2. 重试循环 - 同步失败后不断重试，造成console刷屏
  3. 认证流程 - 应用启动时没有正确重新认证

  解决方案：
  需要在应用启动时检查token有效性，如果无效则重新登录，避免使用失效token进行API调用。

  当前问题是前端使用了过期的token，导致所有认证API都返回403，同步管理器不断重试失败的请求
  。


-----------------

  问题核心：
  1. Token过期/无效 - 前端存储的token已失效
  2. 重试循环 - 同步失败后不断重试，造成console刷屏
  3. 认证流程 - 应用启动时没有正确重新认证

  解决方案：
  需要在应用启动时检查token有效性，如果无效则重新登录，避免使用失效token进行API调用。

  当前问题是前端使用了过期的token，导致所有认证API都返回403，同步管理器不断重试失败的请求
  。

  -----------
⏺ 是的，openid确实唯一且与微信用户绑定

  但仍需JWT的原因：

  1. 传输安全 - openid直接传输容易被截获和重放攻击
  2. 权限控制 - JWT可包含用户权限、过期时间等额外信息
  3. 微信规范 - 微信小程序推荐使用临时凭证而非长期标识符
  4. 会话管理 - JWT提供会话过期机制，openid是永久标识符
    微信登录 → 获取openid → 服务器验证 → 生成JWT(包含user_id) → 客户端使用JWT访问API


    -------
    ⏺  前面提到的3个问题：是的，根源是同一个：Token失效

  问题链：
  1. 根源： Token过期/无效
  2. 直接后果： API调用返回403
  3. 连锁反应： 同步管理器检测到失败后不断重试
  4. 表现症状： Console不停滚动刷屏

  调用链分析：
  Token失效 → 403错误 → 同步重试 → 再次403 → 继续重试 → Console刷屏

  解决方案只需修复根源：
  应用启动时检查token有效性，如果无效则重新认证，避免使用失效token进行后续所有API调用。