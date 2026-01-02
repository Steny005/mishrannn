# Use Node.js 20 as the base image
FROM node:20-slim

# Install system dependencies: Python, FFmpeg, and audio libraries
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy Node.js dependencies and install
COPY package*.json ./
RUN npm install --production

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir librosa requests numpy soundfile

# Copy the rest of the server code
COPY . .

# Ensure necessary directories exist
RUN mkdir -p recordings cut_frames frames

# Set Environment Variables
ENV NODE_ENV=production
ENV AI_DIRECTOR_URL=https://hari-n8n.laddu.cc/webhook/ai-director-input

# Expose the WebSocket/HTTP port
EXPOSE 8080

# Start the Node.js server
CMD ["node", "server.js"]