FROM python:3.12-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 jupyter

WORKDIR /home/jupyter/work

COPY requirements.txt .
USER jupyter
RUN pip install --user --no-warn-script-location -r requirements.txt

ENV PATH=/home/jupyter/.local/bin:$PATH \
    PYTHONPATH=/home/jupyter/work/src

COPY --chown=jupyter:jupyter . .

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser"]
