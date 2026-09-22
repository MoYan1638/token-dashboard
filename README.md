# Token 消耗看板

给 AI Agent 用户的本机用量分析工具。扫描各家 Agent 的会话日志，统计 **Token 消耗、缓存命中率、费用估算**，输出一张单文件看板。

**纯本地运行，不联网、不上传。** 日志只在本机被读取和计算，一个字节都不会离开你的电脑。

---

## 为什么做这个

用 AI Agent 的时候，很容易不清楚自己到底烧了多少 token、钱花在哪。各家平台要么不给明细，要么只能看单次会话。

这个工具直接读你本机的日志，把多个 Agent 的用量汇总到一张表里——用得最多的模型、缓存省了多少、哪个会话最耗钱，一眼看清。

---

## 特性

| | |
|---|---|
| **多 Agent 通用** | 自动探测 WorkBuddy / Claude Code / Codex / Cursor / Gemini CLI 等 12 种日志来源 |
| **零依赖** | 只用 Python 标准库，不需要 pip install 任何东西 |
| **完全离线** | 不发起任何网络请求，数据不出本机 |
| **实时刷新** | 内置本地服务，页面每 15 秒自动更新 |
| **响应式** | 电脑横屏、手机竖屏都能正常阅读 |
| **暗色模式** | 跟随系统深浅色，无需手动切换 |
| **渐进增强** | 关掉 JS 页面照样完整可读，动画只是加分项 |
| **可扩展** | 新增一个 Agent 只需在 `sources.py` 加一条配置 |

---

## 快速开始

需要 Python 3.8 或更高版本。

```bash
# 1. 获取代码
git clone https://github.com/MoYan1638/token-dashboard.git
cd token-dashboard

# 2. 启动实时看板（浏览器会自动打开）
python -m tokenboard
```

打开后你会看到 `http://127.0.0.1:8787/`，页面上有绿色的「实时扫描中」标识，数据每 15 秒自动刷新。

Windows 用户也可以直接双击 `start.bat`。

---

## 常用命令

```bash
# 启动实时看板（默认端口 8787）
python -m tokenboard

# 换端口、改刷新间隔（0 = 不自动刷新）
python -m tokenboard --port 9000 --interval 30

# 生成静态快照，适合分享或存档
python -m tokenboard scan -o dashboard.html

# 看看探测到了哪些日志来源
python -m tokenboard sources -v

# 手动指定日志目录（自动探测没覆盖到的 Agent）
python -m tokenboard --path "D:/some-agent/logs"

# 覆盖价格表
python -m tokenboard --price-config my-prices.json
```

---

## 支持的 Agent

启动时会自动扫描下列位置，**存在哪个就统计哪个**，不存在的直接跳过。

| Agent | 日志位置 |
|---|---|
| WorkBuddy | `~/.workbuddy/projects` |
| Claude Code | `~/.claude/projects` |
| Codex CLI | `~/.codex/sessions` |
| OpenClaw | `~/.openclaw` |
| Cursor | `~/.cursor` |
| Gemini CLI | `~/.gemini/tmp` |
| Continue | `~/.continue` |
| Aider | `~/.aider` |
| Cline | VS Code globalStorage |
| Roo Code | VS Code globalStorage |
| Windsurf | `~/.codeium/windsurf` |
| Kilo Code | VS Code globalStorage |

没有你要的？在 `tokenboard/sources.py` 的 `SOURCES` 里加一行就行：

```python
('myagent', 'My Agent', [
    os.path.join(HOME, '.myagent', 'logs'),
]),
```

字段名不一样也没关系——解析器用的是「候选键名 + 递归下钻」策略，只要用量数据里含有 `input_tokens` / `prompt_tokens` / `inputTokens` 之类的常见字段名，就能自动识别。

---

## 看板包含什么

- **总览** — 请求数、输入/输出 Token、缓存命中、推理 Token
- **来源对比** — 每个 Agent 各自的用量与占比
- **模型分布** — 按模型拆解，含费用估算
- **每日趋势** — 柱状图展示用量变化
- **会话 Top 20** — 最耗 token 的会话排行

页面上还有 `/api/data` 接口，返回 JSON 摘要，方便接你自己的脚本：

```bash
curl http://127.0.0.1:8787/api/data
```

---

## 界面说明

页面配色以梅子紫 `#7a3b57` 与珊瑚粉 `#ff6b81` 为主，深浅两套主题自动跟随系统。

动效全部是纯 CSS + 原生 JS，**没有引入任何图标库或动画库**，页面里也不含任何外部请求。

一个刻意的取舍：所有动画都是渐进增强的。CSS 里默认写的就是最终可见状态，
只有脚本跑起来、给 `<html>` 加上 `js-anim` 之后，才启用「从 0 开始」的初始态。
这样即使脚本加载失败、被 CSP 拦截，或者你直接把 HTML 存下来离线看，
内容也永远完整可见——不会出现白屏或半透明区块。

动画清单：

- KPI 数字从 0 缓动到目标值，结束时回写精确原值
- 占比条与每日趋势柱从零尺寸展开
- 各内容区块依次淡入上移
- 桌面端鼠标划过 KPI 卡片有跟随光晕
- 右上角刷新按钮，点击后重新扫描

如果系统开启了「减少动态效果」（`prefers-reduced-motion`），以上动画会全部跳过。

---

## 费用估算说明

费用是**估算值**，按公开单价折算，实际账单请以服务商为准。

价格表在 `tokenboard/pricing.py`，想改单价用配置文件覆盖：

```json
{
  "price_overrides": {
    "my-model": [2, 8, 0.4]
  }
}
```

格式是 `[输入价, 输出价, 缓存命中价]`，单位 **元 / 百万 token**。

计费规则：缓存命中的部分走缓存价，其余输入走输入价，输出走输出价。

---

## 项目结构

```
tokenboard/
├── __init__.py      版本信息
├── __main__.py      入口
├── cli.py           命令行解析
├── sources.py       各 Agent 日志位置定义 + 自动探测
├── parser.py        日志解析（候选键名 + 递归下钻）
├── report.py        多维度汇总
├── pricing.py       价格表与费用计算
├── renderer.py      HTML 渲染
├── server.py        本地 HTTP 服务
└── templates/
    └── dashboard.html   看板模板
```

---

## 常见问题

**页面上没有数据？**

先跑 `python -m tokenboard sources -v` 看有没有探测到日志。如果某个 Agent 不在列表里，用 `--path` 手动指定它的日志目录。

**"这是静态快照"的黄条是什么？**

说明你打开的是 `scan` 生成的 HTML 文件。静态快照的数据在生成时就固定了，不会更新。要看实时的请用 `python -m tokenboard` 启动服务。

**数据会上传吗？**

不会。代码里没有任何网络请求，唯一的网络行为是启动时打开本地浏览器（`127.0.0.1`）。

**为什么路径显示成 `~`？**

为了脱敏。页面上会用 `~` 替代你的用户目录，避免分享截图时暴露用户名。

---

## 许可

MIT License，详见 [LICENSE](LICENSE)。

by MoYan
