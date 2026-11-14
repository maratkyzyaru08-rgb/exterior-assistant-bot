# Экстерьер көмекшісі — Render

## Файлдар

* `app.py` — Telegram боттың толық коды (Flask webhook + Gemini).
* `requirements.txt` — Python кітапханалары.
* `Procfile` — Render іске қосу командасы.
* `render.yaml` — Render Blueprint конфигурациясы.

## Render Environment Variables

Render сервисінің Environment бөлімінде:

* `BOT\_TOKEN` = BotFather берген Telegram бот токені
* `GEMINI\_API\_KEY` = Google AI Studio API кілті
* `WEBHOOK\_SECRET` = ерікті құпия мәтін (немесе render.yaml арқылы автоматты жасалады)
* `RENDER\_EXTERNAL\_URL` = Render сервисінің `https://...onrender.com` адресі

`RENDER\_EXTERNAL\_URL` мәніне соңында `/` қоймаңыз.
Құпия кілттерді GitHub-қа немесе кодқа енгізбеңіз.

## Render параметрлері

* Runtime: Python
* Build Command: `pip install -r requirements.txt`
* Start Command: `gunicorn app:app --workers 1 --threads 4 --timeout 120`

## Ескерту

Free Render сервисі әрекетсіздік кезінде ұйқы режиміне өтеді. Қайта оянғанда
алғашқы жауап кешігуі мүмкін. Диалог тарихы жадыда сақталады және сервис
қайта іске қосылғанда тазаланады.

