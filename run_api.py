"""
SpinAnalyzer v2.0 - API Server Launcher
Starts the FastAPI application
"""

import sys
from pathlib import Path
import uvicorn
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Launch the API server"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info("🚀 Starting SpinAnalyzer v2.0 API Server...")
    logger.info("📚 API Documentation will be available at: http://localhost:8000/docs")
    logger.info("📊 Alternative docs at: http://localhost:8000/redoc")
    logger.info("")

    try:
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True,
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped by user")
    except Exception as e:
        logger.exception(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
