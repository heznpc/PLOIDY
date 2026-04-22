FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .

# Bot does not listen on any port — just an outbound long-poll to
# Discord's gateway — so no EXPOSE needed.
CMD ["python", "bot.py"]
