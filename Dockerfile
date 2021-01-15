FROM python:3.8-slim

RUN groupadd -g 1234 fb2i \
  && adduser --disabled-password --uid 1234 --gid 1234 fb2i

WORKDIR /home/fb2i

COPY requirements.txt ./
RUN python -m venv venv \
  && venv/bin/pip install -r requirements.txt \
  && venv/bin/pip install gunicorn

COPY fitbit2influx fitbit2influx
COPY docker/* ./
COPY pyproject.toml ./
RUN mkdir -p /var/lib/fb2i \
  && chown -R fb2i:fb2i /var/lib/fb2i ./ \
  && chmod +x docker-entry.sh

USER fb2i
EXPOSE 5000
ENTRYPOINT [ "/home/fb2i/docker-entry.sh" ]
CMD [ "fb2i" ]
