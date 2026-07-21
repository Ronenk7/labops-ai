FROM python:3.12-slim-bookworm

ARG APP_USER=labops
ARG APP_UID=10001

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/labops-ai

RUN groupadd \
      --gid "${APP_UID}" \
      "${APP_USER}" \
    && useradd \
      --uid "${APP_UID}" \
      --gid "${APP_UID}" \
      --create-home \
      --shell /usr/sbin/nologin \
      "${APP_USER}"

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install \
      --no-cache-dir \
      .

COPY \
  config/host_agent_container.json \
  /etc/labops-ai/host_agent.json

USER labops

ENTRYPOINT ["python", "-m", "labops_ai.agent"]
CMD ["--continuous", "--config", "/etc/labops-ai/host_agent.json"]
