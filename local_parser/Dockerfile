FROM python:3.11-slim-bookworm

# uv 以固定版本從官方映像複製進來，確保 build 可重現（不隨 latest 漂移）
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# --locked：uv.lock 與 pyproject.toml 不一致就讓 build 失敗，而非默默重解版本
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

# 讓 uvicorn 直接可用，CMD 不必前綴 uv run
ENV PATH="/app/.venv/bin:$PATH"

COPY app.py .

EXPOSE 8100

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
