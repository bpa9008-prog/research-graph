"""Проверка, что собранный сайт не грузит ресурсы с внешних серверов.

Запуск: python scripts/check_offline.py site

Ищет в HTML и CSS ссылки на внешние ресурсы, которые браузер загрузит сам
(скрипты, стили, шрифты, картинки, iframe). Обычные гиперссылки <a href> не
считаются: по ним браузер идёт только по клику. Код возврата 1, если найдено
хоть одно внешнее подключение, — сайт сломается при недоступности CDN.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

# Атрибуты, по которым браузер загружает ресурс без участия пользователя.
RESOURCE_ATTRS = {
    "script": ("src",),
    "img": ("src", "srcset"),
    "iframe": ("src",),
    "source": ("src", "srcset"),
    "video": ("src", "poster"),
    "audio": ("src",),
    "embed": ("src",),
    "object": ("data",),
}
# <link rel=...>, которые приводят к загрузке.
LINK_RELS = {"stylesheet", "preload", "modulepreload", "icon", "manifest", "preconnect"}
CSS_URL = re.compile(r"""url\(\s*['"]?(https?:)?//([^/'")\s]+)""", re.IGNORECASE)
CSS_IMPORT = re.compile(r"""@import\s+['"](https?:)?//([^/'"]+)""", re.IGNORECASE)


def external_host(url: str) -> str | None:
    url = url.strip().split(" ")[0]  # srcset: «url 2x»
    if url.startswith("//") or url.lower().startswith(("http://", "https://")):
        return urlsplit(url if not url.startswith("//") else "https:" + url).hostname
    return None


class ResourceFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hosts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        candidates: list[str] = []
        if tag == "link":
            rels = set(a.get("rel", "").lower().split())
            if rels & LINK_RELS:
                candidates.append(a.get("href", ""))
        for attr in RESOURCE_ATTRS.get(tag, ()):
            if attr == "srcset":
                candidates.extend(a.get(attr, "").split(","))
            else:
                candidates.append(a.get(attr, ""))
        for c in candidates:
            host = external_host(c)
            if host:
                self.hosts.append(host)


def scan(site: Path) -> Counter[str]:
    found: Counter[str] = Counter()
    for page in site.rglob("*.html"):
        finder = ResourceFinder()
        finder.feed(page.read_text(encoding="utf-8", errors="replace"))
        for host in finder.hosts:
            found[f"{host}  ← {page.relative_to(site)}"] += 1
    for css in site.rglob("*.css"):
        text = css.read_text(encoding="utf-8", errors="replace")
        for m in (*CSS_URL.finditer(text), *CSS_IMPORT.finditer(text)):
            found[f"{m.group(2)}  ← {css.relative_to(site)}"] += 1
    return found


def main(argv: list[str]) -> int:
    site = Path(argv[1] if len(argv) > 1 else "site")
    if not (site / "index.html").is_file():
        print(f"{site}/index.html не найден — сначала соберите сайт", file=sys.stderr)
        return 2
    found = scan(site)
    pages = sum(1 for _ in site.rglob("*.html"))
    if not found:
        print(f"OK: {pages} страниц, внешних подключений нет")
        return 0
    print(f"Найдены внешние подключения ({sum(found.values())}):")
    for item, n in found.most_common():
        print(f"  {n:4d} × {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
