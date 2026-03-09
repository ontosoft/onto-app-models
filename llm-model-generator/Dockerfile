FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

WORKDIR /app/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Install Java (OpenJDK) - these three steps are necessary to ensure Java 25 is installed and available in the environment for the purpose of running the Pellet and HermiT reasoners, using Owlready2, 
# TODO This has to be tested

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && apt-get clean
# Manual install of Java 25 (Reliable for version 25 specifically)
RUN wget https://download.oracle.com/java/25/latest/jdk-25_linux-x64_bin.tar.gz && \
    mkdir -p /usr/lib/jvm/java-25-openjdk-amd64 && \
    tar -xzf jdk-25_linux-x64_bin.tar.gz -C /usr/lib/jvm/java-25-openjdk-amd64 --strip-components=1 && \
    rm jdk-25_linux-x64_bin.tar.gz

# Set the JAVA_HOME to the new Java 25 path
ENV JAVA_HOME=/usr/lib/jvm/java-25-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Verify Java version during build
RUN java -version

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package app

#COPY ./llm-model-generator/scripts /app/llm-model-generator/scripts

COPY ./llm-model-generator/pyproject.toml ./llm-model-generator/README.md /app/llm-model-generator/

COPY ./llm-model-generator/app /app/llm-model-generator/app

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --package app 

WORKDIR /app/llm-model-generator/

CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
