FROM python:3.12-slim

WORKDIR /app

# install uv
RUN pip install --no-cache-dir uv

# copy dependency definition first
COPY pyproject.toml ./

# install runtime dependencies into the system environment so the bind mount does not hide them
RUN uv pip install --system \
	"fastapi[standard]>=0.136.1" \
	"uvicorn[standard]>=0.47.0" \
	"click>=8.1.8" \
	"httpx>=0.28.1" \
	"pydantic>=2.13.4" \
	"python-dotenv>=1.2.2" \
	"loguru>=0.7.3" \
	"langgraph>=1.2.0" \
	"langchain-core>=1.4.0" \
	"langfuse>=4.6.1"

# copy application code AFTER dependencies are installed
COPY . .

EXPOSE 8000

# run python directly (dependencies are installed system-wide)
CMD ["python", "-m", "uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8000"]