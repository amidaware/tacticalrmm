FROM python:3.9.2-slim

ENV TACTICAL_DIR /opt/tactical
ENV TACTICAL_GO_DIR /usr/local/rmmgo
ENV TACTICAL_READY_FILE ${TACTICAL_DIR}/tmp/tactical.ready
ENV WORKSPACE_DIR /workspace
ENV TACTICAL_USER tactical
ENV VIRTUAL_ENV ${WORKSPACE_DIR}/api/tacticalrmm/env
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

RUN groupadd -g 1000 tactical && \
    useradd -u 1000 -g 1000 tactical

# Copy Go Files
COPY --from=golang:1.16 /usr/local/go ${TACTICAL_GO_DIR}/go

# Copy Dev python reqs
COPY ./requirements.txt /

# Copy Docker Entrypoint
COPY ./entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

WORKDIR ${WORKSPACE_DIR}/api/tacticalrmm
