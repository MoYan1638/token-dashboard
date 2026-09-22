# 贡献指南

感谢你愿意参与改进。这个项目很小，规则也简单。

## 最快的贡献方式：加一个 Agent

如果你用的 Agent 还没被支持，在 `tokenboard/sources.py` 的 `SOURCES` 里加一条即可：

```python
('myagent', 'My Agent', [
    os.path.join(HOME, '.myagent', 'logs'),
]),
```

然后验证：

```bash
python -m tokenboard sources -v
```

如果探测到了文件但解析不出用量数据，说明字段名比较特殊。可以先看看日志长什么样：

```bash
python -c "
import json
with open('你的日志.jsonl', encoding='utf-8') as f:
    for i, line in enumerate(f):
        print(json.dumps(json.loads(line), ensure_ascii=False, indent=2)[:1500])
        if i >= 1: break
"
```

如果里面的字段名确实不在 `tokenboard/parser.py` 的候选集合里，补进去就好。

## 提交规范

- 一个提交只做一件事
- 提交信息用中文或英文都行，说清「做了什么」和「为什么」
- PR 前请确保 `python -m compileall -q tokenboard` 无报错

## 代码风格

- 只用标准库，不引入第三方依赖
- 函数保持短小，关键逻辑写中文注释
- 面向用户的文案用中文

## 报告问题

提 issue 时请附上：

1. 操作系统与 Python 版本
2. 出问题的 Agent 名称
3. 运行的完整命令
4. 报错信息或截图

**注意：粘贴日志片段前请先脱敏**，把路径里的用户名、API Key 之类的敏感信息去掉。

## 不接受的方向

- 任何形式的联网上报、遥测、云端同步
- 引入第三方依赖（除非有非常充分的理由）
- 改变「纯本地、零依赖」这个基本定位

这是项目的底线，请理解。

---

by MoYan
