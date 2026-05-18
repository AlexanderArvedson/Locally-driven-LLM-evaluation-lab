FROM python:3.12-slim

WORKDIR /app

# install uv
RUN pip install --no-cache-dir uv

# copy dependency definition first
COPY pyproject.toml ./

# install dependencies into container environment
RUN uv sync --no-install-project

# copy application code AFTER dependencies are installed
COPY . .

EXPOSE 8000

# run python directly (no uv at runtime)
CMD ["python", "-m", "uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8000"]