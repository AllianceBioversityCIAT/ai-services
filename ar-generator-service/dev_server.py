"""
Local Development Server for AICCRA Report Generator Service.

This module provides a simple way to run the FastAPI application locally
with uvicorn for development and testing purposes.

Usage:
    python dev_server.py
    
    or with custom port:
    python dev_server.py --port 8080
    
    or without auto-reload:
    python dev_server.py --no-reload

The server will be available at:
    - API: http://localhost:8000
    - Docs: http://localhost:8000/docs
    - Web UI: http://localhost:8000/web/
"""

import argparse
import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main():
    """Run the development server with configurable options."""
    parser = argparse.ArgumentParser(
        description="AICCRA Report Generator - Local Development Server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Logging level (default: info)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting AICCRA Report Generator Service (Development Mode)")
    print(f"📍 Server: http://{args.host}:{args.port}")
    print(f"📚 API Docs: http://localhost:{args.port}/docs")
    print(f"🖥️  Web UI: http://localhost:{args.port}/web/")
    print(f"🔄 Auto-reload: {'enabled' if args.reload else 'disabled'}")
    print("-" * 60)
    
    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        access_log=True
    )


if __name__ == "__main__":
    main()