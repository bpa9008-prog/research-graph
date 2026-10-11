#!/bin/sh
# Серверная часть выкладки на Helios. Выполняется НА СЕРВЕРЕ так:
#   ssh user@host env HL_WEB=... sh -s -- <команда> [аргументы...] < scripts/helios-remote.sh
# Поэтому только POSIX sh: на Helios FreeBSD, а оболочка входа может быть tcsh.
#
# Раскладка файлов (пути относительно $HOME):
#   $STATE/releases/<tkey>/<id>/   — неизменяемые релизы (main, preview--<ветка>)
#   $STATE/state/<tkey>.current    — id активного релиза
#   $STATE/state/<tkey>.history    — журнал: время, действие, id
#   $STATE/previews/<ветка>        — (symlink-режим) ссылки на активные preview
#   $WEB                           — то, что отдаёт веб-сервер
#
# Режимы активации:
#   symlink — $WEB это символическая ссылка на каталог релиза; переключение
#             атомарно (rename), обрыв выкладки не трогает работающий сайт.
#   swap    — для серверов, где Apache не ходит по ссылкам: релиз копируется
#             в $WEB.new и меняется местами с $WEB двумя rename (окно ~мс).
set -eu

cmd=${1:?команда не задана}
shift

STATE=${HL_STATE:-rg-site}
WEB=${HL_WEB:?HL_WEB не задан}
MODE=${HL_MODE:-symlink}
KEEP=${HL_KEEP:-5}

cd "$HOME"

log() { printf '[helios] %s\n' "$*" >&2; }
die() { printf '[helios] ОШИБКА: %s\n' "$*" >&2; exit 1; }

