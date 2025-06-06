# CRM Telegram Bots

This Django project contains a small CRM system with two Telegram bots for communicating with users. The bots are used to manage a public channel and a private channel. The project includes Celery tasks for broadcasting messages, custom admin pages and various management commands.

## Project structure

- `config/` – Django project configuration (settings, URLs, WSGI/ASGI, Celery config).
- `core/` – main Django app with models, tasks and admin customisations.
- `tg_bots/` – source code for the bots:
  - `bot_public/` – public bot available for everyone.
  - `bot_private/` – private bot for paying users.
- `scripts/` – helper shell scripts.
- `static/`, `templates/`, `media/` – assets used by the project.

## Required environment variables

Create a `.env` file in the project root or export these variables in your shell:

- `SECRET_KEY` – Django secret key.
- `DEBUG` – set to `True` or `False` (default is `True`).
- `ALLOWED_HOSTS` – comma separated list of allowed hosts.
- `DB_PASSWORD` – password for the PostgreSQL user.
- `TELEGRAM_BOT_TOKEN` – token for the public bot.
- `TELEGRAM_BOT_TOKEN_PRIVATE` – token for the private bot.
- `CELERY_BROKER_URL` – (optional) URL of the Celery broker, default `redis://127.0.0.1:6379/0`.
- `CELERY_RESULT_BACKEND` – (optional) result backend for Celery, default `redis://127.0.0.1:6379/1`.

## Running the bots

After installing dependencies (`pip install -r requirements.txt`) and applying migrations, you can start the bots using Django management commands:

```bash
python manage.py runbot          # runs tg_bots.bot_public
python manage.py runbot_private  # runs tg_bots.bot_private
```

Each command reads the required tokens from the environment variables described above.

## License

This project is licensed under the [MIT License](LICENSE).
