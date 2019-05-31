FROM python:3.5-slim

WORKDIR /app

COPY . /app
RUN pip install --upgrade pip
RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 28015

CMD ["python", "-u", "bot.py"]