# Ключ цели и проверка имён: в путях не должно быть ничего, кроме [a-z0-9._-].
tkey_of() {
  case "$1" in
    main) echo main ;;
    preview/*)
      slug=${1#preview/}
      case "$slug" in '' | *[!a-z0-9._-]* | .* ) die "недопустимое имя ветки: $slug" ;; esac
      echo "preview--$slug" ;;
    *) die "цель должна быть main или preview/<ветка>, получено: $1" ;;
  esac
}
check_id() {
  case "$1" in '' | *[!A-Za-z0-9._-]* | .* ) die "недопустимый id релиза: $1" ;; esac
}

# Публичный путь цели в вебе.
web_path_of() {
  case "$1" in
    main) echo "$WEB" ;;
    preview--*) echo "$WEB/preview/${1#preview--}" ;;
  esac
}

# Атомарная замена символической ссылки: создать рядом и переименовать.
# GNU mv понимает -T, FreeBSD mv — -h; иначе остаётся неатомарный ln -sfn.
swap_link() { # $1 — куда указывает, $2 — путь ссылки
  tmp="$2.tmp.$$"
  ln -s "$1" "$tmp"
  if mv -T "$tmp" "$2" 2>/dev/null; then :
  elif mv -h "$tmp" "$2" 2>/dev/null; then :
  else rm -f "$tmp"; ln -sfn "$1" "$2"
  fi
}

record() { # $1 — tkey, $2 — действие, $3 — id
  mkdir -p "$STATE/state"
  printf '%s\n' "$3" > "$STATE/state/$1.current"
  printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$2" "$3" >> "$STATE/state/$1.history"
}

current_of() { cat "$STATE/state/$1.current" 2>/dev/null || true; }

activate() { # $1 — tkey, $2 — id
  rel="$STATE/releases/$1/$2"
  [ -d "$rel" ] || die "релиз не найден: $rel"
  target=$(web_path_of "$1")
  mkdir -p "$(dirname "$WEB")"

  if [ "$MODE" = symlink ]; then
    if [ "$1" = main ]; then
      # Каталог preview/ живёт вне релиза, иначе его стирало бы каждое переключение.
      mkdir -p "$STATE/previews"
      [ -e "$rel/preview" ] || ln -s "$HOME/$STATE/previews" "$rel/preview"
      if [ -d "$WEB" ] && [ ! -L "$WEB" ]; then
        bak="$WEB.bak-$(date -u +%Y%m%dT%H%M%SZ)"
        log "$WEB — обычный каталог, переношу в $bak"
        mv "$WEB" "$bak"
      fi
      swap_link "$HOME/$rel" "$WEB"
    else
      mkdir -p "$STATE/previews"
      swap_link "$HOME/$rel" "$STATE/previews/${1#preview--}"
    fi
  elif [ "$MODE" = swap ]; then
    mkdir -p "$(dirname "$target")"
    rm -rf "$target.new" "$target.old"
    cp -R "$rel" "$target.new"
    # Чтобы смена main не стёрла preview: переносим их в новую копию.
    if [ "$1" = main ] && [ -d "$target/preview" ]; then
      mv "$target/preview" "$target.new/preview"
    fi
    if [ -L "$target" ]; then rm -f "$target"; fi
    if [ -e "$target" ]; then mv "$target" "$target.old"; fi
    mv "$target.new" "$target"
    rm -rf "$target.old"
  else
    die "неизвестный режим HL_MODE=$MODE (symlink|swap)"
  fi
  # Веб-сервер читает файлы от другого пользователя: нужен доступ на чтение
  # и проход по каталогам (на Helios umask часто 077).
  chmod go+x "$HOME" "$STATE" "$STATE/releases" "$STATE/releases/$1" 2>/dev/null || true
  if [ -d "$STATE/previews" ]; then chmod go+rx "$STATE/previews"; fi
  chmod -R u+rwX,go+rX "$rel"
  if [ "$MODE" = swap ]; then chmod -R u+rwX,go+rX "$target"; fi
  log "активирован $1/$2 → $target ($MODE)"
}

prune() { # $1 — tkey: оставить KEEP последних, активный не трогать никогда
  dir="$STATE/releases/$1"
  cur=$(current_of "$1")
  # Недокачанные релизы от оборванных выкладок.
  for p in "$dir"/*.partial; do
    if [ -e "$p" ]; then log "удаляю недокачанный $p"; rm -rf "$p"; fi
  done
  n=0
  for r in $(ls -1 "$dir" | sort -r); do
    n=$((n + 1))
    if [ "$n" -gt "$KEEP" ] && [ "$r" != "$cur" ]; then
      log "удаляю старый релиз $1/$r"
      rm -rf "${dir:?}/$r"
    fi
  done
}

case "$cmd" in
  prepare) # prepare <цель> <id>: путь для загрузки и предыдущий релиз (для --link-dest)
    tkey=$(tkey_of "$1"); check_id "$2"
    mkdir -p "$STATE/releases/$tkey"
    rm -rf "$STATE/releases/$tkey/$2.partial"
    mkdir -p "$STATE/releases/$tkey/$2.partial"
    echo "upload=$STATE/releases/$tkey/$2.partial"
    echo "previous=$(current_of "$tkey")"
    echo "rsync=$(command -v rsync || true)"
    ;;
  finalize) # finalize <цель> <id>: загрузка завершена → релиз → активация
    tkey=$(tkey_of "$1"); check_id "$2"
    up="$STATE/releases/$tkey/$2.partial"
    [ -d "$up" ] || die "нет загруженного каталога $up"
    [ -f "$up/index.html" ] || die "в загрузке нет index.html — выкладка неполная"
    mv "$up" "$STATE/releases/$tkey/$2"
    activate "$tkey" "$2"
    record "$tkey" deploy "$2"
    prune "$tkey"
    ;;
  rollback) # rollback <цель> [id]: по умолчанию — релиз, предшествующий активному
    tkey=$(tkey_of "$1")
    cur=$(current_of "$tkey")
    if [ "${2:-}" ]; then
      check_id "$2"; to=$2
    else
      to=$(ls -1 "$STATE/releases/$tkey" | grep -v '\.partial$' | sort | awk -v c="$cur" '$0 == c { print p; exit } { p = $0 }')
    fi
    [ -n "$to" ] || die "нет релиза для отката (активный: ${cur:-нет})"
    log "откат $tkey: $cur → $to"
    activate "$tkey" "$to"
    record "$tkey" rollback "$to"
    ;;
  list) # list <цель>: релизы и история
    tkey=$(tkey_of "$1")
    cur=$(current_of "$tkey")
    echo "Релизы $tkey (активный помечен *):"
    for r in $(ls -1 "$STATE/releases/$tkey" 2>/dev/null | sort -r); do
      if [ "$r" = "$cur" ]; then echo "* $r"; else echo "  $r"; fi
    done
    echo "История:"
    tail -n 20 "$STATE/state/$tkey.history" 2>/dev/null || echo "  (пусто)"
    ;;
  remove-preview) # remove-preview <ветка>: ветку удалили — убираем её preview
    tkey=$(tkey_of "preview/$1")
    rm -rf "$STATE/previews/$1" "$WEB/preview/$1" "$STATE/releases/$tkey"
    rm -f "$STATE/state/$tkey.current"
    printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" remove "-" >> "$STATE/state/$tkey.history"
    log "preview $1 удалён"
    ;;
  probe) # probe: что умеет сервер (для отладки)
    echo "uname=$(uname -sr)"
    echo "shell=${SHELL:-?}"
    echo "rsync=$(command -v rsync || echo нет)"
    echo "home=$HOME"
    ls -ld "$HOME" "$(dirname "$WEB")" 2>&1 || true
    ;;
  *) die "неизвестная команда: $cmd" ;;
esac
