FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir kubernetes click rich

COPY k8s_advisor/ k8s_advisor/
RUN pip install --no-cache-dir --no-deps .

RUN useradd -r -u 1000 advisor
USER advisor

ENTRYPOINT ["k8s-advisor"]