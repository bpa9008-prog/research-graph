#!/usr/bin/env bash
# Подготовка SSH для job, работающих с Helios (вызывается из workflow Site).
#
#   scripts/ci-ssh-key.sh setup    — ключ и known_hosts из env SSH_KEY и KNOWN_HOSTS
#   scripts/ci-ssh-key.sh cleanup  — удалить их
#
# Файлы кладутся в RUNNER_TEMP, а не в ~/.ssh: self-hosted runner — постоянная
# машина, и ключ не должен оставаться в домашнем каталоге её владельца.
# Пути передаются следующим шагам через GITHUB_ENV (HELIOS_KEY, HELIOS_KNOWN_HOSTS),
# их читает scripts/helios.sh.
set -euo pipefail

: "${RUNNER_TEMP:?RUNNER_TEMP не задан — скрипт рассчитан на GitHub Actions}"
# На Windows (Git Bash) RUNNER_TEMP имеет вид C:\...; переводим в POSIX-путь.
tmp=$(cygpath -u "$RUNNER_TEMP" 2> /dev/null || printf '%s' "$RUNNER_TEMP")
dir="$tmp/helios-ssh"

case "${1:-}" in
  setup)
    : "${SSH_KEY:?секрет HELIOS_SSH_KEY не задан}"
    : "${KNOWN_HOSTS:?переменная HELIOS_KNOWN_HOSTS не задана}"
    mkdir -p "$dir"
    # На NTFS (Git Bash) права эмулируются и chmod каталога может не пройти;
    # доступ там определяет ACL профиля пользователя runner'а.
    chmod 700 "$dir" 2> /dev/null || true
    # tr: секрет, вставленный из Windows-редактора, может содержать CRLF.
    printf '%s\n' "$SSH_KEY" | tr -d '\r' > "$dir/key"
    chmod 600 "$dir/key"
    # Ключ хоста заранее сверен вручную и хранится в переменной окружения.
    # ssh-keyscan здесь НЕ используется: он доверяет первому ответившему.
    printf '%s\n' "$KNOWN_HOSTS" | tr -d '\r' > "$dir/known_hosts"
    ssh-keygen -lf "$dir/known_hosts"
    {
      echo "HELIOS_KEY=$dir/key"
      echo "HELIOS_KNOWN_HOSTS=$dir/known_hosts"
    } >> "$GITHUB_ENV"
    ;;
  cleanup)
    rm -rf "$dir"
    ;;
  *)
    echo "использование: $0 setup|cleanup" >&2
    exit 2
    ;;
esac
