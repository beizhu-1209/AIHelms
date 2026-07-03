FROM python:3.12-slim-bookworm

ARG SKILLSPECTOR_REF=326a2b489411a20ed742ff13701be39ba00063c8

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn \
    SKILLSPECTOR_SERVICE_INPUT_ROOT=/scan-input \
    SKILLSPECTOR_SERVICE_TIMEOUT_SECONDS=600 \
    SKILLSPECTOR_LOG_LEVEL=WARNING

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install \
        "https://github.com/NVIDIA/SkillSpector/archive/${SKILLSPECTOR_REF}.zip" \
        fastapi \
        uvicorn

COPY server.py /app/server.py

RUN python -c "import skillspector; print(skillspector.__version__)"

EXPOSE 8010

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010"]
