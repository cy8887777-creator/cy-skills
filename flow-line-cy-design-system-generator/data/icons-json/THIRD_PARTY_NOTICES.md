# THIRD_PARTY_NOTICES —— data/icons/ 第三方图标库声明

本目录打包了 10 个第三方开源图标库的 SVG 快照，供离线预览与设计系统选型。各库版权归其原作者所有，使用时请遵循下表所列许可。**「开源可商用」≠「免署名」**：CC-BY / CC-4.0 系列要求展示署名。

| 库 | 许可 | 来源 | 备注 |
|---|---|---|---|
| Lucide | ISC | iconify 首采；2026-10-23 自 npm `lucide-static@1.61.0` 回填 | 默认本地预览库 |
| Tabler | MIT | npm `@tabler/icons` | filled/outline 双形态 |
| Remix Icon | Apache-2.0 | npm `remixicon` | |
| Phosphor | MIT | npm `@phosphor-icons/core` | |
| Bootstrap Icons | MIT | npm `bootstrap-icons` | |
| Material Symbols | Apache-2.0 | npm `@material-symbols/svg-400` | outlined/ 内含 -fill 面性变体 |
| HeroIcons | MIT | gh:tailwindlabs/heroicons@master | ⚠ 分支引用，版本待钉 |
| Feather | MIT | npm `feather-icons` | |
| Boxicons | CC-4.0 | npm `boxicons` | CC 许可，注意署名条款 |
| Solar | CC-BY-4.0 | gh:480-Design/Solar-icon-set@main | 署名惯例：*Icons by 480 Design (CC-BY-4.0)*；⚠ 分支引用，版本待钉 |

## 待办

- [ ] heroicons / solar 的 `@master`/`@main` 分支引用改为解析后的具体 commit/tag 写回各 `_meta.json`（保证可重现）
- [ ] 各库目录内补充 LICENSE 副本，满足 MIT/Apache/ISC「保留许可声明」的字面要求
- [ ] 采集脚本 `collect_icons.py` 目前无 hash 校验；渲染端已在 `build-raw-assets.mjs` 的 `sanitizeSvg()` 做 SVG 消毒（剥 script/事件属性/javascript 链接/foreignObject）
