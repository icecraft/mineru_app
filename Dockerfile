FROM node:20-alpine AS node_base

# Install Python 3.10 and other necessary packages
RUN apk add --no-cache \
    python3=~3.12 \
    py3-pip 

# Set the working directory
WORKDIR /app

# Copy the rest of your application code
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt --no-cache-dir --break-system-packages

# Set environment variable
ENV GRADIO_SSR_MODE="true"

# Expose the port your app runs on
EXPOSE 7860

# Command to run your application
CMD ["python3", "src/app.py"]