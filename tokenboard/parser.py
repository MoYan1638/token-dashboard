# -*- coding: utf-8 -*-
"""从各家 Agent 的日志中抽取 token 用量。

策略：不做 schema 硬编码，而是按「候选键名」递归下钻 JSON，
这样新增 Agent 或字段改名时通常无需改代码。
"""

import os
import json
from datetime import datetime

# ---------------------------------------------------------------- 候选键名
IN_KEYS = (
    'input_tokens', 'prompt_tokens', 'inputTokens', 'promptTokens',
    'input_token_count', 'prompt_token_count',
)
OUT_KEYS = (
    'output_tokens', 'completion_tokens', 'outputTokens', 'completionTokens',
    'output_token_count', 'completion_token_count',
)
CACHE_KEYS = (
    'cache_read_input_tokens', 'prompt_cache_hit_tokens', 'cached_tokens',
    'cacheReadInputTokens', 'cache_read_tokens', 'cachedTokens',
    'cacheReadTokens', 'cache_hit_tokens', 'cacheReadInputTokenCount',
)
THINK_KEYS = (
    'completion_thinking_tokens', 'reasoning_tokens', 'thinking_tokens',
    'completionThinkingTokens', 'reasoningTokens', 'reasoning_token_count',
)
MODEL_KEYS = (
    'model', 'model_name', 'modelName', 'model_id', 'modelId',
    'requestModelName', 'model_slug',
)
TIME_KEYS = (
    'timestamp', 'ts', 'time', 'created_at', 'createdAt', 'date',
    'created', 'event_time',
)

MAX_DEPTH = 6


def deep_find(obj, keys, depth=0):
    """递归查找第一个命中的键，返回其数值（非零才算命中）。"""
    if depth > MAX_DEPTH or obj is None:
        return None
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, (int, float)) and v:
                return v
            # 有些实现把数值写成字符串
            if isinstance(v, str) and v.isdigit() and int(v):
                return int(v)
        for v in obj.values():
            r = deep_find(v, keys, depth + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find(v, keys, depth + 1)
            if r is not None:
                return r
    return None


def deep_find_str(obj, keys, depth=0):
    if depth > MAX_DEPTH or obj is None:
        return None
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in obj.values():
            r = deep_find_str(v, keys, depth + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find_str(v, keys, depth + 1)
            if r is not None:
                return r
    return None


def norm_ts(v):
    """把各种时间表示统一成 Unix 秒。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if v > 1e12:      # 毫秒
            return float(v) / 1000.0
        if v > 1e9:       # 秒
            return float(v)
        return None
    if isinstance(v, str):
        s = v.strip()
        if s.replace('.', '', 1).isdigit():
            return norm_ts(float(s))
        s2 = s.replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(s2).timestamp()
        except Exception:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                return datetime.strptime(s[:19], fmt).timestamp()
            except Exception:
                continue
    return None


def extract(obj):
    """从一条日志对象里抽取用量。抽不到返回 None。"""
    if not isinstance(obj, dict):
        return None

    inp = deep_find(obj, IN_KEYS)
    out = deep_find(obj, OUT_KEYS)
    if not inp and not out:
        return None
    inp = int(inp or 0)
    out = int(out or 0)
    if inp <= 0 and out <= 0:
        return None

    cache = int(deep_find(obj, CACHE_KEYS) or 0)
    think = int(deep_find(obj, THINK_KEYS) or 0)
    model = deep_find_str(obj, MODEL_KEYS) or 'unknown'
    ts = norm_ts(deep_find(obj, TIME_KEYS))

    # 缓存命中不可能大于输入
    if cache > inp:
        cache = inp

    return {
        'in': inp, 'out': out, 'cache': cache, 'think': think,
        'model': model, 'ts': ts,
    }


def parse_file(path, source_label):
    """解析单个文件，返回记录列表。兼容 jsonl 与整份 JSON。"""
    recs = []
    dirname = os.path.dirname(path)
    ws = os.path.basename(dirname) or source_label
    sess = os.path.basename(path).rsplit('.', 1)[0]

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            head = fh.read(1)
            fh.seek(0)
            if head == '[':
                # 整份 JSON 数组
                try:
                    arr = json.load(fh)
                except Exception:
                    return recs
                items = arr if isinstance(arr, list) else [arr]
                for it in items:
                    r = extract(it)
                    if r:
                        r.update(src=source_label, ws=ws, sess=sess,
                                 path=dirname)
                        recs.append(r)
                return recs

            # jsonl：逐行，先做廉价预筛再解析
            hint = ('_tokens', 'Tokens', 'token_count', 'tokenCount',
                    '"usage"', 'usage"')
            for line in fh:
                if len(line) < 24:
                    continue
                if not any(h in line for h in hint):
                    continue
                line = line.strip()
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                items = obj if isinstance(obj, list) else [obj]
                for o in items:
                    r = extract(o)
                    if r:
                        r.update(src=source_label, ws=ws, sess=sess,
                                 path=dirname)
                        recs.append(r)
    except OSError:
        pass
    return recs


def parse_files(files, source_label, progress=None):
    """解析一批文件。progress(已处理数, 总数) 可选回调。"""
    all_recs = []
    total = len(files)
    for i, p in enumerate(files, 1):
        all_recs += parse_file(p, source_label)
        if progress:
            progress(i, total)
    return all_recs
