# -*- coding: utf-8 -*-
"""本地 HTTP 服务。页面每次请求都即时扫描，返回最新数据。"""

import json
import os
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import sources as S
from .parser import parse_files
from .report import Report
from .renderer import render
from .pricing import load_overrides

_STATE = {
    'recs': None,
    'at': None,
    'lock': threading.Lock(),
    'opts': {'paths': None, 'ttl': 5, 'interval': 15,
             'price_cfg': None, 'quiet': False},
}


def scan(force=False):
    """扫描全部来源，返回 (记录列表, 时间)。带 TTL 缓存。"""
    now = datetime.now()
    o = _STATE['opts']
    with _STATE['lock']:
        if (not force and _STATE['recs'] is not None and _STATE['at']
                and (now - _STATE['at']).total_seconds() < o['ttl']):
            return _STATE['recs'], _STATE['at']

        recs = []
        for sid, label, files in S.discover(o['paths']):
            recs += parse_files(files, label)
        _STATE['recs'] = recs
        _STATE['at'] = now
        return recs, now


def _build():
    recs, at = scan()
    if not recs:
        return None
    rep = Report(recs, load_overrides(_STATE['opts']['price_cfg']))
    return render(rep, live_interval=_STATE['opts']['interval'],
                  generated_at=at)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        if not _STATE['opts']['quiet']:
            print('  %s' % (fmt % args))

    def _send(self, body, ctype):
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ('/', '/index.html', '/dashboard'):
            try:
                page = _build()
            except Exception as e:
                page = ('<!DOCTYPE html><meta charset="utf-8">'
                        '<h1>扫描出错</h1><pre>%s</pre>' % e)
            if page is None:
                page = ('<!DOCTYPE html><meta charset="utf-8">'
                        '<h1>未探测到可用日志</h1>'
                        '<p>试试手动指定：<code>--path 你的日志目录</code></p>')
            self._send(page.encode('utf-8'), 'text/html; charset=utf-8')

        elif path == '/api/data':
            try:
                recs, at = scan(force=True)
                rep = Report(recs, load_overrides(_STATE['opts']['price_cfg']))
                body = json.dumps({
                    'generated_at': at.strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': rep.summary(),
                }, ensure_ascii=False, indent=2).encode('utf-8')
            except Exception as e:
                body = json.dumps({'error': str(e)},
                                  ensure_ascii=False).encode('utf-8')
            self._send(body, 'application/json; charset=utf-8')

        elif path == '/health':
            self._send(b'{"status":"ok"}', 'application/json')

        else:
            self.send_error(404)


def serve(host='127.0.0.1', port=8787, interval=15, paths=None, ttl=5,
          open_browser=True, price_cfg=None, quiet=False):
    o = _STATE['opts']
    o.update(paths=paths, ttl=ttl, interval=interval,
             price_cfg=price_cfg, quiet=quiet)

    recs, at = scan(force=True)
    url = 'http://%s:%d/' % (host, port)
    print('Token 看板已启动')
    print('  地址：%s' % url)
    print('  数据：%d 条记录（%s）' % (len(recs),
                                  at.strftime('%Y-%m-%d %H:%M:%S')))
    print('  刷新：%s' % ('每 %d 秒自动刷新' % interval if interval > 0
                        else '手动刷新'))
    print('  停止：Ctrl+C')
    if not recs:
        print('  提示：未解析到用量数据，可用 --path 指定日志目录')
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    srv = ThreadingHTTPServer((host, port), _Handler)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')
    finally:
        srv.server_close()
