# Jam3a 术语表 · 英文 / 中文 / 阿拉伯语

> 源表：`Jam3a术语表_PRD英文权威.md`（2026-08-31）。英文为唯一权威，中文沿用源表，阿语为本表新增。
>
> **阿语翻译两条规则（按 PM 指定优先级）**
> 1. **行业常用优先** —— 取海湾地区语音房 / 游戏 / 送礼类 App（BIGO、Yalla、MICO 及主流手游阿语版）的通用译法
> 2. **尽量精简** —— 同一概念有长短两式时取短式，长式在备注里
>
> **变体**：现代标准阿拉伯语（MSA），不用埃及/海湾方言；海湾游戏圈通用外来词（كومبو / بوت / باس）例外，已单独标注。
> **数字体系**：**西阿拉伯数字 `1234`**（GCC 主流）。✅ PM 已锁定（2026-08-29）。
>
> 状态标记：`✅` 已定稿 · `🚫` 面向用户文案禁用
>
> **✅ 本表已全部定稿（2026-08-29 PM 拍板）**，无遗留待定项。8 项裁决见 §十一。

---

## 〇、你上次问我的 7 项，源表的回答

| # | 我的提问 | 源表怎么说 | 结论 |
|---|---|---|---|
| 1 | Rank 是段位还是排名 | 源表无 Rank 词条；有 `Quick Play 快速匹配（排位赛）| 按 ELO 段位匹配`，`Division/Tier 分部/层级`，`Skill-based Tier 技能分层` | ✅ **已定：段位体系 → `الرتبة`**（PM 2026-08-29）。排行榜场景另用 `لوحة الصدارة`，二者不混用 |
| 2 | Battle Pass 用哪个 | `Battle Pass | 赛季通行证` | ✅ **باس الموسم**（赛季通行证，非"战斗通行证"） |
| 3 | Crew war 译法 | `Crew | 竞技战队`；§11-5 明确「统一为「战队」，早期译"船队"作废」 | ✅ **حرب الفرق**（战队战）。⚠️ 源表 6.1 表格里仍写着「船队战」，与 §11-5 冲突，建议同步改掉 |
| 4 | Mic Seat | `Mic Seat（麦位）| 语音房发言席位，标准 1+8` | ✅ **مقعد المايك**。我的初稿是对的 |
| 5 | Coins / Gems | **源表里没有 Coins/Gems**。实际货币是 `Gold 金币`（高级货币）与 `Diamond(s) 钻石`（免费软币） | ❌ **我初稿写错了，已改**。→ `ذهب` / `ألماس` |
| 6 | Age Restriction 是否统一 | `Age Verification | 年龄验证 | 账号级年龄门控` 是 PRD 权威词 | ⚠️ **原型里写的是 "Age Restriction"，与 PRD 权威词不一致**。建议原型改为 Age Verification；阿语按权威词给 `التحقق من العمر`，另附 Restriction 译法备用 |
| 7 | 数字体系 1234 还是 ٠١٢٣ | 源表未规定 | ✅ **已定：`1234`**（PM 2026-08-29）。GCC 主流，全局统一 |

### 源表里新发现、会影响阿语翻译的 3 件事

1. **Owner / Moderator 已经有官方阿语本地化名**：`Owner（Sultan）`、`Moderator（Ameen）`。这是现成的文化适配，直接用：`المالك (سلطان)` / `المشرف (أمين)`。
2. **`Stake / Staking` 是合规禁用词**（§8 UI Language Guidelines：禁止 betting / wagering / gambling）。阿语同理，**`رهان`、`مراهنة`、`قمار` 三个词一个都不能出现在面向用户的文案里**，改用 `مساهمة في الجائزة` 这类批准用语。
3. **游戏名不译**（Ludo / Jackaroo / Carrom / Uno）。✅ PM 已定：**保留拉丁原文，不做阿语音译** —— 见下「不可译清单」。

---

## 一、不可译清单（保留拉丁原文，RTL 中需 `<bdi>` 隔离）

