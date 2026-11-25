---
name: flow-front-line-cy-prd-vue-gen
description: "根据 PRD 文档全自动生成可运行的 Vue3 原型项目（Vue 3 + Vite + UnoCSS + Vue Router + Pinia）：自动提取页面清单、分批生成列表页与详情页（含路由、交互和业务上说得通的示例数据），按清单逐项验证并自动补漏，完成后输出报告，npm 启动即可在浏览器预览。当用户想基于 PRD 快速得到 Vue3 页面原型时使用；支持增量执行。"
argument-hint: "PRD文档路径（绝对路径）"
allowed-tools: Skill, Write, Glob, Bash, Read, Grep
auto-execute: true
---

# 原型生成器 Harness（Vue3 自动执行版）

> **全自动执行，用户只需提供 PRD 路径即可获得完整 Vue3 原型项目**

**执行公式**：Input(PRD) → Auto Loop(Harness) → Output(完整项目)

**技术栈**：Vue 3 + Vite + UnoCSS + Vue Router 4 + Pinia

---

## 自动执行流程

```
用户输入: PRD路径
           ↓
┌─────────────────────────────────────────────────────────┐
│  自动化执行（约 5-10 分钟，视页面数量而定）                   │
│                                                           │
│  Phase 1: 页面清单提取（自动）                              │
│  Phase 2: 分批生成（自动，无需确认）                        │
│  Phase 3: 验证检查（自动）                                │
│  Phase 4: 遗漏补充（自动）                                │
│  Phase 5: 最终报告（自动）                                │
└─────────────────────────────────────────────────────────┘
           ↓
用户获得: 完整的 Vue3 原型项目
```

---

## Phase 1: 自动提取页面清单

**执行动作（无需用户确认）**：
1. 读取 PRD 文件
2. 解析所有"UI 页面清单"、"页面列表"、"功能清单"章节
3. 检测端类型（单端/多端）
4. 生成 `generated-pages.json`
5. 报告：`✅ 发现 X 个页面（含 N 个端），开始生成`

**端检测规则**：
- 查找 PRD 中是否提及"平台后台"、"商家后台"、"小程序"等关键词
- 按页面路径前缀或模块归属自动分类
- 单端：直接进入生成流程
- 多端：自动生成导航首页

---

## Phase 2: 自动分批生成

**执行规则**：
- 每批 5-10 个页面
- 自动跳过已生成的页面（增量执行）
- 自动更新追踪文件

**自动处理**：
- 图标约束违规 → 自动替换为白名单图标
- 路由路径错误 → 自动修正为标准路径
- 缺少交互 → 自动补全（基于强制补全规则）

---

## Phase 3: 自动验证

**验证清单（自动逐项检查）**：

### 列表页（7 项）
- [ ] 页面头部包含标题、描述、新增按钮
- [ ] 表格有序号列（从 1 开始）
- [ ] 每行有编辑和删除按钮
- [ ] 删除有二次确认弹窗
- [ ] 分页显示"共 X 条记录"
- [ ] 空列表时显示"暂无数据"
- [ ] 搜索栏仅当 PRD 要求时存在

### 详情页（8 项）
- [ ] 左上角有返回按钮
- [ ] 新增/编辑模式标题正确
- [ ] 必填字段有红色星号
- [ ] 底部有取消和保存按钮
- [ ] 编辑模式加载已有数据
- [ ] 保存成功有 Message/跳转提示
- [ ] 保存失败显示错误信息
- [ ] 表单数据与 reactive/ref 双向绑定

### 路由（4 项）
- [ ] 列表→新增路径 = `/admin/{模块}/create`
- [ ] 列表→编辑路径 = `/admin/{模块}/:id`
- [ ] 详情→返回路径 = `/admin/{模块}`
- [ ] router/index.js 路由与跳转一致

### 图标（自动校验）
- [ ] 无禁止图标（Wechat/Alipay/EyeOpen 等）
- [ ] 图标均在白名单内

### 示例数据（4 项）
- [ ] 数据格式正确（手机号、邮箱、日期等）
- [ ] 关联数据一致（外键关联正确）
- [ ] 状态值在枚举范围内
- [ ] 数据具有业务代表性（非无意义字符串）

**验证失败处理**：
- 自动修复可修复的问题
- 无法自动修复的，记录到最终报告

