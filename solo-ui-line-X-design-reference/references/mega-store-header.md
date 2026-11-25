# 大卖场商城 - 页面Header组件规范

> 基于盒马风格的小程序商城首页Header组件设计规范

---

## 1. 顶部Header组件结构

### 组件层级（从上到下）

```
┌─────────────────────────────────────────────┐
│ 1. 状态栏 (Status Bar)                       │
│    - 深色文字/图标                           │
│    - 高度: 24px                              │
├─────────────────────────────────────────────┤
│ 2. 标题栏 (Title Bar)                        │
│    - 页面标题 "商城首页"                      │
│    - 小程序胶囊按钮                          │
├─────────────────────────────────────────────┤
│ 3. 功能栏 (Function Bar)                     │
│    - 配送位置选择                           │
│    - 扫码图标 | 会员码图标 | 消息图标        │
├─────────────────────────────────────────────┤
│ 4. 搜索栏 (Search Bar)                       │
│    - 胶囊输入框样式                         │
└─────────────────────────────────────────────┘
```

### 背景渐变

```css
background: linear-gradient(to bottom, #FFF5EB 0%, #FFFFFF 100%);
/* 浅橙色 → 白色 */
```

---

## 2. 各层级详细规范

### 2.1 状态栏 (Status Bar)

```html
<!-- 深色状态栏 -->
<div class="flex justify-between items-center text-gray-800 text-xs py-2">
    <span class="font-medium">9:41</span>
    <div class="flex items-center gap-1">
        <i class="fas fa-signal"></i>
        <i class="fas fa-wifi ml-1"></i>
        <!-- 电量图标 -->
        <div class="ml-1 flex items-end">
            <div class="w-5 h-2.5 border border-gray-800 rounded-sm relative">
                <div class="absolute inset-0.5 bg-gray-800 rounded-xs"></div>
            </div>
            <div class="w-0.5 h-1 bg-gray-800 rounded-r-sm ml-px"></div>
        </div>
    </div>
</div>
```

### 2.2 标题栏 (Title Bar)

```html
<div class="flex items-center justify-between pb-3">
    <!-- 页面标题 -->
    <span class="text-lg font-bold text-gray-800">商城首页</span>

    <!-- 小程序胶囊按钮 -->
    <div class="px-4 py-1.5 rounded-full bg-gray-200 flex items-center gap-2 cursor-pointer">
        <i class="fas fa-th-large text-gray-600 text-sm"></i>
        <span class="text-sm text-gray-600">小程序</span>
    </div>
</div>
```

### 2.3 功能栏 (Function Bar)

```html
<div class="flex items-center justify-between py-2">
    <!-- 左侧：配送位置 -->
    <div class="flex items-center gap-2">
        <i class="fas fa-map-marker-alt text-gray-800"></i>
        <span class="text-sm text-gray-800">南山区科技园</span>
        <i class="fas fa-chevron-down text-gray-400 text-xs"></i>
    </div>

    <!-- 右侧：功能图标 -->
    <div class="flex items-center gap-4">
        <!-- 扫码 -->
        <div class="w-6 h-6 flex items-center justify-center cursor-pointer">
            <i class="fas fa-qrcode text-gray-800"></i>
        </div>
        <!-- 会员码 -->
        <div class="w-6 h-6 flex items-center justify-center cursor-pointer">
            <i class="fas fa-id-card text-gray-800"></i>
        </div>
        <!-- 消息 -->
        <div class="w-6 h-6 flex items-center justify-center cursor-pointer relative">
            <i class="fas fa-bell text-gray-800"></i>
            <!-- 红点提示 -->
            <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full"></span>
        </div>
    </div>
</div>
```

### 2.4 搜索栏 (Search Bar)

```html
<!-- 胶囊输入框 -->
<div class="pb-3">
    <div class="bg-gray-100 rounded-full px-4 py-2.5 flex items-center">
        <i class="fas fa-search text-gray-400"></i>
        <input type="text" placeholder="搜索水果/蔬菜/饮料..."
               class="bg-transparent flex-1 ml-2 text-sm text-gray-700 outline-none">
    </div>
</div>
```

