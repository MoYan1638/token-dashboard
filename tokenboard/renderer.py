# -*- coding: utf-8 -*-
"""渲染单文件 HTML 看板。"""

import html
import os
from datetime import datetime

from .report import fmt_int, fmt_tok

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, 'templates', 'dashboard.html')


def _esc(s):
    return html.escape(str(s))


def _load_template():
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def render(rep, source_note='', live_interval=0, generated_at=None):
    """生成完整 HTML 文本。

    rep             Report 实例
    source_note     页脚补充说明（可空）
    live_interval   大于 0 时页面自动刷新（秒）
    generated_at    datetime，不传则取当前时间
    """
    at = generated_at or datetime.now()
    gen = at.strftime('%Y-%m-%d %H:%M:%S')

    # ---- KPI ----
    kpis = ''.join([
        _kpi(fmt_int(rep.total_req), '总请求数',
             '%d 个会话' % rep.session_count),
        _kpi(fmt_tok(rep.total_in), '输入 Token', '含缓存命中'),
        _kpi(fmt_tok(rep.total_out), '输出 Token', '含推理 token'),
        _kpi(fmt_tok(rep.total_cache), '缓存命中',
             '命中率 %.1f%%' % rep.hit_rate),
        _kpi(fmt_tok(rep.total_tokens), '合计 Token',
             '%d 天 · %d 个来源' % (rep.day_count, len(rep.sources))),
        _kpi(fmt_tok(rep.total_think), '推理 Token',
             '占输出 %.0f%%' % (rep.total_think / rep.total_out * 100
                              if rep.total_out else 0)),
    ])

    # ---- 来源表 ----
    srows = []
    for name, sv in rep.sorted_sources():
        tot = sv['in'] + sv['out']
        p = sv.get('path') or ''
        home = os.path.expanduser('~')
        if p and home and home in p:
            p = p.replace(home, '~')
        srows.append(
            '<tr><td class="l"><b>%s</b></td>'
            '<td class="l path" data-label="日志目录">%s</td>'
            '<td data-label="请求">%s</td><td data-label="输入">%s</td>'
            '<td data-label="输出">%s</td><td data-label="缓存命中">%s</td>'
            '<td data-label="会话">%d</td>'
            '<td data-label="占比">%s</td></tr>'
            % (_esc(name), _esc(p or '—'), fmt_int(sv['req']),
               fmt_tok(sv['in']), fmt_tok(sv['out']), fmt_tok(sv['cache']),
               len(sv['sess']),
               _bar(tot / max(1, rep.total_tokens) * 100)))
    src_table = ''.join(srows) or _empty(8)

    # ---- 模型表 ----
    mrows = []
    for mname, mv in rep.sorted_models():
        tot = mv['in'] + mv['out']
        mrows.append(
            '<tr><td class="l">%s</td>'
            '<td data-label="请求">%s</td><td data-label="输入">%s</td>'
            '<td data-label="输出">%s</td><td data-label="缓存命中">%s</td>'
            '<td data-label="合计">%s</td>'
            '<td data-label="占比">%s</td><td data-label="费用">¥%.2f</td></tr>'
            % (_esc(mname), fmt_int(mv['req']), fmt_tok(mv['in']),
               fmt_tok(mv['out']), fmt_tok(mv['cache']), fmt_tok(tot),
               _bar(tot / max(1, rep.total_tokens) * 100),
               rep.model_cost(mname)))
    model_table = ''.join(mrows) or _empty(8)

    # ---- 每日趋势 ----
    days = rep.recent_days(40)
    mx = max([rep.days[d]['in'] + rep.days[d]['out'] for d in days] or [1])
    dcols = []
    for d in days:
        v = rep.days[d]
        h = (v['in'] + v['out']) / mx * 100
        ch = (v['cache'] / max(1, v['in'])) * h
        dcols.append(
            '<div class="dc" title="%s&#10;合计 %s&#10;缓存命中 %s&#10;请求 %d">'
            '<div class="db" style="height:%.1f%%">'
            '<i style="height:%.1f%%"></i></div><span>%s</span></div>'
            % (d, fmt_int(v['in'] + v['out']), fmt_int(v['cache']), v['req'],
               max(h, 1), ch, d[5:]))
    daily = ''.join(dcols) or '<div class="empty">暂无时间数据</div>'

    # ---- 会话表 ----
    qrows = []
    for sid, qv in rep.sorted_sessions(20):
        qrows.append(
            '<tr><td class="l mono">%s</td><td class="l">%s</td>'
            '<td class="l" data-label="来源">%s</td>'
            '<td data-label="请求">%s</td><td data-label="输入">%s</td>'
            '<td data-label="输出">%s</td><td data-label="合计">%s</td></tr>'
            % (_esc(sid[:16]), _esc(qv['model']), _esc(qv['src']),
               fmt_int(qv['req']), fmt_tok(qv['in']), fmt_tok(qv['out']),
               fmt_tok(qv['in'] + qv['out'])))
    sess_table = ''.join(qrows) or _empty(7)

    # ---- 页脚来源清单 ----
    lines = []
    for name, sv in rep.sorted_sources():
        p = sv.get('path') or ''
        home = os.path.expanduser('~')
        if p and home and home in p:
            p = p.replace(home, '~')
        lines.append('%s · %s 条%s' % (name, fmt_int(sv['req']),
                                      (' · ' + p) if p else ''))
    sources_html = ('共 %d 个来源解析到用量数据：<br>%s'
                    % (len(lines), '<br>'.join(_esc(x) for x in lines))
                    ) if lines else '未解析到任何用量数据'

    page = _load_template()
    snapshot_note, live_tag = _mode_blocks(live_interval, gen)

    for k, v in [
        ('__GEN__', gen), ('__KPIS__', kpis), ('__SRC_TABLE__', src_table),
        ('__MODEL_TABLE__', model_table), ('__DAILY__', daily),
        ('__SESS_TABLE__', sess_table), ('__SOURCES__', sources_html),
        ('__SOURCE_NOTE__', _esc(source_note) if source_note else ''),
        ('__SNAPSHOT__', snapshot_note), ('__LIVE_TAG__', live_tag),
        ('__COST__', '%.2f' % rep.est_cost),
        ('__YEAR__', str(datetime.now().year)),
    ]:
        page = page.replace(k, v)

    if live_interval > 0:
        page = page.replace(
            '</body>',
            '<script>setInterval(function(){location.reload()},%d)</script>'
            '\n</body>' % (live_interval * 1000))
    return page


