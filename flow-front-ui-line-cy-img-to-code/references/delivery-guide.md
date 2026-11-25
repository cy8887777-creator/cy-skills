# 交付与受控修改（references）——第 6/7 步细则

## §1 交付报告（第 6 步）

- 产物清单：`index.html`、`assets/`、`layout_brief.txt`、
  `layout.json`、`styles.json`、`assets_report.json`、
  `preview_desktop.png` / `preview_mobile.png` / `preview_wide.png`、
  `verify_report.json`、`_diff_sheet.png`、`_asset_render_check_*.png`；
- 技术栈与档位：实际使用的栈（应为第 1 步用户所选项）与档位；
- 素材使用情况：每个素材用了透明图 / 原图 / 降级（SVG 或占位），
  含校准阶段被自动精化（BOX-CLIPPED / BOX-LOOSE）的素材清单与
  **verdict 非 OK 的处置记录**；图标逐个标注来源路径：
  `[ICON-LIB: 集合:名称]` / `[BITMAP: asset_N]` / `[CSS-NATIVE]`；
- 断言结果（PASS，或经 2 轮修正后仍 FAIL 的项）；
- **数据纪律**：报告中的所有数字只允许引用 verify_report.json /
  styles.json / assets_report.json 的既有数据，禁止模型手写或心算
  统计；
- diff 对照结论：逐带对照结果（无差异 / 修正了哪些差异），引用带
  编号；
- **预览口径（固定输出，不可省略）**：产物是无外壳的 body 画布
  （供 Figma 导入），浏览器预览请用画布等宽视口（宽视口/RTL 页面下
  body 会贴边属正常形态，`preview_wide.png` 已验证整体对齐）。

## §2 受控修改轮（第 7 步）

用户对已交付产物提修改（"按钮大一点""文案改成 X"）时：
1. **不重跑管线**——layout.json 与 assets/ 的校准结果仍有效，直接
   从第 4 步定点修改开始（精确字符串替换，不整文件重写）；
2. 只有修改涉及**新增/移动素材**时才补标 assets.json 重跑第 3 步
   （旧 layout.json 被覆盖属预期；同目录重跑为增量模式，见
   calibration-guide §2）；
3. 每轮修改完**重跑第 5 步同一命令**复检（含目检）；
4. 禁止以修改为由整页重新生成——那是放弃已校准的几何基准。
