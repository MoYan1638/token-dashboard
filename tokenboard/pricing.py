# -*- coding: utf-8 -*-
"""价格表。单位：元 / 百万 token，格式 [输入, 输出, 缓存命中]。

这张表用于「估算」费用，实际账单请以服务商为准。
用户可以在 config.json 里用 price_overrides 覆盖。
"""

import json
import os

DEFAULT_PRICE = [2, 8, 0.4]

# 按前缀匹配，长前缀优先（如 kimi-k3 会先于 kimi 命中）
BUILTIN_PRICE = {
    # DeepSeek
    'deepseek-v4-flash': [1, 4, 0.2],
    'deepseek-v4-pro': [2, 8, 0.5],
    'deepseek-v4': [2, 8, 0.5],
    'deepseek': [2, 8, 0.5],
    # 智谱 GLM
    'glm-5.3': [2, 8, 0.4],
    'glm-5.2': [0.8, 3.2, 0.16],
    'glm': [1, 4, 0.2],
    # 月之暗面 Kimi
    'kimi-k3': [30, 120, 3],
    'kimi': [1.5, 6, 0.3],
    # Anthropic Claude
    'claude-opus': [110, 550, 11],
    'claude-sonnet': [22, 110, 2.2],
    'claude-haiku': [6, 30, 0.6],
    'claude': [110, 550, 11],
    # OpenAI
    'gpt-5': [8, 40, 1],
    'gpt-4o': [18, 72, 2],
    'gpt-4o-mini': [1, 4, 0.1],
    'o3': [8, 40, 1],
    'o4-mini': [2, 8, 0.5],
    # Google
    'gemini-2.5-pro': [9, 36, 0.9],
    'gemini': [1.5, 6, 0.3],
    # 阿里通义
    'qwen-max': [9.6, 38.4, 1.9],
    'qwen': [2.4, 9.6, 0.48],
    # 腾讯混元
    'hy4': [4, 16, 0.8],
    'hy': [4, 16, 0.8],
    # MiniMax
    'minimax': [1, 5, 0.2],
    'm3': [1, 5, 0.2],
    # xAI
    'grok': [3, 15, 0.3],
}


class PriceTable:
    def __init__(self, overrides=None):
        self.table = dict(BUILTIN_PRICE)
        for k, v in (overrides or {}).items():
            if isinstance(v, (list, tuple)) and len(v) == 3:
                self.table[str(k).lower()] = [float(x) for x in v]
        self._keys = sorted(self.table, key=len, reverse=True)

    def of(self, model):
        n = (model or '').lower()
        for k in self._keys:
            if n.startswith(k):
                return self.table[k]
        return DEFAULT_PRICE

    def est_cost(self, model, in_tok, out_tok, cache_tok):
        """按输入/输出/缓存三档分别计价。"""
        p = self.of(model)
        billable_in = max(0, in_tok - cache_tok)
        return (billable_in / 1e6 * p[0]
                + out_tok / 1e6 * p[1]
                + cache_tok / 1e6 * p[2])


def load_overrides(path):
    """从配置目录读取 price_overrides。"""
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        ov = cfg.get('price_overrides') or {}
        return ov if isinstance(ov, dict) else {}
    except Exception:
        return {}
