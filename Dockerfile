# Use official lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /code

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 7860 (default for Hugging Face Spaces)
EXPOSE 7860

# Run alembic migrations and start server using uvicorn on port 7860
CMD python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860
