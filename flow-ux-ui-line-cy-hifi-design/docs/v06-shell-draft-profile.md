# V06-③ 壳子 draft 档改动清单

> 状态：草案待用户审。目标：同一壳子两种解锁深度——预览版（draft 档）纯看图+旁批，编辑版（附加A转化）解锁编辑。

## 改动项

1. **绑定本地文件弹窗延后**：现在首开即弹，改为打开不弹；触发点移到"会写盘的动作"——保存、批注保存、导出。纯预览的客户全程不见弹窗。
2. **编辑入口隐藏**：draft 档下「去编辑」按钮、口令入口、编辑相关工具项不渲染（profile 注入 body 级类如 `ed-draft`，CSS 控制隐藏；不删能力，转化版去掉 draft 标记即恢复）。
3. **批注面板保留、默认收起**：点「批」展开；批注的写盘动作同样走延后弹窗。批注内容由后置旁批技能预写（功能逻辑旁批），客户可续批。
4. **build.py 注册 `--profile draft`**：assets/project-profiles/ 新增 draft 声明（注入 `ed-draft` 类+标题可加"设计稿预览"前缀）。profile 机制已存在，注册即可。
5. **不动**：页面树导航、机型切换、状态持久化、导出、命名空间隔离。

## 验收（实施时全做）

- draft 档打开：零弹窗、零编辑入口可见、页面树切换正常、机型切换正常、批注可展开查看
- 延后弹窗：点保存/批注保存时弹绑定引导，取消则不写盘
- 编辑版（无 draft 档）行为零回归

## 多风格聚合：目录页（每风格一个包，链接聚合）

多风格比稿（N 个风格各出代表页）不合并进一个产物——**每风格各自 build 一个完整预览包 HTML**（各自独立可开、互不干扰、无 id 冲突），聚合只需一个**静态目录页**（列出各风格包链接）。模板（复制到工程根 `build/风格目录.html`，改链接即可）：

```html
<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>风格比稿目录</title>
<style>body{font-family:system-ui;margin:40px;background:#f7f7f8}h1{font-size:20px}
a{display:block;padding:14px 18px;margin:10px 0;background:#fff;border:1px solid #e5e5ea;border-radius:10px;
color:#1c1c1e;text-decoration:none;font-size:15px}a:hover{border-color:#7c5cff}</style></head><body>
<h1>风格比稿目录</h1>
<a href="微信WeUI.html">微信 WeUI</a>
<a href="扁平2.0.html">扁平 2.0</a>
</body></html>
```

注意：禁止把多个风格的页面 DOM 合并进一个产物文档（data-screen 全局唯一会跨风格撞车，且风格切换是文件级的事，不是 DOM 级的事）。
