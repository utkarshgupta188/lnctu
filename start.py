#!/usr/bin/env python3
"""
LNCT Attendance API - Automated Startup Script
This script provides easy startup with configuration options
"""

import argparse
import os
import sys
import uvicorn
from at import app

def main():
    parser = argparse.ArgumentParser(description='LNCT Attendance API - Automated')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to (default: 8000)')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes')
    parser.add_argument('--log-level', default='info', choices=['debug', 'info', 'warning', 'error'], 
                       help='Log level (default: info)')
    
    args = parser.parse_args()
    
    print("🚀 Starting LNCT Attendance API - Automated")
    print(f"📍 Server: http://{args.host}:{args.port}")
    print("🔧 Features: Session Caching, Auto-Retry, Background Processing, Rate Limiting")
    print("📚 Docs: http://{args.host}:{args.port}/docs")
    print("❤️  Health: http://{args.host}:{args.port}/health")
    print("-" * 60)
    
    # Set environment variables for configuration
    os.environ['LNCT_API_HOST'] = args.host
    os.environ['LNCT_API_PORT'] = str(args.port)
    
    try:
        uvicorn.run(
            "at:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()