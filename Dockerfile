FROM python:3.8.6-alpine3.11

COPY requirements.txt /pblive/requirements.txt

RUN /sbin/apk add --no-cache --virtual .deps gcc musl-dev \
 && /usr/local/bin/pip install --no-cache-dir --requirement /pblive/requirements.txt \
 && /sbin/apk del --no-cache .deps

ENV PYTHONUNBUFFERED="1"

WORKDIR /pblive
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["-m", "pblive"]

COPY /pblive /pblive/pblive
