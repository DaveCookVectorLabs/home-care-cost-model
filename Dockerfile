FROM python:3.11-alpine

LABEL maintainer="Dave Cook <dave@binx.ca>"
LABEL description="Home Care Cost Model — Python engine with reference CSVs"
LABEL org.opencontainers.image.source="https://github.com/DaveCookVectorLabs/home-care-cost-model"
LABEL org.opencontainers.image.documentation="https://www.binx.ca/guides/home-care-cost-model-guide.pdf"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install Python dependencies
COPY engines/python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy engine and reference CSVs
COPY engines/python/engine.py .
COPY datasets/home_care_services_canada.csv datasets/
COPY datasets/home_care_tax_parameters_2026.csv datasets/
COPY datasets/home_care_subsidy_programs.csv datasets/

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8003/health || exit 1

CMD ["python", "engine.py", "--serve", "--port", "8003"]
