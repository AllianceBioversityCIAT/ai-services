#!/usr/bin/env python3
"""
Entry point for running the AI Services Feedback API server.

This service provides comprehensive feedback management capabilities
for any AI service that generates user-facing content.
"""

import uvicorn
import argparse
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Main entry point for the AI Services Feedback API server."""
    parser = argparse.ArgumentParser(description="AI Services Feedback API Server")
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8001, 
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true", 
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--log-level", 
        default="info", 
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level (default: info)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Starting AI Services Feedback API server...")
    print(f"📍 Server will be available at: http://{args.host}:{args.port}")
    print(f"📚 API documentation: http://{args.host}:{args.port}/docs")
    print(f"❤️  Health check: http://{args.host}:{args.port}/health")
    print("🔄 Universal feedback collection for AI services")
    print("📊 Multi-service analytics and monitoring")
    print("🏗️ Service auto-registration enabled")
    
    # Start the server
    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()