| 英文 | 处理 | 阿语备注 |
|---|---|---|
| Jam3a | 保留 | 品牌名，不音译 |
| GvG | 保留 | 源表 §11-7：PRD 未给正式拼写，首次出现处标注 GvG (Group vs Group) |
| Ludo / Jackaroo / Carrom / Uno | **保留拉丁原文** | ✅ PM 已定：**不做音译**（不用 لودو / جاكارو / كاروم / أونو）。RTL 中用 `<bdi>` 隔离 |
| XP | **保留 `XP`** | ✅ PM 已定：**不译为 `خبرة`**。海湾游戏普遍直接显示 XP，RTL 中用 `<bdi>` 隔离 |
| ELO | 保留 | 积分算法专名 |
| VIP | 保留或 `مميز` | 视版式 |
| WOLF | 保留 | 客户方团队名 |
| PDPL / GDPR / COPPA / PCI DSS | 保留 | 合规框架缩写 |
| AR | 保留（AR Gift Effects） | 增强现实 |
| X (formerly Twitter) | 保留 | 平台名 |
| 国家区号 `+966` 等、时间 `12:00`、纯数字 | 原样 + LTR 隔离 | — |

---

## 二、核心实体与组织

| 英文（PRD 权威） | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| Group | 群组 | المجموعة | 口语也见 `قروب`，正式文案用 المجموعة |
| Crew | 竞技战队 | الفريق | 与 Group 必须区分，不能也译成"群组" |
| Owner | 所有者 / 群主 | المالك (سلطان) | ✅ Sultan 是方案书 V4 已定的本地化称谓 |
| Moderator | 管理员 | المشرف (أمين) | ✅ Ameen 同上 |
| Captain | 队长 | القائد | |
| Member | 成员 | عضو | |
| Subscriber | 订阅者 | مشترك | |
| Staff | 平台运营 | الإدارة | 长式 `فريق الإدارة` |
| WOLF Staff / WOLF team | WOLF 运营团队 | فريق WOLF | WOLF 保留 |
| Seat | 席位 | مقعد | |
| Roster | 花名册 | التشكيلة | 长式 `قائمة الأعضاء` |
| Chat Mode / Game Mode | 语聊态 / 游戏态 | وضع المحادثة / وضع اللعب | ⚠️ 方案书建议废弃此二分 |

---

## 三、货币与经济

| 英文 | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| Gold | 金币 | ذهب | 高级货币 |
| Diamond(s) | 钻石 | ألماس | 免费软币 |
| XP | 经验值 | **XP**（保留） | ✅ 不译。见不可译清单 |
| Escrow | 托管 | الضمان | Gold Escrow → ضمان الذهب |
| Gold Prize | 金币奖池 | جائزة الذهب | |
| Prize Pool | 奖池 | مجموع الجوائز | 电竞阿语通用 |
| Entry Fee | 报名费 / 参赛费 | رسوم الدخول | |
| Creation Fee | 创建费 | رسوم الإنشاء | |
| Reward Pool | 奖励池 | مجموع المكافآت | 与 Prize Pool 句式统一 |
| Cash-out | 提现 | السحب | |
| Penalty Fee | 罚金 / 违约金 | غرامة | |
| **Stake / Staking** | 押注 / 下注 | 🚫 **禁用** | **面向用户文案禁止出现。** 内部可译 `الرهان`；对外必须用批准用语：competitive stakes → `جوائز تنافسية`、prize pool contribution → `مساهمة في الجائزة`、team challenge entry → `رسوم تحدي الفرق` |

---

## 四、装扮（In-Game Cosmetics）

