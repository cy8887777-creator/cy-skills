# 组件风格库清单（第四步 组件风格的风格卡来源）

> 用法：第四步组件风格从这里选库——**运行时按需抓取该库官方文档**（抓取前先实测可达），渲染该库风格的核心组件形态卡（按钮/标签/卡片/输入组合样）。**链接全部需实测后呈现给用户。**
> 定位：组件**风格基调**来源（形态语言/密度/质感参照）；配色与字体永远用已锁令牌；组件族清单与契约结构用 data/case 案例。

## 🟢 微信 / 小程序生态（关键）

| 库 | 端 | 官方入口（待实测） | 风格特征 |
|---|---|---|---|
| WeUI | 移动/H5 | github.com/weui/weui · weui.io | 微信原生视觉，克制标准 |
| 微信小程序设计规范 | 小程序 | developers.weixin.qq.com/miniprogram/design/ | 官方设计指南（导航/操作/色彩） |
| Vant Weapp | 小程序 | github.com/youzan/vant-weapp | 有赞小程序组件 |
| TDesign 小程序 | 小程序 | tdesign.tencent.com | 腾讯小程序组件 |

## 📱 移动端 · 国内

| 库 | 端 | 官方入口（待实测） | 风格特征 |
|---|---|---|---|
| Vant | 移动 H5 | vant-ui.github.io/vant | 移动第一梯队，组件全 |
| Ant Design Mobile | 移动 H5 | mobile.ant.design | 蚂蚁移动体系 |
| NutUI | 移动 H5/小程序 | nutui.jd.com | 京东电商系 |
| TDesign Mobile | 移动 | tdesign.tencent.com/mobile | 腾讯移动 |
| Varlet | 移动 H5 | varletjs.com | Material 风移动 |
| Mand Mobile | 移动 | mand-mobile.gitee.io | 滴滴金融级 |

## 📱 移动端 · 官方设计规范

| 库 | 端 | 官方入口 |
|---|---|---|
| Material Design 3 | Android | m3.material.io |
| Apple HIG | iOS | developer.apple.com/design（有中文） |
| HarmonyOS Design | 鸿蒙 | developer.huawei.com/consumer/cn/design/ |

## 🖥 PC · 国内

| 库 | 端 | 官方入口（待实测） |
|---|---|---|
| Ant Design ★ | PC | ant.design |
| Arco Design | PC | arco.design |
| TDesign | PC | tdesign.tencent.com/design |
| Element Plus | PC | element-plus.org |
| Semi Design | PC | semi.design |

## 🌐 PC · 国际

| 库 | 端 | 官方入口（待实测） |
|---|---|---|
| shadcn/ui | Web | ui.shadcn.com |
| Chakra UI | Web | chakra-ui.com |
| Mantine | Web | mantine.dev |
| HeroUI | Web | heroui.com |
| Radix Themes | Web | radix-ui.com/themes |
| Fluent 2 | 跨端 | fluent2.microsoft.design |
| Atlassian Design System | Web | atlassian.design |
| IBM Carbon | Web | carbondesignsystem.com |

## 🎨 非大厂高质量（形态参考）

| 库 | 说明 | 官方入口（待实测） |
|---|---|---|
| daisyUI | Tailwind 多主题 | daisyui.com |
| Flowbite | Tailwind 组件+文档 | flowbite.com |
| Preline UI | Tailwind 开源组件 | preline.io |
| Tremor | 数据看板组件 | tremor.so |
| Untitled UI | 高质量 UI kit 标杆（部分免费） | untitledui.com |

## 第四步使用规则

1. 按画像端向（移动/PC）从对应组选 **6~8 个库**（含 Ant 必选）+ **AI 生成 2~3 张**【AI 生成】
2. 每库渲染核心组件形态卡（按钮/标签/卡片/输入组合样）——**运行时抓官方文档前先实测可达**；抓不到的如实标注跳过
3. 用户选一个风格基调 → 融合产出：基调形态语言 × 已锁令牌 → 逐族组件规范卡 → 总览组件章成文
4. 快照（可选增强）：对选定库抓官方文档 md/HTML 存 data/component-styles/<lib>/，标版本与出处

*清单登记：2026-10-22 · 链接均待实测*

## 📦 已本地快照（data/component-styles/ 下）

| 库 | 快照内容 | 状态 |
|---|---|---|
| **antd/** | 40 个组件规范文档（zh-CN，按组件命名：button/alert/table…含设计规范 docs/spec） | ✅ 已落地 |
| **vant/** | 15 个移动组件官方文档（zh-CN） | ✅ 已落地 |
| **daisyui/** | 27 个组件文档 | ✅ 已落地 |
| **element/** | 30 个组件文档（en-US） | ✅ 已落地 |
| **arco/** | 14 个组件文档 | ✅ 已落地 |
| **antd-mobile/** | 12 个组件文档 | ✅ 已落地 |
| **varlet/** | 14 个组件文档 | ✅ 已落地 |
| **naive-ui/** | 4 个组件文档 | ✅ 已落地 |
| **tdesign-mobile/** | 2 个组件文档 | ✅ 已落地 |
| **wechat-miniprogram/** | 10 章官方设计指南（色板/图标等以图片承载的规格已加注） | ✅ 已落地 |
| **weui/** | 3 个（组件总览 / 20 核心组件 DOM 形态树 / README） | ✅ 已落地 |
| **hig-apple/** | 12 章官方规范（中文版，含系统色表格） | ✅ 已落地 |
| **harmonyos/** | 26 章官方规范（「设计原则」专页官方 404，以《设计理念》替代，_meta 已标注） | ✅ 已落地 |
| **material3/** | 11 章官方规范（英文，36 组件总览 + 6 组件详情） | ✅ 已落地 |
| **shadcn-ui/** | 30 个组件文档 | ✅ 已落地 |
| **chakra-ui/** | 30 个组件文档 | ✅ 已落地 |
| **heroui/** | 30 个组件文档 | ✅ 已落地 |
| **mantine/** | 32 个组件文档（2 个官方空壳文件已剔除） | ✅ 已落地 |
| **carbon/** | 30 个组件文档（overview.mdx 薄页自动回退同名组件页） | ✅ 已落地 |
| **fluent-2/** | 20 个（仓库无组件文档主体，收各包官方 README 纲要，_meta 注明） | ✅ 部分 |
| **radix-themes/** | 1 个（仓库无组件文档，仅 README + 官网链接） | ✅ 部分 |
| **flowbite/** | 30 个组件文档（components + forms） | ✅ 已落地 |
| **preline/** | 23 个（仓库仅交互插件官方 README，_meta 注明） | ✅ 已落地 |
| tremor | 官网域名解析失败 + 仓库无文档（仅 _meta 记录出处） | ⏳ 待补 |
| atlassian-design | 按批次约定仅登记官网出处（1 份 _meta） | ⏳ 待补 |
| untitled-ui | 按批次约定仅登记官网出处（1 份 _meta） | ⏳ 待补 |

*当前快照合计：446 个文档（23 库有实质快照；其中 14 库附 _meta.md 记录入口/方式/已知限制，国内 9 库暂缺。「原始组件库规范」页自动读取本目录生成）*
