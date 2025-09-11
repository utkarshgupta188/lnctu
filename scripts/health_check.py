#!/usr/bin/env python3
"""
Health check script for LNCT Attendance System
Tests if all services can be imported and basic functionality works
"""

import sys
import os
import importlib
import time
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import(module_name):
    """Test if a module can be imported"""
    try:
        importlib.import_module(module_name)
        return True, f"✓ {module_name}.py imported successfully"
    except Exception as e:
        return False, f"✗ {module_name}.py failed to import: {str(e)}"

def test_flask_apps():
    """Test Flask app creation"""
    results = []
    
    # Test main.py
    try:
        from main import app as main_app
        results.append((True, "✓ main.py Flask app created"))
    except Exception as e:
        results.append((False, f"✗ main.py Flask app failed: {str(e)}"))
    
    # Test api.py
    try:
        from api import app as api_app
        results.append((True, "✓ api.py Flask app created"))
    except Exception as e:
        results.append((False, f"✗ api.py Flask app failed: {str(e)}"))
    
    # Test bot.py
    try:
        from bot import app as bot_app
        results.append((True, "✓ bot.py Flask app created"))
    except Exception as e:
        results.append((False, f"✗ bot.py Flask app failed: {str(e)}"))
    
    return results

def test_fastapi_app():
    """Test FastAPI app creation"""
    try:
        from at import app as fastapi_app
        return True, "✓ at.py FastAPI app created"
    except Exception as e:
        return False, f"✗ at.py FastAPI app failed: {str(e)}"

def main():
    """Run all health checks"""
    print("🏥 LNCT Attendance System Health Check")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_passed = True
    
    # Test imports
    print("📦 Testing module imports...")
    modules = ['main', 'api', 'bot', 'at', 'test']
    for module in modules:
        passed, message = test_import(module)
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    print()
    
    # Test Flask apps
    print("🌐 Testing Flask applications...")
    flask_results = test_flask_apps()
    for passed, message in flask_results:
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    print()
    
    # Test FastAPI app
    print("⚡ Testing FastAPI application...")
    passed, message = test_fastapi_app()
    print(f"  {message}")
    if not passed:
        all_passed = False
    
    print()
    print("=" * 50)
    
    if all_passed:
        print("🎉 All health checks passed!")
        sys.exit(0)
    else:
        print("❌ Some health checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()