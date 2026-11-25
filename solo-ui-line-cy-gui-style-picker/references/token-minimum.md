# 令牌最小集（token-minimum）

比稿卡与选型回传共用的令牌语义名单。**定位=取值记录，不是锁定条款**：选定风格的这些设计值照常回传，供主技能装入开工文档、编辑版转化（附加A）回流时参考；它们不锁画面、不约束任何环节的自由绘制（V06 定案：风格符合度对风格提示词，不对令牌）。值从哪来见下文「取值」。

## 命名与作用域

- 键名**逐字照抄本名单**，一律全小写连字符（驼峰、下划线、大写都是错写）；正本表在主技能 `assets/token-keys.json`（每个键的取值类型、运行时落点、常见错误写法以它为准）；表外参数是扩展参数，同样必须全小写连字符（运行时统一生成 `--sp-<键名>` 变量供页面引用）；
- 比稿卡是独立 HTML（picker 产物，不进编辑器壳）；产物内令牌前缀与分域遵循主技能 references/namespace-spec.md——变量落产物侧发生在附加A（编辑版转化）构建时，选型阶段不碰。

## 名单（选型阶段最小集，32 键，与正本表 minimum:true 一致）

| 组 | 键名 | 数量 |
|---|---|---|
| 颜色 | `primary` / `bg` / `surface` / `surface-alt` / `text-primary` / `text-secondary` / `border` / `success` / `danger` | 9 |
| 字体 | `font-head` / `font-body` | 2 |
| 字阶 | `size-title` / `size-head` / `size-body` / `size-caption` | 4 |
| 字重 | `weight-head` / `weight-body` | 2 |
| 行高 | `line-height-body` | 1 |
| 圆角 | `radius-sm` / `radius-md` / `radius-lg` | 3 |
| 间距 | `space-1` / `space-2` / `space-3` / `space-4`（紧凑→宽松四档） | 4 |
| 控件高度 | `size-ctl-sm` / `size-ctl-md` / `size-ctl-lg` | 3 |
| 阴影 | `shadow-sm` / `shadow-md` | 2 |
| 动效 | `motion-duration-base` / `motion-easing-base` | 2 |

- 密度档与网格列数在附加A 转化展开时补（`density` / `grid-cols`，见正本表），选型阶段不强制；
- **取值**：每档值是该风格自己的设计值，不是中性默认值。形态值（圆角、间距、字号等）取风格的设计来源：库内风格看项目里的提示词副本（`specimens/<卡id>/prompt.md`，进项目的唯一参照文件），AI 新创风格看样张；设计来源没给的，AI 按风格气质自己定，可参考样张。颜色有用户锁定的品牌色盘时以它为准，否则同样取设计来源。

## 下游关系

- **skeletonTokens**（selection-result）= 本名单的取值结果——作为记录随回执走，不冻结、不锁画面；
- **附加A 转化展开**（design-system.json）：以本名单为语义基线，扩间距阶梯/尺寸阶梯/密度/网格/motion 全套；
- **硬值 lint 白名单依据**（丁线）：产物 CSS 中的间距/尺寸/列数/颜色/圆角/阴影值必须可归因到令牌（或白名单物理值如 1px 边框），白名单口径=本名单语义组。
