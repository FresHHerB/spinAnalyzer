# SpinAnalyzer v2.0 - Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### For Local Development
- Python 3.10+
- Node.js 18+
- npm or yarn
- Git

### For Docker Deployment
- Docker 20.10+
- Docker Compose 2.0+

### For Production
- Linux server (Ubuntu 20.04+ recommended)
- 2GB+ RAM
- 10GB+ disk space
- Domain name (optional)
- SSL certificate (optional, recommended for HTTPS)

## Local Development

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/FresHHerB/spinAnalyzer.git
   cd spinAnalyzer
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare data and indices:**
   - Place poker hand history JSON files in `dataset/` directory
   - Indices will be automatically created on first run

5. **Run the API server:**
   ```bash
   python run_api.py
   ```

   The API will be available at `http://localhost:8000`

6. **Run tests:**
   ```bash
   # Unit tests
   pytest tests/test_range_analysis.py -v

   # Integration tests
   pytest tests/test_integration.py -v

   # All tests with coverage
   pytest -v --cov=src
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure API URL:**
   Create `.env` file in `frontend/` directory:
   ```
   VITE_API_URL=http://localhost:8000
   ```

4. **Run development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

5. **Build for production:**
   ```bash
   npm run build
   ```

## Docker Deployment

### Quick Start

1. **Build and run with docker-compose:**
   ```bash
   docker-compose up -d
   ```

   This will:
   - Build backend image
   - Build frontend image
   - Start both services
   - Create network and volumes

2. **Access the application:**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`

3. **View logs:**
   ```bash
   # All services
   docker-compose logs -f

   # Backend only
   docker-compose logs -f backend

   # Frontend only
   docker-compose logs -f frontend
   ```

4. **Stop services:**
   ```bash
   docker-compose down
   ```

5. **Rebuild after code changes:**
   ```bash
   docker-compose up -d --build
   ```

### Individual Docker Builds

**Backend:**
```bash
docker build -t spinanalyzer-backend .
docker run -p 8000:8000 \
  -v $(pwd)/dataset:/app/dataset \
  -v $(pwd)/indices:/app/indices \
  spinanalyzer-backend
```

**Frontend:**
```bash
cd frontend
docker build -t spinanalyzer-frontend .
docker run -p 3000:80 spinanalyzer-frontend
```

## Production Deployment

### Using Docker on Production Server

1. **Connect to your server:**
   ```bash
   ssh user@your-server-ip
   ```

2. **Install Docker and Docker Compose:**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo apt-get install docker-compose-plugin
   ```

3. **Clone repository:**
   ```bash
   git clone https://github.com/FresHHerB/spinAnalyzer.git
   cd spinAnalyzer
   ```

4. **Upload your dataset:**
   ```bash
   # From local machine
   scp -r dataset/* user@your-server-ip:~/spinAnalyzer/dataset/
   ```

5. **Update docker-compose.yml for production:**
   ```yaml
   services:
     frontend:
       environment:
         - VITE_API_URL=http://your-domain.com/api  # Update this
   ```

6. **Start services:**
   ```bash
   sudo docker-compose up -d
   ```

7. **Setup Nginx reverse proxy (optional):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

8. **Setup SSL with Let's Encrypt (recommended):**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Health Checks

The application includes health checks for both services:

**Backend health check:**
```bash
curl http://localhost:8000/health
```

**Frontend health check:**
```bash
curl http://localhost:3000/
```

**Docker health status:**
```bash
docker-compose ps
```

## Environment Configuration

### Backend Environment Variables

Create `.env` file in project root:
```
# API Configuration
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1

# FAISS Configuration
FAISS_INDEX_PATH=./indices
DATASET_PATH=./dataset

# API Server
HOST=0.0.0.0
PORT=8000
```

### Frontend Environment Variables

Create `.env` file in `frontend/` directory:
```
# Development
VITE_API_URL=http://localhost:8000

# Production
# VITE_API_URL=https://your-domain.com/api
```

## Troubleshooting

### Backend Issues

**Issue: API fails to start**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Dataset directory missing
mkdir -p dataset

# 2. Indices directory missing
mkdir -p indices

# 3. Port already in use
lsof -i :8000  # Find process using port
kill -9 <PID>  # Kill the process
```

**Issue: FAISS index build fails**
```bash
# Check dataset format
python -c "import json; json.load(open('dataset/your-file.json'))"

# Rebuild indices manually
rm -rf indices/*
python run_api.py  # Will rebuild on startup
```

**Issue: Tests fail**
```bash
# Ensure test dependencies installed
pip install pytest pytest-cov requests

# Run with verbose output
pytest -vv

# Run specific test
pytest tests/test_range_analysis.py::TestRangeAnalysis::test_basic -vv
```

### Frontend Issues

**Issue: Frontend build fails**
```bash
# Clear cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

**Issue: API connection fails**
```bash
# Check API URL in .env
cat frontend/.env

# Test API directly
curl http://localhost:8000/health

# Check browser console for CORS errors
# If CORS issue, verify backend CORS configuration
```

### Docker Issues

**Issue: Docker build fails**
```bash
# Check Docker version
docker --version
docker-compose --version

# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache
```

**Issue: Containers exit immediately**
```bash
# Check container logs
docker-compose logs backend
docker-compose logs frontend

# Check container status
docker-compose ps

# Run container interactively
docker run -it spinanalyzer-backend /bin/bash
```

**Issue: Volume permission errors**
```bash
# Fix permissions on Linux
sudo chown -R $USER:$USER dataset indices

# On Docker Desktop (Windows/Mac), ensure directories are in shared drives
```

### Performance Issues

**Issue: Slow API responses**
```bash
# Check index file sizes
ls -lh indices/

# Monitor resource usage
docker stats

# Optimize FAISS indices (reduce nlist for smaller datasets)
```

**Issue: High memory usage**
```bash
# Limit Docker memory
docker-compose.yml:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

## Monitoring

### Application Metrics

**Health endpoints:**
- Backend: `http://localhost:8000/health`
- Returns: API version, number of indices, total vectors

**Docker metrics:**
```bash
# Resource usage
docker stats

# Container health
docker inspect spinanalyzer-backend | grep Health
```

### Logs

**View application logs:**
```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Export logs
docker-compose logs > application.log
```

## Backup and Recovery

### Backup

**Backup datasets and indices:**
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz dataset/ indices/
```

**Backup Docker volumes:**
```bash
docker run --rm -v spinanalyzer_dataset-volume:/data -v $(pwd):/backup ubuntu tar czf /backup/dataset-backup.tar.gz /data
```

### Recovery

**Restore from backup:**
```bash
tar -xzf backup-20240115.tar.gz
docker-compose up -d
```

## CI/CD

The project includes GitHub Actions workflows:

**.github/workflows/ci.yml**
- Runs on push to main/develop
- Executes unit tests
- Runs integration tests
- Builds Docker images
- Code quality checks

**To enable:**
1. Push code to GitHub
2. GitHub Actions will automatically run
3. Check status in Actions tab

## Support

For issues and questions:
- GitHub Issues: https://github.com/FresHHerB/spinAnalyzer/issues
- Documentation: See `README.md`
- API Documentation: `http://localhost:8000/docs` (when running)

## Version

Current version: **2.0.0**
