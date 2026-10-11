#!/usr/bin/env bash
# Клиентская часть выкладки на Helios ИТМО (выполняется на раннере CI или локально).
#
#   scripts/helios.sh deploy <main|preview/<ветка>> <каталог_сайта> [id_релиза]
#   scripts/helios.sh rollback <main|preview/<ветка>> [id_релиза]
#   scripts/helios.sh list <main|preview/<ветка>>
#   scripts/helios.sh remove-preview <ветка>
#   scripts/helios.sh probe
#
# Настройки — переменные окружения:
#   HELIOS_HOST, HELIOS_USER          — обязательно
#   HELIOS_PORT        (22)           — у Helios ИТМО обычно 2222
#   HELIOS_WEB_DIR     (public_html/rg) — что отдаёт веб-сервер, от $HOME
#   HELIOS_STATE_DIR   (rg-site)       — где хранятся релизы, от $HOME
#   HELIOS_MODE        (symlink)       — symlink | swap, см. helios-remote.sh
#   HELIOS_KEEP        (5)             — сколько релизов хранить на цель
#   HELIOS_KEY         (~/.ssh/helios_deploy)       — приватный deploy-ключ
#   HELIOS_KNOWN_HOSTS (~/.ssh/known_hosts_helios)  — проверенный ключ хоста
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
remote_script="$here/helios-remote.sh"

: "${HELIOS_HOST:?HELIOS_HOST не задан}"
: "${HELIOS_USER:?HELIOS_USER не задан}"
port=${HELIOS_PORT:-22}
web=${HELIOS_WEB_DIR:-public_html/rg}
state=${HELIOS_STATE_DIR:-rg-site}
mode=${HELIOS_MODE:-symlink}
keep=${HELIOS_KEEP:-5}
key=${HELIOS_KEY:-$HOME/.ssh/helios_deploy}
known=${HELIOS_KNOWN_HOSTS:-$HOME/.ssh/known_hosts_helios}
dest="$HELIOS_USER@$HELIOS_HOST"

[[ -f $key ]] || { echo "нет ключа $key" >&2; exit 1; }
[[ -s $known ]] || { echo "нет known_hosts $known — проверка ключа хоста обязательна" >&2; exit 1; }

# StrictHostKeyChecking=yes: неизвестный или изменившийся ключ хоста — отказ,
# а не молчаливое добавление. BatchMode: никаких интерактивных запросов пароля.
ssh_opts=(
  -p "$port" -i "$key"
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o UserKnownHostsFile="$known"
  -o BatchMode=yes
  -o ConnectTimeout=20
  -o ServerAliveInterval=15 -o ServerAliveCountMax=4
)

# Запуск серверной части. Переменные передаются через env, потому что ssh не
# пробрасывает окружение, а оболочка входа на сервере может быть не sh.
remote() {
  ssh "${ssh_opts[@]}" "$dest" \
    env HL_WEB="$web" HL_STATE="$state" HL_MODE="$mode" HL_KEEP="$keep" \
    sh -s -- "$@" < "$remote_script"
}

now() { date +%s.%N; }
elapsed() { awk -v a="$1" -v b="$(now)" 'BEGIN { printf "%.1f", b - a }'; }
out() { # пишет key=value в GITHUB_OUTPUT, если запущены в Actions
  echo "$1=$2"
  if [[ -n ${GITHUB_OUTPUT:-} ]]; then echo "$1=$2" >> "$GITHUB_OUTPUT"; fi
}

cmd=${1:?команда не задана}
shift

case "$cmd" in
  deploy)
    target=${1:?цель не задана}
    site=${2:?каталог сайта не задан}
    id=${3:-$(date -u +%Y%m%dT%H%M%SZ)-$(git rev-parse --short=7 HEAD 2>/dev/null || echo local)}
    [[ -f $site/index.html ]] || { echo "в $site нет index.html — сначала соберите сайт" >&2; exit 1; }
    t0=$(now)

    info=$(remote prepare "$target" "$id")
    upload=$(sed -n 's/^upload=//p' <<< "$info")
    previous=$(sed -n 's/^previous=//p' <<< "$info")
    remote_rsync=$(sed -n 's/^rsync=//p' <<< "$info")
    echo "релиз $id → $upload (предыдущий: ${previous:-нет})"

    t1=$(now)
    if command -v rsync > /dev/null && [[ -n $remote_rsync ]]; then
      method=rsync
      link=()
      # --link-dest: неизменившиеся файлы становятся жёсткими ссылками на
      # предыдущий релиз — передаётся только разница, место не удваивается.
      if [[ -n $previous ]]; then link=(--link-dest="../$previous"); fi
      # Статистику пишем в файл, а не в конвейер с grep: иначе код ошибки rsync
      # потерялся бы, и недокачанный релиз ушёл бы в finalize.
      stats=$(mktemp)
      rsync -rlz --delete --stats "${link[@]}" \
        --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r \
        -e "ssh ${ssh_opts[*]}" \
        "$site/" "$dest:$upload/" > "$stats"
      grep -E '^(Number of (regular )?files transferred|Total transferred file size)' "$stats" || true
      rm -f "$stats"
    else
      method=tar
      tar -C "$site" -cf - . | ssh "${ssh_opts[@]}" "$dest" "tar -xf - -C $upload"
    fi
    upload_s=$(elapsed "$t1")

    # Только после полной загрузки: переименование .partial → релиз и переключение.
    # Обрыв до этой строки оставляет работающим прежний релиз.
    remote finalize "$target" "$id"

    out release "$id"
    out previous "$previous"
    out method "$method"
    out upload_seconds "$upload_s"
    out total_seconds "$(elapsed "$t0")"
    ;;
  rollback | list)
    remote "$cmd" "$@"
    ;;
  remove-preview | probe)
    remote "$cmd" "$@"
    ;;
  *)
    echo "неизвестная команда: $cmd" >&2
    exit 2
    ;;
esac
