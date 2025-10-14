# ---- Stage 1: exporter les deps avec Poetry ----
FROM python:3.10 AS requirements-stage
WORKDIR /tmp
RUN pip install --no-cache-dir "poetry>=1.6.0" "poetry-plugin-export>=1.6.0"
COPY ./pyproject.toml ./poetry.lock* /tmp/
# Si tu n'as pas de poetry.lock, décommente la ligne suivante :
# RUN poetry lock --no-update
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --with-credentials

# ---- Stage 2: image finale ----
FROM python:3.10
WORKDIR /code

# 1) Outils de build + Rust (pour tiktoken)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# 2) pip récent (sinon pas de wheels récents)
RUN pip install --no-cache-dir --upgrade pip

# 3) Deps Python
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt
# après: RUN pip install --no-cache-dir -r /code/requirements.txt
RUN pip install --no-cache-dir --upgrade 'qdrant-client>=1.15.0'

# 4) Code
COPY . /code
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn","server.main:app","--host","0.0.0.0","--port","8000"]
