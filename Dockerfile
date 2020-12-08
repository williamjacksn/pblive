FROM python:3.9.1-alpine3.12

COPY requirements.txt /pblive/requirements.txt

RUN /usr/local/bin/pip install --no-cache-dir --requirement /pblive/requirements.txt

ENV PYTHONUNBUFFERED="1"

WORKDIR /pblive
ENTRYPOINT ["/usr/local/bin/python"]
CMD ["-m", "pblive"]

COPY /pblive /pblive/pblive
