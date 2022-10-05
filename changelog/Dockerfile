FROM python:3-alpine

WORKDIR /app

RUN apk add git

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && rm requirements.txt

RUN git config --system --add safe.directory '*'

COPY changelog.py .

ENTRYPOINT ["/app/changelog.py"]