---

## Phase 4: 遗漏自动补充

**执行动作**：
1. 读取 `generated-pages.json` 的 `pending` 列表
2. 逐个自动生成遗漏的页面
3. 更新 `pending` 列表
4. 直到 `pending` 为空

---

## Phase 5: 自动生成最终报告

**报告格式**：
```
═══════════════════════════════════════════
  原型生成完成
═══════════════════════════════════════════

📁 项目路径：docs/ui-vue/
📊 页面统计：50/50（100%）
🏗️ 技术栈：Vue3 + Vite + UnoCSS + Vue Router + Pinia
🌐 端口：5173

✅ 已生成（50）：
  ✓ 导航首页 (1页)
  ✓ 平台后台/列表页 (10页)
  ✓ 平台后台/详情页 (10页)
  ✓ 商家后台/列表页 (10页)
  ✓ 商家后台/详情页 (10页)
  ✓ 小程序端/列表页 (5页)
  ✓ 小程序端/详情页 (4页)

⚠️ 需要人工确认（0）

═══════════════════════════════════════════
  启动项目：cd docs/ui-vue && npm install && npm run dev
  访问地址：http://localhost:5173
═══════════════════════════════════════════
```

---

## 约束规则（自动执行）

### C1. 图标白名单
```
允许（@iconify/vue）：
  heroicons:plus, heroicons:pencil, heroicons:trash,
  heroicons:save, heroicons:x, heroicons:check,
  heroicons:magnifying-glass, heroicons:funnel,
  heroicons:arrow-left, heroicons:arrow-right,
  heroicons:chevron-left, heroicons:chevron-right,
  heroicons:eye, heroicons:eye-slash, heroicons:power,
  heroicons:lock, heroicons:lock-open, heroicons:exclamation-circle,
  heroicons:check-circle, heroicons:information-circle,
  heroicons:user, heroicons:users, heroicons:cog,
  heroicons:bell, heroicons:chat, heroicons:arrow-down-tray,
  heroicons:arrow-up-tray, heroicons:arrow-path,
  heroicons:dots-vertical, heroicons:clipboard,
  heroicons:printer, heroicons:desktop-computer,
  heroicons:shopping-bag, heroicons:device-phone-mobile

禁止（自动替换）：
  Wechat → device-phone-mobile
  Alipay → wallet
  EyeOpen → eye
  EyeClosed → eye-slash
```

**Vue 图标使用方式**：
```vue
<script setup>
import { Icon } from '@iconify/vue'
</script>

<template>
  <Icon icon="heroicons:plus" class="w-5 h-5" />
</template>
```

### C2. 路由标准化
```
列表页：/admin/{模块名}
新增页：/admin/{模块名}/create
详情页：/admin/{模块名}/:id

自动修正：
  /add     → /create
  /edit    → /:id
  {id}/edit → /:id
```

### C3. 交互强制补全
```
删除 → 必须有确认弹窗（自动添加）
保存 → 必须有 loading 态（自动添加）
失败 → 必须有错误提示（自动添加）
成功 → 必须有反馈（自动添加）
```

### C4. Schema 强制字段
```json
{
  "name": "页面名称",
  "path": "/路径",
  "interactions": ["操作列表"],
  "modules": []
}
```

### C5. 示例数据校验

**数据准确性规则**：
- 手机号：必须是 11 位，以 13/14/15/16/17/18/19 开头
- 邮箱：必须包含 @ 和 域名后缀
- 身份证：18 位，前 17 位为数字，最后一位可以是 X
- 日期：格式必须统一（YYYY-MM-DD）
- 金额：保留 2 位小数
- URL：必须以 http:// 或 https:// 开头

**数据正确性规则**：
- ID/编号：唯一性，不能重复
- 外键关联：关联的 ID 必须在对应表中存在
- 状态值：必须在定义的状态枚举范围内
- 枚举字段：值必须在 PRD 定义的可选列表中

**数据合理性规则**：
- 排序/优先级：数值在合理范围内（如 0-100）
- 百分比：0-100 之间
- 数量：非负整数
- 时间范围：结束时间 > 开始时间
- 字符串长度：在合理范围内（如名称 2-50 字符）

