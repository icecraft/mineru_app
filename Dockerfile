FROM python:3.10-slim

# Install Node.js
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the rest of your application code
COPY . .

# Install Python dependencies
RUN pip install requests \
    python-dotenv \
    PyMuPDF==1.24.9 \
    gradio \
    gradio_client \
    gradio_pdf==0.0.19

# Expose the port your app runs on
EXPOSE 7860

ENV GRADIO_SSR_MODE="true"

# Command to run your application
CMD ["python3", "src/app.py"]