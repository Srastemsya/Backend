# Вход и регистрация

[Секция Figma](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9964) показывает выбор способа входа, подтверждение контакта и завершение регистрации. Формы используют `Surface / Liquid Glass`, общие кнопки и поля UI-кита.

| Экран | Действие |
|---|---|
| [Выбор способа входа](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9966) | Выбор телефона или почты. В макете также показаны варианты входа через провайдеров. |
| [Вход по телефону](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-9997) | Ввести номер и запросить код. |
| [Код из SMS](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-10020) | Ввести четыре цифры и подтвердить. Ниже показаны повторная отправка и таймер. |
| [Профиль после входа по телефону](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-10047) | Указать имя и дату рождения. |
| [Вход по почте](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-10096) | Ввести адрес и запросить код. |
| [Код из письма](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-10119) | Ввести четыре цифры и подтвердить. Ниже показаны повторная отправка и таймер. |
| [Профиль после входа по почте](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=280-10146) | Указать имя и дату рождения. |

## Сценарий

1. Открыть экран входа и выбрать телефон или почту.
2. Заполнить поле и запросить код.
3. Ввести код и подтвердить контакт.
4. Заполнить данные профиля и завершить регистрацию.

## Liquid Glass

У семи форм одинаковые внутренние отступы. Активные сегменты индикатора шагов используют токен `color/action/primary`. В двух экранах подтверждения используется экземпляр `Auth/Code` с четырьмя ячейками. Заголовок, подсказка и блок повторной отправки с таймером остаются частью экрана. [UI Kit](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=69-583) · [Auth/Code](https://www.figma.com/design/khewsPf7b4JVyBwJaCmO43/startap_design?node-id=165-1432).

Прототип показывает отдельные состояния форм. **Требует решения** — способы входа через провайдеров, правила повторной отправки и экран после завершения регистрации.

Поведение локальной регистрации, таймеров и переходов описано в [контракте релиза](../contracts/discovery-v1.md#вход-и-регистрация).
