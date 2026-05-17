FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir python-telegram-bot==21.6 httpx==0.27.2 python-dotenv==1.0.1
COPY . .
CMD ["python", "bot.py"]
