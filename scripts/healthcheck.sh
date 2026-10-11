#!/usr/bin/env bash
# Проверка опубликованного сайта после выкладки.
#
#   scripts/healthcheck.sh <базовый_URL> <ожидаемый_хеш_коммита>
#
# Проверяет не «открывается ли страница», а что открывается ИМЕННО новая версия:
#   1. главная отдаёт 200;
#   2. в HTML есть <meta name="rg-build" content="<хеш>"> — контрольная строка;
#   3. индекс поиска доступен и является JSON (поиск работает);
#   4. MathJax отдаётся с самого сайта (формулы не зависят от CDN);
#   5. страница с формулами отдаёт 200 и содержит размеченные формулы;
#   6. несуществующий адрес отдаёт 404, а не 200 (нет «вечного index.html»).
# Сетевые кэши могут отдавать старую версию — поэтому несколько попыток.
set -uo pipefail

base=${1:?базовый URL не задан}
sha=${2:?хеш коммита не задан}
base=${base%/}/
attempts=${HEALTHCHECK_ATTEMPTS:-6}
delay=${HEALTHCHECK_DELAY:-10}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Python нужен только для разбора индекса поиска. На Windows-runner python3
# бывает заглушкой Microsoft Store, поэтому проверяем, что он реально запускается.
py=
for c in python3 python; do
  if "$c" -c '' 2> /dev/null; then py=$c; break; fi
done

search_docs() { # $1 — файл индекса; печатает число записей, код 1 — не индекс
  if [[ -n $py ]]; then
    "$py" -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); assert d["docs"]; print(len(d["docs"]))' "$1" 2> /dev/null
  else
    # Без Python — грубая проверка: JSON-объект с непустым массивом docs.
    head -c 1 "$1" | grep -q '{' && grep -q '"docs": *\[ *{' "$1" && echo "?"
  fi
}

fetch() { # $1 — путь от базового URL, $2 — файл для тела; печатает код ответа
  curl -sS -L --max-time 30 -o "$2" -w '%{http_code}' \
    -H 'Cache-Control: no-cache' "${base}$1?hc=$(date +%s)" 2> "$tmp/curl.err" || echo 000
}

check() {
  local code fail=0

  code=$(fetch "" "$tmp/index.html")
  if [[ $code != 200 ]]; then
    echo "✗ главная: HTTP $code $(cat "$tmp/curl.err")"; return 1
  fi
  echo "✓ главная: HTTP 200"

  local found
  found=$(grep -o '<meta name="rg-build" content="[^"]*"' "$tmp/index.html" | sed 's/.*content="//; s/"$//')
  if [[ $found != "$sha" ]]; then
    echo "✗ контрольная строка: ожидался rg-build=$sha, на сайте ${found:-<нет>}"; return 1
  fi
  echo "✓ контрольная строка: rg-build=$sha"

  code=$(fetch "search/search_index.json" "$tmp/search.json")
  local docs
  if [[ $code == 200 ]] && docs=$(search_docs "$tmp/search.json"); then
    echo "✓ индекс поиска: $docs записей"
  else
    echo "✗ индекс поиска: HTTP $code или не JSON"; fail=1
  fi

  code=$(fetch "assets/vendor/mathjax/tex-svg.js" "$tmp/mj.js")
  if [[ $code == 200 ]]; then echo "✓ MathJax с сайта: $(wc -c < "$tmp/mj.js") байт"
  else echo "✗ MathJax с сайта: HTTP $code"; fail=1; fi

  code=$(fetch "report/math-check/" "$tmp/math.html")
  if [[ $code == 200 ]] && grep -q 'class="arithmatex"' "$tmp/math.html"; then
    echo "✓ страница с формулами"
  else
    echo "✗ страница с формулами: HTTP $code или нет формул"; fail=1
  fi

  code=$(fetch "no-such-page-$RANDOM/" "$tmp/404.html")
  if [[ $code == 404 ]]; then echo "✓ несуществующая страница: 404"
  else echo "✗ несуществующая страница: HTTP $code (ожидался 404)"; fail=1; fi

  return $fail
}

for ((i = 1; i <= attempts; i++)); do
  echo "— попытка $i/$attempts: $base"
  if check; then
    echo "healthcheck пройден"
    exit 0
  fi
  if ((i < attempts)); then sleep "$delay"; fi
done
echo "healthcheck НЕ пройден: $base" >&2
exit 1
