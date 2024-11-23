FROM python:3.12.7-bookworm

WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --require-hashes --no-deps

COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
