"""Замер страницы в headless Chromium: запросы, вес, отрисовка формул.

Нужен playwright (в зависимости сайта не входит, ставится отдельно):
    pip install playwright && playwright install chromium

Запуск:
    python scripts/measure_page.py <каталог_сайта> <страница> <режим> [скриншот.png]

Режимы работы внешних (не localhost) запросов:
    pass  — пропускать (обычная работа, CDN доступен);
    abort — сразу обрывать (CDN недоступен: DNS не резолвится, порт закрыт);
    hang  — не отвечать (CDN «висит»: фильтрация, потеря пакетов).
Печатает одну строку JSON с результатами.
"""

from __future__ import annotations

import functools
import gzip
import http.server
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Request, Route, sync_playwright

MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1366, "height": 900}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def serve(directory: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def measure(site: Path, page_path: str, mode: str, shot: str | None) -> dict[str, Any]:
    server, port = serve(site)
    url = f"http://127.0.0.1:{port}/{page_path}"
    requests: list[dict[str, Any]] = []
    held: list[Route] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=MOBILE if shot and "mobile" in shot else DESKTOP)
        page = ctx.new_page()

        def route(r: Route) -> None:
            if r.request.url.startswith("http://127.0.0.1"):
                r.continue_()
            elif mode == "abort":
                r.abort("namenotresolved")
            elif mode == "hang":
                held.append(r)  # ответа не будет
            else:
                r.continue_()

        page.route("**/*", route)

        def on_finished(req: Request) -> None:
            resp = req.response()
            size = 0
            gz = 0
            if resp is not None:
                try:
                    body = resp.body()
                    size = len(body)
                    gz = len(gzip.compress(body, 6))
                except Exception:  # тело недоступно (редирект и т.п.)
                    pass
            requests.append(
                {
                    "url": req.url,
                    "external": not req.url.startswith("http://127.0.0.1"),
                    "bytes": size,
                    "gzip": gz,
                    "failed": False,
                }
            )

        page.on("requestfinished", on_finished)
        page.on(
            "requestfailed",
            lambda req: requests.append(
                {
                    "url": req.url,
                    "external": not req.url.startswith("http://127.0.0.1"),
                    "bytes": 0,
                    "gzip": 0,
                    "failed": True,
                }
            ),
        )

        t0 = time.monotonic()
        try:
            page.goto(url, wait_until="load", timeout=45_000)
            load_s: float | None = round(time.monotonic() - t0, 2)
        except Exception:
            load_s = None  # load так и не наступил
        # Даём MathJax время отрисовать формулы.
        page.wait_for_timeout(3000)
        math_total = page.locator(".arithmatex").count()
        math_rendered = page.locator(".arithmatex mjx-container").count()
        # body может так и не появиться, если отрисовку держит CSS из <head>.
        font = page.evaluate(
            "document.body ? getComputedStyle(document.body).fontFamily"
            " : '<страница не отрисована>'"
        )
        fcp = page.evaluate(
            "(performance.getEntriesByName('first-contentful-paint')[0] || {}).startTime ?? null"
        )
        if shot and fcp is not None:
            page.screenshot(path=shot, full_page=False, timeout=10_000)
        # Отпускаем «зависшие» запросы, иначе браузер не закроется.
        for r in held:
            r.abort()
        browser.close()
    server.shutdown()

    external = [r for r in requests if r["external"]]
    return {
        "page": page_path,
        "mode": mode,
        "requests": len(requests),
        "external_requests": len(external),
        "external_hosts": sorted({r["url"].split("/")[2] for r in external}),
        "bytes": sum(r["bytes"] for r in requests),
        "gzip_bytes": sum(r["gzip"] for r in requests),
        "load_s": load_s,
        "math_total": math_total,
        "math_rendered": math_rendered,
        "first_paint_s": round(fcp / 1000, 2) if fcp is not None else None,
        # Material при font: false подставляет «_» перед системным стеком шрифтов.
        "font": "системный" if font.startswith("_") else font.split(",")[0],
    }


if __name__ == "__main__":
    site_dir, page_arg, mode_arg = sys.argv[1], sys.argv[2], sys.argv[3]
    shot_arg = sys.argv[4] if len(sys.argv) > 4 else None
    print(json.dumps(measure(Path(site_dir), page_arg, mode_arg, shot_arg), ensure_ascii=False))
