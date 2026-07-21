FROM python:3.12-slim-bookworm

ARG APP_USER=labops
ARG APP_UID=10001

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV LABOPS_AI_PROJECT_ROOT=/opt/labops-ai

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
COPY config ./config
COPY logs ./logs

RUN python -m pip install \
      --no-cache-dir \
      . \
    && mkdir -p \
      /opt/labops-ai/runtime \
    && chown -R \
      "${APP_USER}:${APP_USER}" \
      /opt/labops-ai/runtime

COPY \
  config/host_agent_container.json \
  /etc/labops-ai/host_agent.json

USER labops

ENTRYPOINT ["python", "-m", "labops_ai.agent"]
CMD ["--continuous", "--config", "/etc/labops-ai/host_agent.json"]