| ID | 英文 | 中文 | 阿拉伯语 |
|---|---|---|---|
| CS-001 | Avatar Frame | 头像框 | إطار الصورة |
| CS-002 | Dice Skin | 骰子皮肤 | مظهر النرد |
| CS-003 | Game Piece Skin | 棋子皮肤 | مظهر القطع |
| CS-004 | Board Skin | 棋盘皮肤 | مظهر اللوحة |
| CS-005 | Victory Animation | 胜利动画 | حركة الفوز |
| CS-006 | Player Title | 玩家称号 | لقب اللاعب |
| CS-007 | Chat Emote Pack | 聊天表情包 | حزمة تعبيرات |
| CS-008 | Crew Banner | 战队旗帜 | راية الفريق |
| CS-009 | Crew Entrance Animation | 战队入场动画 | حركة دخول الفريق |
| CS-010 | Arena Theme | 竞技场主题 | سمة الساحة |
| CS-011 | Match Effect | 比赛特效 | تأثير المباراة |
| CS-012 | Profile Background | 资料背景 | خلفية الملف |
| CS-013 | Seasonal Set | 季节套装 | مجموعة موسمية |

**相关术语**

| 英文 | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| Cosmetics | 装扮 / 外观道具 | المظاهر | |
| Inventory | 背包 | الحقيبة | 游戏阿语惯用 |
| Equip / Unequip | 装备 / 卸下 | تجهيز / إزالة | |
| Rental | 租用 | إيجار | |
| Retire / Retirement | 退役 | إحالة | 商品下架的正式说法 |
| Seasonal | 季节限定 | موسمي | |
| Cosmetics Store | 装扮商店 | متجر المظاهر | |
| Try-Before-Buy | 先试后买 | جرب قبل الشراء | |
| Skin | 皮肤 | مظهر | ⚠️ 海湾游戏圈普遍说 `سكن`，正式文案建议 `مظهر` |
| Loot Box | 盲盒 | صندوق الغنائم | 用于"No Loot Boxes"合规表述 |

---

## 五、礼物（Social Gifting）

### 5.1 礼物目录

| ID | 英文 | 中文 | 阿拉伯语 |
|---|---|---|---|
| GF-001 | Clap | 鼓掌 | تصفيق |
| GF-002 | Fire Reaction | 火焰 Reaction | تفاعل النار |
| GF-003 | Rose Bouquet | 玫瑰花束 | باقة ورد |
| GF-004 | Crown Toss | 抛皇冠 | رمي التاج |
| GF-005 | Spotlight | 聚光灯 | دائرة الضوء |
| GF-006 | Treasure Chest | 宝箱 | صندوق الكنز |
| GF-007 | Fireworks Show | 烟花秀 | عرض الألعاب النارية |
| GF-008 | Sultan's Throne | Sultan 王座 | عرش السلطان |
| GF-009 | Diamond Rain | 钻石雨 | مطر الألماس |
| GF-010 | Legendary Crown | 传奇皇冠 | التاج الأسطوري |

**Tier 层级**：Micro → مصغّر · Small → صغير · Medium → متوسط · Large → كبير · Premium → مميّز · Ultra → أسطوري

**季节礼物**：Ramadan Lantern → فانوس رمضان · National Day Falcon → صقر اليوم الوطني

### 5.2 送礼场景

| ID | 英文 | 中文 | 阿拉伯语 |
|---|---|---|---|
| CTX-001 | Crew Voice Room | 战队语音房 | غرفة الفريق الصوتية |
| CTX-002 | During a Match | 对局进行中 | أثناء المباراة |
| CTX-003 | Tournament Spectating | 锦标赛观战 | مشاهدة البطولة |
| CTX-004 | Group Feed | 群组动态流 | موجز المجموعة |
| CTX-005 | User Profile | 个人资料页 | الملف الشخصي |
| CTX-006 | Public City Room | 公开城市房 | غرفة المدينة العامة |
| CTX-007 | Post-Match Results | 赛后结算页 | نتائج المباراة |
| CTX-008 | GvG Match | GvG 对局 | مباراة GvG |

### 5.3 其他送礼术语

