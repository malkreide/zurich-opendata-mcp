FROM python:3.11-slim

WORKDIR /app

# Copy everything needed for pip install
COPY pyproject.toml README.md ./
COPY src/ src/

# Install package
RUN pip install --no-cache-dir .

# Environment: SSE transport for remote access
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0

# Render sets PORT automatically
EXPOSE 8000

CMD ["zurich-opendata-mcp"]
