# -------------------------
# BASE IMAGE
# -------------------------
FROM python:3.11-slim

# -------------------------
# WORKDIR
# -------------------------
WORKDIR /app

# -------------------------
# INSTALL UV
# -------------------------
RUN pip install --no-cache-dir uv

# -------------------------
# COPY PROJECT FILES
# -------------------------
COPY pyproject.toml ./

# Optional lockfile
# COPY uv.lock ./

# -------------------------
# INSTALL DEPENDENCIES
# -------------------------
# --no-install-project prevents uv from attempting
# to build/install the repository itself.
RUN uv sync --no-install-project

# -------------------------
# COPY SOURCE CODE
# -------------------------
COPY . .

# -------------------------
# EXPOSE PORT
# -------------------------
EXPOSE 8000

# -------------------------
# START APPLICATION
# -------------------------
CMD ["uv", "run", "uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8000"]