| 英文 | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| Gifting Economy | 送礼经济 | اقتصاد الهدايا | |
| Gift Combo / Stacking | 礼物连击 / 堆叠 | كومبو الهدايا | ⚠️ `كومبو` 是海湾语音房 App 通用外来词；正式备选 `سلسلة الهدايا` |
| Gift History | 送礼记录 | سجل الهدايا | |
| Patron | Patron 等级（赞助人） | الراعي | |
| Patron Tier | Patron 层级 | فئة الراعي | Bronze/Silver/Gold/Diamond → برونزي / فضي / ذهبي / ألماسي |
| Patron Badge | Patron 徽章 | شارة الراعي | |
| Patron Leaderboard | Patron 排行榜 | لوحة الرعاة | |
| Gifter / Recipient | 送礼者 / 收礼者 | المُرسل / المُستلم | |
| Combo Multiplier | 连击倍率 | مضاعف الكومبو | |
| Gift Reactions | 礼物回应 | ردود الهدايا | |
| AR Gift Effects | AR 礼物特效 | تأثيرات AR للهدايا | |

---

## 六、赛事与竞技

### 6.1 赛事分类

| 英文 | 中文 | 阿拉伯语 |
|---|---|---|
| App-Level Tournament | 平台级锦标赛 | بطولة المنصة |
| Weekly Cup | 周杯 | كأس الأسبوع |
| Daily Cup | 每日杯 | كأس اليوم |
| Social Tournament | 社交赛事（用户自建） | بطولة اجتماعية |
| Private Tournament | 私密赛事 | بطولة خاصة |
| Public/Global Tournament | 公开 / 全球赛事 | بطولة عامة / عالمية |
| Challenge (Player vs Player) | 1v1 挑战 | التحدي |
| Group Challenge (GvG) | 群组挑战 | تحدي المجموعات |
| Crew War (GvG Bracket) | 战队战 | حرب الفرق |

### 6.2 竞技术语

| 英文 | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| GvG (Group vs Group) | 群组对抗 | GvG | 保留缩写 |
| Bracket | 对阵表 / 赛程表 | جدول المباريات | |
| Seeding | 种子排序 | الترتيب المسبق | |
| Single Elimination | 单败淘汰 | خروج المغلوب | 阿语体坛标准说法 |
| Double Elimination | 双败淘汰 | خروج المغلوب مرتين | |
| Round-robin | 循环赛 | نظام الدوري | |
| Losers' Bracket | 败者组 | جدول الخاسرين | |
| Rounds | 局数 / 回合数 | الجولات | |
| Best-of-N | N 局制 | الأفضل من N | |
| Division / Tier | 分部 / 层级 | القسم / الفئة | |
| Skill-based Tier | 技能分层 | فئة المهارة | |
| Promotion / Relegation | 晋级 / 降级 | ترقية / هبوط | |
| Group Rating | 群组积分 | تقييم المجموعة | |
| ELO | ELO 积分 | ELO | 保留 |
| Quick Play | 快速匹配（排位赛） | اللعب السريع | |
| Bot | 智能机器人替补 | بوت | 海湾通用外来词 |
| Forfeit | 弃权 | انسحاب | |
| Grace Period | 宽限期 | فترة السماح | |
| Counter-Offer | 还价 / 反提议 | عرض مضاد | |
| Player Selection | 选手选择 | اختيار اللاعبين | |
| Spectator / Spectating | 观战者 / 观战 | مشاهد / مشاهدة | |
| Champion / Runner-up | 冠军 / 亚军 | البطل / الوصيف | |
| Battle Pass | 赛季通行证 | باس الموسم | ⚠️ 海湾圈也直接说 `الباس` |
| Global League | 全球联赛 | الدوري العالمي | |
| **Rank** | **段位** | **الرتبة** | ✅ 已定为段位体系。排行榜场景用 `لوحة الصدارة`，不与本词混用 |

### 6.3 游戏与部件

| 英文 | 中文 | 阿拉伯语 |
|---|---|---|
| Ludo / Jackaroo / Carrom / Uno | 不译 | 保留拉丁原文 |
| Board | 棋盘 | اللوحة |
| Stickers（Carrom） | 贴纸 | الملصقات |
| Carromen | 卡隆棋棋子 | قطع الكاروم |
| Pieces（Ludo / Jackaroo） | 棋子 | القطع |
| Cards（Uno） | 牌 | البطاقات |

---

## 七、通知

