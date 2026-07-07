FROM python:3.10-slim

WORKDIR /code

# System libraries required by mediapipe / opencv at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

EXPOSE 7860

CMD ["uvicorn", "app_full:app", "--host", "0.0.0.0", "--port", "7860"]