**关联数据一致性**：
```
示例：用户详情页
├── user_id: 1
├── user_name: "张三"
├── store_id: 101
└── store_name: "店铺A"  # store_id=101 的店铺名必须与 store 表一致

示例：订单详情页
├── order_id: "ORD202604210001"
├── user_id: 1  # 必须存在于 user 表
├── items: [
│   { product_id: 1001, product_name: "商品A" },  # product_id 必须存在于 product 表
│   { product_id: 1002, product_name: "商品B" }
│  ]
└── total_amount: 299.00  # 必须等于所有 items 价格之和
```

**自动校验流程**：
1. 生成模拟数据时按规则校验
2. 发现格式错误自动修正（如手机号少位数的补全或替换）
3. 发现关联错误自动补充关联数据
4. 无法自动修复的记录到报告

**校验示例**：
```vue
// ❌ 错误数据
{ phone: "12345", email: "test", status: "active" }

// ✅ 正确数据
{ phone: "13812345678", email: "user@example.com", status: "正常" }
```

---

## 输出结构

```
docs/ui-vue/
├── generated-pages.json    # 追踪文件（自动维护）
├── package.json
├── vite.config.js
├── uno.config.js           # UnoCSS 配置
├── index.html
└── src/
    ├── main.js
    ├── App.vue
    ├── style.css
    ├── router/
    │   └── index.js
    ├── stores/             # Pinia stores
    │   └── app.js
    ├── pages/
    │   └── home/
    │       └── index.vue   # 多端导航首页（多端时自动生成）
    ├── layouts/
    │   └── AdminLayout.vue
    └── [platform]/
        └── [模块名]/
            ├── list/
            │   ├── index.vue
            │   └── schema.json
            └── detail/
                ├── index.vue
                └── schema.json
```

### 多端导航首页

**触发条件**：当 PRD 包含多个端（平台后台、商家后台、小程序等）时，自动生成导航首页。

**首页内容**：
- 标题：项目名称 + "原型"
- 卡片列表：每个端一个入口卡片
- 卡片样式：图标 + 端名称 + 描述
- 点击跳转：进入对应端的第一个页面

**示例**：
```vue
<script setup>
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const platforms = [
  {
    icon: 'heroicons:desktop-computer',
    title: '平台后台',
    description: '运营管理、用户管理、数据统计',
    path: '/platform'
  },
  {
    icon: 'heroicons:shopping-bag',
    title: '商家后台',
    description: '门店管理、订单管理、商品管理',
    path: '/merchant'
  },
  {
    icon: 'heroicons:device-phone-mobile',
    title: '小程序端',
    description: '用户端小程序原型',
    path: '/wxapp'
  }
]
</script>

<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <h1 class="text-3xl font-bold mb-8">XX系统原型</h1>
    <div class="grid grid-cols-3 gap-6">
      <div
        v-for="platform in platforms"
        :key="platform.path"
        class="bg-white rounded-lg p-6 cursor-pointer hover:shadow-lg transition-shadow"
        @click="router.push(platform.path)"
      >
        <Icon :icon="platform.icon" class="w-12 h-12 mb-4 text-blue-600" />
        <h3 class="text-lg font-semibold mb-2">{{ platform.title }}</h3>
        <p class="text-gray-500 text-sm">{{ platform.description }}</p>
      </div>
    </div>
  </div>
</template>
```

**单端项目**：不生成导航首页，直接进入唯一端

---

### 端路由配置

```js
// router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 导航首页（多端时显示）
  { path: '/', name: 'Home', component: () => import('@/pages/home/index.vue') },

  // 平台后台
  {
    path: '/platform',
    component: () => import('@/layouts/PlatformLayout.vue'),
    children: [
      { path: 'users', name: 'UsersList', component: () => import('@/views/platform/users/list.vue') },
      // ...
    ]
  },

  // 商家后台
  {
    path: '/merchant',
    component: () => import('@/layouts/MerchantLayout.vue'),
    children: [
      { path: 'stores', name: 'StoresList', component: () => import('@/views/merchant/stores/list.vue') },
      // ...
    ]
  },

  // 小程序端
  {
    path: '/wxapp',
    component: () => import('@/layouts/WxappLayout.vue'),
    children: [
      { path: 'index', name: 'WxappIndex', component: () => import('@/views/wxapp/index.vue') },
      // ...
    ]
  },

  // 404
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('@/pages/NotFound.vue') }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

**端命名规范**：
- 平台后台：`/platform`
- 商家后台：`/merchant`
- 小程序端：`/wxapp`

---

### Layout 组件规范

**多端必须生成 4 种 Layout**：

```vue
<!-- 1. HomeLayout - 导航页布局 -->
<template>
  <div class="min-h-screen bg-gray-100">
    <slot />
  </div>