def _kpi(value, label, sub=''):
    """KPI 卡片。注意 kv 只写一次——前端数字滚动会接管这个节点。"""
    return ('<div class="kpi"><div class="kv">%s</div><div class="kl">%s</div>'
            '<div class="ks">%s</div></div>'
            % (_esc(value), _esc(label), _esc(sub)))


def _bar(pct):
    """占比条。宽度内联写死一次，前端只做动画不重写数值。"""
    return ('<div class="bar" role="img" aria-label="占比 %.1f%%">'
            '<i style="width:%.1f%%"></i></div>' % (pct, pct))


def _empty(colspan):
    return '<tr><td colspan="%d" class="l">暂无数据</td></tr>' % colspan


def _mode_blocks(live_interval, gen):
    """返回 (快照提示条, 实时标识)。两者互斥，由模板中的标记控制显示。"""
    if live_interval > 0:
        tag = ('<span class="live-tag">实时扫描中 · 每 %d 秒刷新</span>'
               % live_interval)
        return '', tag
    note = ('<div class="snapshot-note"><b>这是静态快照</b>，'
            '数据冻结于 %s，不会自动更新。需要实时数据请运行 '
            '<code>python -m tokenboard serve</code>，'
            '并通过 <code>http://127.0.0.1:8787/</code> 访问。'
            '</div>' % gen)
    return note, ''
