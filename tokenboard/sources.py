# -*- coding: utf-8 -*-
"""各 AI Agent 的日志来源定义与自动探测。

新增一个 Agent 只需在 SOURCES 里加一条：
    (source_id, display_name, [候选根目录], [文件名匹配模式])
"""

import os

HOME = os.path.expanduser('~')

# Windows 常见 AppData 位置
LOCAL = os.environ.get('LOCALAPPDATA', os.path.join(HOME, 'AppData', 'Local'))
ROAMING = os.environ.get('APPDATA', os.path.join(HOME, 'AppData', 'Roaming'))

# 遍历时跳过的目录，避免扫进依赖、缓存、二进制
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', 'cache', 'Cache', 'Caches',
    'blobs', 'binaries', 'extensions', 'plugins', 'skills', 'logs',
    'media', 'file-history', 'shell-snapshots', 'traces',
}

# ---------------------------------------------------------------- 来源定义
# 结构：(id, 显示名, [根目录候选...])
SOURCES = [
    ('workbuddy', 'WorkBuddy', [
        os.path.join(HOME, '.workbuddy', 'projects'),
    ]),
    ('claude', 'Claude Code', [
        os.path.join(HOME, '.claude', 'projects'),
        os.path.join(HOME, '.config', 'claude', 'projects'),
    ]),
    ('codex', 'Codex CLI', [
        os.path.join(HOME, '.codex', 'sessions'),
        os.path.join(HOME, '.codex'),
    ]),
    ('openclaw', 'OpenClaw', [
        os.path.join(HOME, '.openclaw'),
    ]),
    ('cursor', 'Cursor', [
        os.path.join(HOME, '.cursor'),
        os.path.join(ROAMING, 'Cursor', 'User', 'globalStorage'),
    ]),
    ('gemini', 'Gemini CLI', [
        os.path.join(HOME, '.gemini', 'tmp'),
        os.path.join(HOME, '.gemini'),
    ]),
    ('continue', 'Continue', [
        os.path.join(HOME, '.continue'),
    ]),
    ('aider', 'Aider', [
        os.path.join(HOME, '.aider'),
    ]),
    ('cline', 'Cline', [
        os.path.join(ROAMING, 'Code', 'User', 'globalStorage',
                     'saoudrizwan.claude-dev', 'tasks'),
    ]),
    ('roo', 'Roo Code', [
        os.path.join(ROAMING, 'Code', 'User', 'globalStorage',
                     'rooveterinaryinc.roo-cline', 'tasks'),
    ]),
    ('windsurf', 'Windsurf', [
        os.path.join(HOME, '.codeium', 'windsurf'),
        os.path.join(ROAMING, 'Windsurf', 'User', 'globalStorage'),
    ]),
    ('kilo', 'Kilo Code', [
        os.path.join(ROAMING, 'Code', 'User', 'globalStorage',
                     'kilocode.kilo-code', 'tasks'),
    ]),
]

# 允许的文件名后缀
LOG_SUFFIXES = ('.jsonl', '.ndjson')
JSON_SUFFIXES = ('.json',)


def _is_log_file(name):
    """判断是否是可能含用量数据的日志文件。"""
    low = name.lower()
    if low.endswith(LOG_SUFFIXES):
        return True
    # 整份 json：只收文件名里带 session/conversation/chat/usage 的，
    # 避免把 config.json 这类配置读进来
    if low.endswith(JSON_SUFFIXES):
        return any(k in low for k in
                   ('session', 'conversation', 'chat', 'usage', 'message'))
    return False


def collect_files(root, limit=8000, min_size=180):
    """递归收集日志文件。跳过无关目录与过小的文件。"""
    out = []
    if os.path.isfile(root):
        return [root] if _is_log_file(os.path.basename(root)) else []
    if not os.path.isdir(root):
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith('.')]
        for fn in filenames:
            if not _is_log_file(fn):
                continue
            p = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(p) < min_size:
                    continue
            except OSError:
                continue
            out.append(p)
        if len(out) > limit:
            break
    return out


def discover(extra_paths=None):
    """探测日志来源。

    参数
        extra_paths: 用户手动的目录列表；给了就只用这些。

    返回
        [(source_id, 显示名, [文件路径...]), ...]
        只包含实际找到文件的来源。
    """
    if extra_paths:
        files = []
        for p in extra_paths:
            files += collect_files(os.path.expanduser(p))
        files = sorted(set(files))
        return [('custom', '自定义路径', files)] if files else []

    found = []
    for sid, label, roots in SOURCES:
        files = []
        for r in roots:
            files += collect_files(r)
        files = sorted(set(files))
        if files:
            found.append((sid, label, files))
    return found


def source_path_of(filepath, source_label):
    """从一个日志文件路径反推它所属的根目录（用于展示）。"""
    d = os.path.dirname(filepath)
    parts = d.replace('\\', '/').split('/')
    for marker in ('projects', 'sessions', 'tasks'):
        if marker in parts:
            i = parts.index(marker)
            return '/'.join(parts[:i + 1])
    return d
