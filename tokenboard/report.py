# -*- coding: utf-8 -*-
"""把请求记录汇总成多维度统计。"""

from collections import defaultdict
from datetime import datetime

from .pricing import PriceTable


def fmt_int(n):
    return '{:,}'.format(int(n))


def fmt_tok(n):
    """中文语境下的大数简写：亿 / 万。"""
    n = int(n)
    if n >= 1e8:
        return '%.2f 亿' % (n / 1e8)
    if n >= 1e4:
        return '%.1f 万' % (n / 1e4)
    return fmt_int(n)


class Report:
    """一次汇总的结果。"""

    def __init__(self, recs, price_overrides=None):
        self.recs = recs
        self.prices = PriceTable(price_overrides)

        self.total_req = len(recs)
        self.total_in = sum(r['in'] for r in recs)
        self.total_out = sum(r['out'] for r in recs)
        self.total_cache = sum(r['cache'] for r in recs)
        self.total_think = sum(r['think'] for r in recs)

        self.models = defaultdict(lambda: {'req': 0, 'in': 0, 'out': 0,
                                           'cache': 0, 'think': 0})
        self.sources = defaultdict(lambda: {'req': 0, 'in': 0, 'out': 0,
                                            'cache': 0, 'sess': set(),
                                            'path': ''})
        self.days = defaultdict(lambda: {'req': 0, 'in': 0, 'out': 0,
                                         'cache': 0})
        self.sessions = defaultdict(lambda: {'req': 0, 'in': 0, 'out': 0,
                                             'model': '', 'src': '',
                                             'ws': ''})
        self._build()

    def _build(self):
        for r in self.recs:
            m = self.models[r['model']]
            m['req'] += 1
            m['in'] += r['in']
            m['out'] += r['out']
            m['cache'] += r['cache']
            m['think'] += r['think']

            s = self.sources[r['src']]
            s['req'] += 1
            s['in'] += r['in']
            s['out'] += r['out']
            s['cache'] += r['cache']
            s['sess'].add(r['sess'])
            if r.get('path') and not s['path']:
                s['path'] = r['path']

            if r['ts']:
                d = self.days[
                    datetime.fromtimestamp(r['ts']).strftime('%Y-%m-%d')]
                d['req'] += 1
                d['in'] += r['in']
                d['out'] += r['out']
                d['cache'] += r['cache']

            q = self.sessions[r['sess']]
            q['req'] += 1
            q['in'] += r['in']
            q['out'] += r['out']
            q['model'] = r['model']
            q['src'] = r['src']
            q['ws'] = r['ws']

    # ------------------------------------------------------------ 派生指标
    @property
    def hit_rate(self):
        return (self.total_cache / self.total_in * 100) if self.total_in else 0

    @property
    def total_tokens(self):
        return self.total_in + self.total_out

    @property
    def day_count(self):
        return len(self.days)

    @property
    def session_count(self):
        return len(self.sessions)

    @property
    def est_cost(self):
        return sum(self.model_cost(m) for m in self.models)

    def model_cost(self, model):
        mv = self.models[model]
        return self.prices.est_cost(model, mv['in'], mv['out'], mv['cache'])

    def sorted_models(self):
        return sorted(self.models.items(),
                      key=lambda kv: -(kv[1]['in'] + kv[1]['out']))

    def sorted_sources(self):
        return sorted(self.sources.items(),
                      key=lambda kv: -(kv[1]['in'] + kv[1]['out']))

    def sorted_sessions(self, limit=None):
        out = sorted(self.sessions.items(),
                     key=lambda kv: -(kv[1]['in'] + kv[1]['out']))
        return out[:limit] if limit else out

    def recent_days(self, limit=40):
        return sorted(self.days.keys())[-limit:]

    def summary(self):
        """给 API 用的精简摘要。"""
        return {
            'requests': self.total_req,
            'input_tokens': self.total_in,
            'output_tokens': self.total_out,
            'cached_tokens': self.total_cache,
            'total_tokens': self.total_tokens,
            'cache_hit_rate': round(self.hit_rate, 2),
            'est_cost_cny': round(self.est_cost, 2),
            'sessions': self.session_count,
            'days': self.day_count,
            'sources': sorted(self.sources.keys()),
            'models': sorted(self.models.keys()),
        }