| 英文 | 中文 | 阿拉伯语 |
|---|---|---|
| In-App Notification | 应用内通知 | إشعار داخل التطبيق |
| Push Notification | 推送通知 | إشعار فوري |
| Notification Matrix | 通知矩阵 | مصفوفة الإشعارات |
| Notification Preferences | 通知偏好 | تفضيلات الإشعارات |
| Deep Link | 深链 | رابط عميق |
| Deep Link Attribution | 深链归因 | إحالة الرابط العميق |
| External Sharing Channels | 外部分享渠道 | قنوات المشاركة الخارجية |
| Pending Channel Owner Approval | 待频道 Owner 审批 | بانتظار موافقة مالك القناة |

---

## 八、合规与风控

| 英文 | 中文 | 阿拉伯语 | 备注 |
|---|---|---|---|
| GCC | 海湾合作委员会国家 | دول الخليج | 正式全称 `مجلس التعاون الخليجي` |
| Legal Classification | 法律定性 | التصنيف القانوني | |
| Level-Based Access Gating | 等级门控 | تقييد الوصول حسب المستوى | |
| VIP-Only Alternative Gate | VIP 专属门控 | حصر VIP | |
| Per-Country Feature Toggle | 按国别功能开关 | تبديل الميزات حسب الدولة | |
| Daily/Weekly Staking Cap | 每日/每周押注上限 | 🚫 内部术语 | 对外不得出现"押注"字样，改 `الحد الأقصى اليومي/الأسبوعي` |
| UI Language Guidelines | 用语规范 | إرشادات لغة الواجهة | |
| Audit Trail | 审计追踪 | سجل التدقيق | |
| **Age Verification** | 年龄验证 | **التحقق من العمر** | ✅ PRD 权威词 |
| （Age Restriction） | （年龄限制） | （قيود العمر） | ⚠️ 原型中出现的非权威词，建议改回 Age Verification |
| Anti-Collusion and Fair Play | 反串谋与公平竞技 | مكافحة التواطؤ واللعب النزيه | |
| Anti-Cheat | 反作弊 | مكافحة الغش | |
| Moderation | 内容审核 / 治理 | الإشراف | |
| Rate Limiting and Anti-Spam | 频率限制与反垃圾 | تحديد المعدل ومكافحة السبام | |
| Data Retention and Deletion | 数据留存与删除 | الاحتفاظ بالبيانات وحذفها | |
| RTL / LTR | 从右到左 / 从左到右 | من اليمين إلى اليسار / من اليسار إلى اليمين | |

**🚫 阿语面向用户文案禁用词**：`قمار`（赌博）、`مراهنة`（下注）、`رهان`（赌注）、`مقامرة`
**✅ 批准替代**：`جوائز تنافسية` / `مساهمة في الجائزة` / `رسوم تحدي الفرق`

---

## 九、运营与技术

| 英文 | 中文 | 阿拉伯语 |
|---|---|---|
| Feature Toggle | 功能开关 | مفتاح الميزة |
| Per-Feature Granularity | 按功能粒度 | دقة لكل ميزة |
| Phased Rollout | 分阶段放量 | إطلاق تدريجي |
| Graceful Degradation | 优雅降级 | تدهور سلس |
| Rollback Safety | 回滚安全 | أمان التراجع |
| Toggle Audit Log | 开关审计日志 | سجل تدقيق المفاتيح |
| Admin Panel | 管理后台 | لوحة الإدارة |
| Configurable | 后台可配置 | قابل للتهيئة |
| Shared Pipeline | 共享执行管线 | مسار تنفيذ مشترك |
| Divergent Paths | 分叉路径 | مسارات متباينة |
| Atomic Transaction | 原子事务 | عملية ذرية |
| No Loot Boxes / Deterministic | 无盲盒 / 确定性购买 | لا صناديق غنائم / شراء محدد |
| Mic Seat | 麦位 | مقعد المايك |
| Discovery / Discover Screen | 发现页 | الاستكشاف |

---

## 十、登录注册 UI 文案（POC 当前所需）

