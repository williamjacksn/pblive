FROM python:3.10.6-alpine3.15

RUN /usr/sbin/adduser -g python -D python

USER python
RUN /usr/local/bin/python -m venv /home/python/venv

COPY --chown=python:python requirements.txt /home/python/pblive/requirements.txt
RUN /home/python/venv/bin/pip install --no-cache-dir --requirement /home/python/pblive/requirements.txt

ENV PATH="/home/python/venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1" \
    QUIZ_SERVER_URL="This is set by env var QUIZ_SERVER_URL" \
    TZ="Etc/UTC"

WORKDIR /home/python/pblive
ENTRYPOINT ["/home/python/venv/bin/python"]
CMD ["-m", "pblive"]

LABEL org.opencontainers.image.source="https://github.com/williamjacksn/pblive"

COPY --chown=python:python pblive /home/python/pblive/pblive
