---
name: flow-front-line-cy-prd-ui-gen
description: "根据 PRD 文档全自动生成可运行的 React 原型项目：自动提取页面清单、分批生成列表页与详情页（含路由、交互和业务上说得通的示例数据），按清单逐项验证并自动补漏，完成后输出报告，npm 启动即可在浏览器预览。当用户想基于 PRD 快速得到 React 页面原型时使用；支持增量执行，已生成的页面自动跳过。"
argument-hint: "PRD文档路径（绝对路径）"
allowed-tools: Skill, Write, Glob, Bash, Read, Grep
auto-execute: true
---

# 原型生成器 Harness（自动执行版）

> **全自动执行，用户只需提供 PRD 路径即可获得完整原型项目**

**执行公式**：Input(PRD) → Auto Loop(Harness) → Output(完整项目)

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
用户获得: 完整的 React 原型项目
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
- [ ] 保存成功有 Toast/跳转提示
- [ ] 保存失败显示错误信息
- [ ] 表单数据与 state 双向绑定

### 路由（4 项）
- [ ] 列表→新增路径 = `/admin/{模块}/create`
- [ ] 列表→编辑路径 = `/admin/{模块}/:id`
- [ ] 详情→返回路径 = `/admin/{模块}`
- [ ] App.jsx 路由与跳转一致

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

📁 项目路径：docs/ui-html/
📊 页面统计：50/50（100%）
🏗️ 组件：HomeLayout, PlatformLayout, MerchantLayout,
         WxappLayout, Sidebar, TabBar, Toast
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
  启动项目：cd docs/ui-html && npm install && npm run dev
  访问地址：http://localhost:5173
═══════════════════════════════════════════
```

---

## 约束规则（自动执行）

### C1. 图标白名单
```
允许：Plus, Edit, Pencil, Delete, Trash2, Save, X, Close,
      Check, Search, Filter, ArrowLeft, ArrowRight,
      ChevronLeft, ChevronRight, Eye, EyeOff, Power,
      Lock, Unlock, AlertCircle, CheckCircle, Info,
      User, Users, Settings, Bell, MessageSquare,
      Download, Upload, RefreshCw, MoreVertical, Copy,
      Desktop, Store, Smartphone, Grid, List, Layout

禁止（自动替换）：
  Wechat → Smartphone
  Alipay → Wallet
  EyeOpen → Eye
  EyeClosed → EyeOff
  Wxmoment → Grid
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
```jsx
// ❌ 错误数据
{ phone: "12345", email: "test", status: "active" }

// ✅ 正确数据
{ phone: "13812345678", email: "user@example.com", status: "正常" }
```

---

## 输出结构

```
docs/ui-html/
├── generated-pages.json    # 追踪文件（自动维护）
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── index.css
    ├── pages/
    │   └── home/
    │       └── index.jsx    # 多端导航首页（多端时自动生成）
    ├── layouts/
    │   └── AdminLayout.jsx
    └── [platform]/
        └── [模块名]/
            ├── list/
            │   ├── index.jsx
            │   └── schema.json
            └── detail/
                ├── index.jsx
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
```jsx
// 多端导航首页
<div className="min-h-screen bg-gray-100 p-8">
  <h1 className="text-3xl font-bold mb-8">XX系统原型</h1>
  <div className="grid grid-cols-3 gap-6">
    <Card
      icon={<Desktop />}
      title="平台后台"
      description="运营管理、用户管理、数据统计"
      onClick={() => navigate('/platform')}
    />
    <Card
      icon={<Store />}
      title="商家后台"
      description="门店管理、订单管理、商品管理"
      onClick={() => navigate('/merchant')}
    />
    <Card
      icon={<Smartphone />}
      title="小程序端"
      description="用户端小程序原型"
      onClick={() => navigate('/wxapp')}
    />
  </div>
