FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Re-install with source (editable not needed in prod)
RUN pip install --no-cache-dir .

# SSE transport for remote access
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

EXPOSE 8080

CMD ["zurich-opendata-mcp"]
