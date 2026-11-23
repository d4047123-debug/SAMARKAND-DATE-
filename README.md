# SAMARKAND DATE — Telegram Mini App

Telegram bot + Mini App questionnaire built with Python, Aiogram, FastAPI and HTML/CSS/JS.

## Features
- `/start` opens the Telegram Mini App.
- 12 questions about meeting preferences in Samarkand.
- Access code checked on the server.
- Telegram `initData` signature validation.
- Sends the numbered answers and Telegram sender details to the admin.
- No database and no Railway Volume.
- Basic copy/context-menu restrictions (not screenshot protection).

## Environment variables

Set these in Railway → your service → Variables:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | Token from @BotFather |
| `ADMIN_ID` | Your numeric Telegram user ID |
| `WEBAPP_URL` | Public HTTPS Railway domain, e.g. `https://your-app.up.railway.app` |
| `ACCESS_CODE` | Your own access code (at least 4 characters) |

Do not put real tokens or access codes into GitHub or source files.

## GitHub + Railway deployment

1. Create a GitHub repository and upload all project files, preserving the `static` folder.
2. In Railway choose **New Project → Deploy from GitHub Repo** and select the repository.
3. Add the four variables above in Railway Variables.
4. Deploy. Railway detects the `Procfile`; the start command is `python main.py`.
5. In Railway → Settings → Networking, generate a public domain.
6. Copy the HTTPS domain into `WEBAPP_URL` in Variables, then redeploy.
7. In @BotFather, use `/setdomain`, select your bot and provide the hostname only (for example `your-app.up.railway.app`) if Telegram asks for the Mini App domain.
8. Open your bot and send `/start`.

## Important
- This is a single-service deployment: FastAPI serves the Mini App and Aiogram polls Telegram updates in the same process.
- Do not add a Railway Volume. The app does not write user answers to disk or keep a permanent database.
- The answers are delivered to `ADMIN_ID` in Telegram. The application does not persist them.
- The in-memory 30-second rate limit resets on service restart.
- Copy blocking is only a deterrent. It cannot reliably prevent screenshots, screen recording, external cameras, browser inspection, or copying by modified clients.
- Use the form only with the recipient's knowledge and consent. Avoid asking for sensitive personal information.
- For a production system with many users, add persistent storage, stronger abuse controls, monitoring, and a clear data-retention policy.
