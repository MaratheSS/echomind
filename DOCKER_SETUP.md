# Docker Setup Guide for EchoMind

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier deployment)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Create a `.env` file** in the project root with your API keys:
```env
GROQ_API_KEY=your_groq_key_here
AZURE_SPEECH_KEY=your_azure_key_here (optional)
AZURE_REGION=your_azure_region (optional)
GEMINI_API_KEY=your_gemini_key_here (optional)
```

2. **Build and run the container**:
```bash
docker-compose up -d
```

3. **Access the application**:
Open your browser and navigate to `http://localhost:8501`

4. **View logs**:
```bash
docker-compose logs -f
```

5. **Stop the container**:
```bash
docker-compose down
```

### Option 2: Using Docker directly

1. **Build the Docker image**:
```bash
docker build -t echomind:latest .
```

2. **Run the container**:
```bash
docker run -d \
  --name echomind \
  -p 8501:8501 \
  -e GROQ_API_KEY=your_groq_key_here \
  -e AZURE_SPEECH_KEY=your_azure_key_here \
  -e AZURE_REGION=your_azure_region \
  -e GEMINI_API_KEY=your_gemini_key_here \
  -v $(pwd)/.env:/app/.env:ro \
  -v echomind_data:/app/data \
  echomind:latest
```

3. **Access the application**:
Open your browser and navigate to `http://localhost:8501`

4. **View logs**:
```bash
docker logs -f echomind
```

5. **Stop the container**:
```bash
docker stop echomind
docker rm echomind
```

## Environment Variables

The following environment variables can be set:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for transcription and LLM |
| `AZURE_SPEECH_KEY` | No | Azure Speech API key for TTS |
| `AZURE_REGION` | No | Azure region (e.g., centralindia) |
| `GEMINI_API_KEY` | No | Google Gemini API key (for future use) |

## Volumes

The Docker setup uses volumes to persist data:

- **echomind_data**: Stores the SQLite database (`echomind_notes.db`)
- **downloads**: (Optional) Persists downloaded YouTube audio files

## Building for Production

For production deployment, you may want to:

1. **Use a specific tag**:
```bash
docker build -t echomind:v1.0.0 .
```

2. **Push to a container registry**:
```bash
docker tag echomind:v1.0.0 your-registry/echomind:v1.0.0
docker push your-registry/echomind:v1.0.0
```

## Troubleshooting

### Port already in use
If port 8501 is already in use, change it in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"  # Use 8502 on host instead
```

### Database not persisting
Ensure the volume is properly mounted:
```bash
docker volume ls | grep echomind_data
```

### FFmpeg not working
FFmpeg is included in the Docker image. If you encounter issues, check the container logs:
```bash
docker logs echomind
```

### API keys not working
Verify environment variables are set correctly:
```bash
docker exec echomind env | grep API_KEY
```

## Development Mode

For development with hot-reload, mount the source code:

```yaml
volumes:
  - ./main.py:/app/main.py
  - ./download.py:/app/download.py
```

Then restart the container to see changes.

## Security Notes

- Never commit `.env` files with real API keys
- Use Docker secrets or environment variables in production
- Consider using a reverse proxy (nginx) for HTTPS in production
- Regularly update the base image and dependencies

## System Requirements

- **Minimum**: 2 CPU cores, 2GB RAM
- **Recommended**: 4 CPU cores, 4GB RAM
- **Disk Space**: ~2GB for image + data

## Support

For issues or questions, please refer to the main README.md or create an issue in the project repository.

