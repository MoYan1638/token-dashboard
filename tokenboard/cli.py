# -*- coding: utf-8 -*-
"""命令行入口。

    python -m tokenboard                 # 启动实时看板（推荐）
    python -m tokenboard scan            # 生成静态 HTML 快照
    python -m tokenboard sources         # 列出探测到的日志来源
    python -m tokenboard --help
"""

import argparse
import os
import sys

from . import __version__
from . import sources as S
from .parser import parse_files
from .report import Report, fmt_int, fmt_tok
from .renderer import render
from .pricing import load_overrides


def _add_common(p):
    p.add_argument('--path', '-p', action='append', default=None,
                   help='指定日志目录（可多次）；不传则自动探测')
    p.add_argument('--price-config', default=None,
                   help='自定义价格表 JSON，用于覆盖单价')
    p.add_argument('--quiet', '-q', action='store_true', help='静默模式')


def _cmd_sources(args):
    found = S.discover(args.path)
    if not found:
        print('未探测到任何日志来源。')
        print('可用 --path 手动指定，例如：')
        print('  python -m tokenboard sources --path "D:/my-agent/logs"')
        return 1
    print('探测到 %d 个日志来源：\n' % len(found))
    for sid, label, files in found:
        print('  [%s] %s' % (sid, label))
        print('        文件 %d 个' % len(files))
        root = S.source_path_of(files[0], label)
        home = os.path.expanduser('~')
        print('        目录 %s' % (root.replace(home, '~') if home in root
                                  else root))
        if args.verbose:
            for f in files[:5]:
                print('          - %s' % f)
            if len(files) > 5:
                print('          ... 其余 %d 个' % (len(files) - 5))
    return 0


def _collect(paths, quiet=False):
    found = S.discover(paths)
    recs, labels, skipped = [], [], []
    for sid, label, files in found:
        r = parse_files(files, label)
        if r:
            recs += r
            labels.append('%s(%d条)' % (label, len(r)))
        else:
            skipped.append(label)
    return recs, labels, skipped


def _cmd_scan(args):
    recs, labels, skipped = _collect(args.path, args.quiet)
    if not recs:
        print('未解析出任何 token 用量记录。')
        print('试试：python -m tokenboard sources  先看看有没有可用日志')
        return 2
    if skipped and not args.quiet:
        print('（%s 未解析到用量数据，已跳过）' % '、'.join(skipped))

    rep = Report(recs, load_overrides(args.price_config))
    out = args.out or 'token-dashboard.html'
    page = render(rep, source_note='本文件为静态快照，可通过 '
                                   'python -m tokenboard 启动实时版。')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)

    if args.json:
        import json
        jp = os.path.splitext(out)[0] + '.json'
        with open(jp, 'w', encoding='utf-8') as f:
            json.dump({'generated_at': rep.days and max(rep.days) or '',
                       'summary': rep.summary(),
                       'records': rep.recs}, f, ensure_ascii=False)
        print('JSON 已导出：%s' % jp)

    print('已生成：%s' % out)
    print('  来源 %s' % ' / '.join(labels))
    print('  请求 %s · 输入 %s · 输出 %s · 缓存 %s · 估算 ¥%.2f'
          % (fmt_int(rep.total_req), fmt_tok(rep.total_in),
             fmt_tok(rep.total_out), fmt_tok(rep.total_cache),
             rep.est_cost))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog='tokenboard',
        description='Token 消耗看板 —— 各 AI Agent 通用的本地用量分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例：\n'
               '  python -m tokenboard                 启动实时看板\n'
               '  python -m tokenboard scan -o out.html 生成静态快照\n'
               '  python -m tokenboard sources          查看探测到的日志\n')
    ap.add_argument('-V', '--version', action='version',
                    version='tokenboard %s' % __version__)
    sub = ap.add_subparsers(dest='cmd')

    ps = sub.add_parser('scan', help='生成静态 HTML 快照')
    ps.add_argument('-o', '--out', default=None, help='输出文件路径')
    ps.add_argument('--json', action='store_true', help='同时导出 JSON')
    _add_common(ps)

    pl = sub.add_parser('sources', help='列出探测到的日志来源')
    pl.add_argument('-v', '--verbose', action='store_true',
                    help='列出具体文件')
    _add_common(pl)

    # 默认（无子命令）启动服务
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--interval', type=int, default=15,
                    help='页面自动刷新秒数，0 表示关闭')
    ap.add_argument('--ttl', type=int, default=5,
                    help='服务端扫描缓存秒数')
    ap.add_argument('--no-open', action='store_true', help='不自动开浏览器')
    _add_common(ap)

    args = ap.parse_args(argv)

    if args.cmd == 'scan':
        return _cmd_scan(args)
    if args.cmd == 'sources':
        return _cmd_sources(args)

    from .server import serve
    serve(host=args.host, port=args.port, interval=args.interval,
          paths=args.path, ttl=args.ttl, open_browser=not args.no_open,
          price_cfg=args.price_config, quiet=args.quiet)
    return 0


if __name__ == '__main__':
    sys.exit(main())
