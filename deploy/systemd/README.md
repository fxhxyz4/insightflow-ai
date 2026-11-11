# Запуск за розкладом через systemd (без Docker)

```zsh
mkdir -p ~/.config/systemd/user
cp deploy/systemd/insightflow.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now insightflow.timer
systemctl --user list-timers | grep insightflow
systemctl --user start insightflow.service
journalctl --user -u insightflow.service -e
```
`Persistent=true`: якщо ноутбук був вимкнений у призначений час, запуск виконається при наступному вмиканні.
Щоб змінити модель, відредагуйте `--model` / додайте `--digest-model` у `ExecStart`.