</div>
```

**单端项目**：不生成导航首页，直接进入唯一端

---

### 端路由配置

```jsx
// App.jsx
<Routes>
  {/* 导航首页（多端时显示） */}
  <Route path="/" element={<HomePage />} />

  {/* 平台后台 */}
  <Route path="/platform" element={<PlatformLayout />}>
    <Route path="users" element={<UsersList />} />
    {/* ... */}
  </Route>

  {/* 商家后台 */}
  <Route path="/merchant" element={<MerchantLayout />}>
    <Route path="stores" element={<StoresList />} />
    {/* ... */}
  </Route>

  {/* 小程序端 */}
  <Route path="/wxapp" element={<WxappLayout />}>
    <Route path="index" element={<WxappIndex />} />
    {/* ... */}
  </Route>
</Routes>
```

**端命名规范**：
- 平台后台：`/platform`
- 商家后台：`/merchant`
- 小程序端：`/wxapp`

**自动判断**：解析 PRD 页面清单，按路径前缀或模块归属自动分类

---

### Layout 组件规范

**多端必须生成 4 种 Layout**：

```jsx
// 1. HomeLayout - 导航页布局（简洁无边栏）
function HomeLayout({ children }) {
  return <div className="min-h-screen bg-gray-100">{children}</div>
}

// 2. PlatformLayout - 平台后台布局（左侧边栏 + 顶部导航）
function PlatformLayout({ children }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar menus={platformMenus} />
      <div className="flex-1">
        <Header title="平台后台" />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}

// 3. MerchantLayout - 商家后台布局（与 PlatformLayout 类似）
function MerchantLayout({ children }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar menus={merchantMenus} />
      <div className="flex-1">
        <Header title="商家后台" />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}

// 4. WxappLayout - 小程序端布局（底部 Tab 栏）
function WxappLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="pb-16">{children}</main>
      <TabBar tabs={wxappTabs} />
    </div>
  )
}
```

**Sidebar 菜单结构**：
```jsx
const platformMenus = [
  { key: 'dashboard', label: '首页概览', icon: <Home />, path: '/platform' },
  { key: 'users', label: '用户管理', icon: <User />, path: '/platform/users' },
  { key: 'stores', label: '门店管理', icon: <Store />, path: '/platform/stores' },
  // ...
]
```

**TabBar 菜单结构**：
```jsx
const wxappTabs = [
  { key: 'index', label: '首页', icon: <Home />, path: '/wxapp' },
  { key: 'order', label: '订单', icon: <FileText />, path: '/wxapp/orders' },
  { key: 'cart', label: '购物车', icon: <ShoppingCart />, path: '/wxapp/cart' },
  { key: 'profile', label: '我的', icon: <User />, path: '/wxapp/profile' },
]
```

---

### Toast 组件规范

**统一使用 React Hot Toast**：

```jsx
// 在 App.jsx 中全局配置
import { Toaster } from 'react-hot-toast'

function App() {
  return (
    <>
      <Routes>...</Routes>
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 3000,
          success: { style: { background: '#10b981', color: '#fff' } },
          error: { style: { background: '#ef4444', color: '#fff' } },
        }}
      />
    </>
  )
}

// 使用方式
import toast from 'react-hot-toast'

toast.success('保存成功')
toast.error('保存失败：' + error.message)
```

---

### 404 页面规范

**路由匹配失败时显示**：

```jsx
function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <AlertCircle className="mx-auto mb-4" size={64} />
        <h1 className="text-2xl font-bold mb-2">页面不存在</h1>
        <p className="text-gray-500 mb-6">您访问的页面可能已被删除或地址有误</p>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg"
        >
          返回首页
        </button>
      </div>
    </div>
  )
}

// App.jsx 路由配置
<Route path="*" element={<NotFoundPage />} />
```

---

### 端口配置

**Vite 默认端口 5173**：

```js
// vite.config.js
export default defineConfig({
  server: {
    port: 5173,
    open: true
  }
})
```

**启动命令**：
```bash
npm install
npm run dev  # 自动打开 http://localhost:5173
```

---

## 执行示例

**用户输入**：
```
/flow-front-line-cy-prd-ui-gen /path/to/prd.docx
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

**用户获得**：完整的原型项目

---

## 核心原则

1. **全自动执行** - 输入 PRD 路径，输出完整项目
2. **约束自动遵守** - 违规自动修正，不打断流程
3. **状态自动追踪** - 追踪文件自动维护
4. **验证自动进行** - 无需用户逐项确认
5. **遗漏自动补充** - pending 为空才算完成