</template>

<!-- 2. PlatformLayout - 平台后台布局 -->
<template>
  <div class="flex min-h-screen">
    <aside class="w-64 bg-gray-900 text-white">
      <div class="p-4 font-bold">平台后台</div>
      <nav class="mt-4">
        <router-link
          v-for="menu in menus"
          :key="menu.path"
          :to="menu.path"
          class="flex items-center gap-2 px-4 py-2 hover:bg-gray-800"
        >
          <Icon :icon="menu.icon" class="w-5 h-5" />
          {{ menu.label }}
        </router-link>
      </nav>
    </aside>
    <div class="flex-1">
      <header class="bg-white border-b px-6 py-4">
        <span class="font-medium">平台后台</span>
      </header>
      <main class="p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<!-- 3. MerchantLayout - 商家后台布局（与 PlatformLayout 类似） -->
<!-- ... -->

<!-- 4. WxappLayout - 小程序端布局（底部 Tab 栏） -->
<template>
  <div class="min-h-screen bg-gray-50">
    <main class="pb-16">
      <slot />
    </main>
    <nav class="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around py-2">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="flex flex-col items-center gap-1"
      >
        <Icon :icon="tab.icon" class="w-6 h-6" />
        <span class="text-xs">{{ tab.label }}</span>
      </router-link>
    </nav>
  </div>
</template>
```

---

### Message 组件规范

**使用 ElMessage 或 MiniMessage**：

```vue
<script setup>
import { ElMessage } from 'element-plus'

const handleSave = async () => {
  try {
    await saveData(formData)
    ElMessage.success('保存成功')
    router.push('/admin/users')
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}
</script>
```

**或者使用独立的 Message 组件**（推荐，更轻量）：

```vue
<script setup>
import Message from '@/components/Message.vue'

const { showMessage } = useMessage()

showMessage({ type: 'success', text: '保存成功' })
</script>
```

---

### 404 页面规范

**路由匹配失败时显示**：

```vue
<script setup>
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="text-center">
      <Icon icon="heroicons:exclamation-circle" class="w-16 h-16 mx-auto mb-4 text-gray-400" />
      <h1 class="text-2xl font-bold mb-2">页面不存在</h1>
      <p class="text-gray-500 mb-6">您访问的页面可能已被删除或地址有误</p>
      <button
        @click="router.push('/')"
        class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        返回首页
      </button>
    </div>
  </div>
</template>
```

---

### UnoCSS 配置

```js
// uno.config.js
import { defineConfig, presetUno, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetIcons({
      scale: 1.2,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle'
      }
    })
  ],
  theme: {
    colors: {
      primary: '#3b82f6'
    }
  }
})
```

---

### 端口配置

**Vite 默认端口 5173**：

```js
// vite.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    open: true
  }
})
```

---

## 执行示例

**用户输入**：
```
/flow-front-line-cy-prd-vue-gen /path/to/prd.docx
```

**自动执行**：
```
[1/5] 提取页面清单... 发现 50 个页面
[2/5] 分批生成中... 第1批完成(10页)
[2/5] 分批生成中... 第2批完成(10页)
[2/5] 分批生成中... 第3批完成(10页)
[2/5] 分批生成中... 第4批完成(10页)
[2/5] 分批生成中... 第5批完成(10页)
[3/5] 验证检查... 通过率 100%
[4/5] 遗漏检测... 无遗漏
[5/5] 生成报告... 完成
```

**用户获得**：完整的 Vue3 原型项目

---

## 核心原则

1. **全自动执行** - 输入 PRD 路径，输出完整项目
2. **约束自动遵守** - 违规自动修正，不打断流程
3. **状态自动追踪** - 追踪文件自动维护
4. **验证自动进行** - 无需用户逐项确认
5. **遗漏自动补充** - pending 为空才算完成
6. **Vue 3 Composition API** - 使用 `<script setup>` 语法
7. **UnoCSS** - 高性能原子化 CSS
