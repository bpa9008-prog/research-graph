---
search:
  exclude: true
---

# Тексты пайплайнов

Файлы ниже вставляются в страницу при сборке сайта из репозитория
(`pymdownx.snippets`), поэтому всегда совпадают с тем, что реально выполняется.
Пояснения — в комментариях внутри файлов.

## Workflow `Site`

Сборка, публикация на GitHub Pages и Helios, откат, удаление preview.

```yaml linenums="1" title=".github/workflows/site.yml"
--8<-- ".github/workflows/site.yml"
```

## Выкладка на Helios: клиентская часть

Выполняется на раннере: подключение по SSH со строгой проверкой ключа хоста,
загрузка через `rsync --link-dest` или `tar`.

```bash linenums="1" title="scripts/helios.sh"
--8<-- "scripts/helios.sh"
```

## Выкладка на Helios: серверная часть

Выполняется на Helios, передаётся через `ssh … sh -s`. Только POSIX sh.

```sh linenums="1" title="scripts/helios-remote.sh"
--8<-- "scripts/helios-remote.sh"
```

## Healthcheck

```bash linenums="1" title="scripts/healthcheck.sh"
--8<-- "scripts/healthcheck.sh"
```

## Проверка отсутствия внешних ресурсов

```python linenums="1" title="scripts/check_offline.py"
--8<-- "scripts/check_offline.py"
```

## Workflow `CI` (из ЛР1, без изменений)

```yaml linenums="1" title=".github/workflows/ci.yml"
--8<-- ".github/workflows/ci.yml"
```

!!! note "Страница исключена из поиска"
    Полные тексты скриптов увеличивали индекс поиска с 196 до 255 КБ, а тема
    загружает индекс при открытии любой страницы. Поиск по коду удобнее вести
    в репозитории.