| 英文 | 中文 | 阿拉伯语 | 风险 |
|---|---|---|---|
| Log In / Login | 登录 | تسجيل الدخول | — |
| Sign Up | 注册 | إنشاء حساب | — |
| Phone Number | 手机号 | رقم الهاتف | 窄容器短版：الهاتف |
| Email | 邮箱 | البريد الإلكتروني | 窄容器短版：البريد |
| Verification Code | 验证码 | رمز التحقق | |
| Send Code | 发送验证码 | إرسال الرمز | 按钮短版：أرسل |
| Password | 密码 | كلمة المرور | |
| Confirm Password | 确认密码 | تأكيد كلمة المرور | 窄容器短版：التأكيد |
| Forgot Password? | 忘记密码？ | نسيت كلمة المرور؟ | |
| Reset Password | 重置密码 | إعادة تعيين كلمة المرور | 按钮短版：إعادة التعيين |
| Country | 国家 | الدولة | |
| Select Country | 选择国家 | اختيار الدولة | |
| Search country... | 搜索国家... | ابحث عن دولة... | |
| Edit Date of Birth | 修改生日 | تعديل تاريخ الميلاد | |
| Set Up Your Profile | 完善资料 | إعداد الملف الشخصي | 标题短版：الملف الشخصي |
| Continue | 继续 | متابعة | |
| Skip | 跳过 | تخطي | |
| Claim | 领取 | استلام | |
| OK | 好的 | حسناً | |
| Or continue with | 或使用第三方登录 | أو تابع عبر | |
| Don't have an account? | 还没有账号？ | ليس لديك حساب؟ | |
| Already have an account? | 已有账号？ | لديك حساب بالفعل؟ | |
| Welcome Back | 欢迎回来 | مرحباً بعودتك | |
| Welcome to Jam3a! | 欢迎加入 Jam3a | مرحباً بك في Jam3a! | Jam3a 加 `<bdi>` |
| You've received a first-day reward: | 你已获得首日奖励 | لقد حصلت على مكافأة اليوم الأول: | 偏长，短版：مكافأة اليوم الأول |
| You must be 13 years or older to create a Jam3a account. | 需满 13 岁才能注册 | يجب أن يكون عمرك 13 عاماً أو أكثر لإنشاء حساب Jam3a. | |
| Terms of Service | 用户协议 | شروط الخدمة | |
| Privacy Policy | 隐私政策 | سياسة الخصوصية | |
| Log Out | 退出登录 | تسجيل الخروج | |

---

## 十一、仍待 PM 拍板

| # | 事项 | 我的建议 | 为什么 |
|---|---|---|---|
| 1 | **Rank 是段位还是排行榜** | 段位体系 → `الرتبة`；排行榜 → `لوحة الصدارة` | 两者阿语完全不同，定错全局返工。原型文件夹叫「Rank 内页交互」，倾向段位 |
| 2 | **数字体系** | `1234` | GCC 主流（沙特/阿联酋 App 与系统默认）；埃及才常用 `٠١٢٣` |
| 3 | **游戏名是否音译** | 保留拉丁原文 | PRD 明写"英文权威，不译"；音译反而增加对齐成本 |
| 4 | **XP 保留还是译 `خبرة`** | 保留 `XP` | 海湾游戏普遍直接显示，用户认知度最高 |
| 5 | **Combo 用 `كومبو` 还是 `سلسلة`** | `كومبو` | 规则一是行业常用，BIGO/Yalla 等同类产品都用 كومبو |
| 6 | **Skin 用 `مظهر` 还是 `سكن`** | `مظهر` | `سكن` 是口语外来词，客户交付文档建议正式 |
| 7 | **原型里 "Age Restriction" 改不改** | 改为 Age Verification | PRD 权威词是 Age Verification，保持一致 |
| 8 | **源表 6.1 的「船队战」** | 改为「战队战」 | 与源表 §11-5 的裁决冲突 |

---

*阿语列由本表新增，依「行业常用优先 → 尽量精简」两条规则拟定，使用现代标准阿拉伯语。源表英文术语取自客户直供 PRD，未作改动。*
