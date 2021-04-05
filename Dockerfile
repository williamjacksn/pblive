FROM python:3.9.3-alpine3.13

COPY requirements.txt /pblive/requirements.txt

RUN /usr/local/bin/pip install --no-cache-dir --requirement /pblive/requirements.txt

ENV PYTHONUNBUFFERED="1"
ENV QUIZ_SERVER_URL="This is set by env var QUIZ_SERVER_URL"

WORKDIR /pblive
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["-m", "pblive"]

COPY /pblive /pblive/pblive
