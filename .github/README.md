# GitHub Repository Configuration

Этот репозиторий содержит конфигурацию для GitHub.

## Структура

```
.github/
├── ISSUE_TEMPLATE/
│   ├── bug_report.md          # Шаблон для сообщений о багах
│   └── feature_request.md     # Шаблон для запросов функций
└── pull_request_template.md   # Шаблон для Pull Requests
```

## Использование

### Создание Issue

При создании нового Issue выберите один из шаблонов:
- **Bug Report** — для сообщений о проблемах
- **Feature Request** — для предложений новых функций

### Создание Pull Request

При создании Pull Request используйте шаблон, который поможет:
- Описать изменения
- Указать связанные Issues
- Добавить инструкции по тестированию
- Проверить чеклист

---

## Конфигурация

### Labels

Рекомендуемые labels для Issues и Pull Requests:

- `bug` — ошибки
- `enhancement` — улучшения
- `documentation` — документация
- `good first issue` — хорошее начало для новичков
- `help wanted` — нужна помощь
- `priority: high` — высокий приоритет
- `priority: medium` — средний приоритет
- `priority: low` — низкий приоритет
- `wontfix` — не будет исправлено
- `duplicate` — дубликат
- `invalid` — недействительно

### Branch Protection

Рекомендуемые настройки защиты ветки `main`:

- Require pull request reviews before merging
  - Require approvals: 1
- Require status checks to pass before merging
  - Require branches to be up to date before merging
- Do not allow bypassing the above settings

---

## Дополнительные ресурсы

- [GitHub Issue Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository)
- [GitHub Pull Request Templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
