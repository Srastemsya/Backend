# OpenCode для «Срастёмся»

Проектная конфигурация рассчитана на macOS Apple Silicon и использует Python 3 для формирования параметров провайдера. OpenCode читает существующий `AGENTS.md`. Правила дизайна, бэкенда и тестирования подключаются по маршрутам в этом файле и в `workflow/rules/index.md`.

## Установка и обновление

Основной лаунчер использует **OpenCode 2.2.7** из `.opencode/bin/v2/opencode`. Для macOS Apple Silicon выполните из корня проекта:

```sh
(
  set -eu
  archive=$(mktemp)
  trap 'rm -f "$archive"' EXIT
  curl -fsSL https://registry.npmjs.org/@opencode/cli-darwin-arm64/-/cli-darwin-arm64-2.2.7.tgz -o "$archive"
  mkdir -p .opencode/bin/v2
  tar -xzf "$archive" -C .opencode/bin/v2 --strip-components 2 package/bin/opencode
  .opencode/launch --version
)
```

Для другой платформы скачайте CLI 2.2.7 через [официальный канал OpenCode 2.x](https://opencode.ai/v2/docs/) и укажите его абсолютный путь в `OPENCODE_BIN`.

## Подключение API

Выполните в zsh из корня проекта. Подставьте базовый URL провайдера, обычно с суффиксом `/v1`, и точный ID модели с поддержкой tool calling.

```zsh
export COMPAT_API_BASE='https://gptunnel.ru/v1'
export COMPAT_API_MODEL='model-id'
read -rs 'COMPAT_API_KEY?Ключ API: '
echo
export COMPAT_API_KEY
.opencode/launch
unset COMPAT_API_KEY
```

Сессии, кэш и локальные данные OpenCode хранятся в игнорируемом каталоге `.opencode/state/`. Ключ вводится без эха и передаётся в окружении процесса. Команды агента запускаются с унаследованным окружением, поэтому проверяйте запросы терминала перед подтверждением. Настройки разрешений OpenCode действуют на уровне инструментов и отличаются от системной песочницы Codex.

## Workflow

- Для явного запуска очереди используйте `/spec-queue`. PM, Developer и Tester работают в отдельных контекстах. Если разделение контекстов невозможно подтвердить, команда предписывает зафиксировать BLOCKED. Проектные файлы ролей и существующая очередь остаются источником требований.
- Изменения файлов и большинство команд терминала требуют подтверждения. Git, тесты и локальные инструменты используют обычное окружение проекта.
- OpenCode обнаруживает стандартные навыки в `~/.agents/skills`, включая `setup-spec-pipeline`. Этот навык предназначен для настройки pipeline, а текущая очередь уже настроена. Навыки, завязанные на инструменты Codex и его плагины, требуют отдельной адаптации. Пользовательские правила команд Codex в `~/.codex/rules` имеют другой формат. Отдельного каталога пользовательских команд Codex и проектных файлов `.mdc` при аудите не обнаружено.
- Для Figma запустите `.opencode/launch mcp auth figma`, затем `.opencode/launch mcp list`. Права зависят от аккаунта Figma. Интеграции Codex Desktop и его node_repl в эту конфигурацию не включены.

## Проверка с подключённой моделью

Используйте временный Git-репозиторий с простым тестом и чистым исходным коммитом. Сначала запросите анализ и план. Затем подтвердите изменение кода и запуск теста, просмотрите `git diff`. Для проверки MCP запросите чтение доступного Figma-файла после OAuth. Проверяйте очередь на отдельном сценарии, прежде чем применять её к рабочему проекту.

[Конфигурация](https://opencode.ai/docs/config) · [Провайдеры](https://opencode.ai/docs/providers) · [MCP](https://opencode.ai/docs/mcp-servers) · [Skills](https://opencode.ai/docs/skills)