---

## 3. 完整Header代码模板

```html
<!-- Top Header - 小程序商城风格 -->
<div class="bg-gradient-to-b from-orange-100 to-white px-4">
    <!-- 状态栏 - 深色 -->
    <div class="flex justify-between items-center text-gray-800 text-xs py-2">
        <span class="font-medium">9:41</span>
        <div class="flex items-center gap-1">
            <i class="fas fa-signal"></i>
            <i class="fas fa-wifi ml-1"></i>
            <div class="ml-1 flex items-end">
                <div class="w-5 h-2.5 border border-gray-800 rounded-sm relative">
                    <div class="absolute inset-0.5 bg-gray-800 rounded-xs"></div>
                </div>
                <div class="w-0.5 h-1 bg-gray-800 rounded-r-sm ml-px"></div>
            </div>
        </div>
    </div>

    <!-- 标题栏 -->
    <div class="flex items-center justify-between pb-3">
        <span class="text-lg font-bold text-gray-800">商城首页</span>
        <div class="px-4 py-1.5 rounded-full bg-gray-200 flex items-center gap-2 cursor-pointer">
            <i class="fas fa-th-large text-gray-600 text-sm"></i>
            <span class="text-sm text-gray-600">小程序</span>
        </div>
    </div>

    <!-- 功能栏 -->
    <div class="flex items-center justify-between py-2">
        <div class="flex items-center gap-2">
            <i class="fas fa-map-marker-alt text-gray-800"></i>
            <span class="text-sm text-gray-800">南山区科技园</span>
            <i class="fas fa-chevron-down text-gray-400 text-xs"></i>
        </div>
        <div class="flex items-center gap-4">
            <div class="w-6 h-6 flex items-center justify-center cursor-pointer">
                <i class="fas fa-qrcode text-gray-800"></i>
            </div>
            <div class="w-6 h-6 flex items-center justify-center cursor-pointer">
                <i class="fas fa-id-card text-gray-800"></i>
            </div>
            <div class="w-6 h-6 flex items-center justify-center cursor-pointer relative">
                <i class="fas fa-bell text-gray-800"></i>
                <span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full"></span>
            </div>
        </div>
    </div>

    <!-- 搜索栏 -->
    <div class="pb-3">
        <div class="bg-gray-100 rounded-full px-4 py-2.5 flex items-center">
            <i class="fas fa-search text-gray-400"></i>
            <input type="text" placeholder="搜索水果/蔬菜/饮料..."
                   class="bg-transparent flex-1 ml-2 text-sm text-gray-700 outline-none">
        </div>
    </div>
</div>
```

---

## 4. Tailwind CSS 关键类名

| 元素 | 类名 |
|------|------|
| 整体背景 | `bg-gradient-to-b from-orange-100 to-white` |
| 状态栏文字 | `text-gray-800` |
| 页面标题 | `text-lg font-bold text-gray-800` |
| 胶囊按钮 | `px-4 py-1.5 rounded-full bg-gray-200` |
| 胶囊图标 | `text-gray-600 text-sm` |
| 功能图标 | `w-6 h-6 cursor-pointer` |
| 搜索栏容器 | `bg-gray-100 rounded-full` |
| 搜索输入框 | `bg-transparent flex-1 outline-none` |

---

## 5. 设计原则

1. **层级分明**：从上到下依次是状态栏→标题→功能→搜索
2. **视觉平衡**：左右对称，留白充足
3. **交互友好**：所有可点击元素都有 `cursor-pointer`
4. **小程序风格**：参考微信小程序设计规范
5. **配色统一**：使用灰色系图标，橙色作为主题强调色

---

## 6. 应用页面

此Header模板适用于：
- 首页 (index.html)
- 分类页 (category.html) - 需适配返回按钮
- 搜索页 (search.html) - 需适配返回按钮

子页面（如商品详情、购物车、我的）使用独立的Header设计：
- 返回按钮 + 页面标题
- 或Tab标签切换
