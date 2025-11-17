FROM python:3.13

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scraper.py .

# Create a non-root user to run the application
RUN useradd -m scraper
USER scraper

# Run the scraper
CMD ["python", "scraper.py"]