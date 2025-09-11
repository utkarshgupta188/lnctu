#!/usr/bin/env python3
"""
Setup script for LNCT Attendance System
Automates initial project setup and development environment configuration
"""

import os
import sys
import subprocess
import platform

def run_command(command, description="", ignore_errors=False):
    """Run a shell command and handle errors"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if not ignore_errors:
            print(f"   ❌ Error: {e}")
            if e.stderr:
                print(f"   {e.stderr.strip()}")
            return False
        else:
            print(f"   ⚠️ Warning: {e} (ignored)")
            return True

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major != 3 or version.minor < 9:
        print(f"❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def setup_virtual_environment():
    """Set up virtual environment if not already in one"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
        return True
    
    print("🔧 Setting up virtual environment...")
    if not run_command("python -m venv venv", "Creating virtual environment"):
        return False
    
    print("💡 Virtual environment created!")
    print("   Activate it with:")
    if platform.system() == "Windows":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    return True

def install_dependencies():
    """Install project dependencies"""
    print("📦 Installing dependencies...")
    
    # Upgrade pip first
    if not run_command("python -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install main dependencies
    if not run_command("pip install -r requirements.txt", "Installing main dependencies"):
        return False
    
    # Install development dependencies
    dev_packages = ["black", "flake8", "isort", "pre-commit", "pytest", "safety", "bandit"]
    dev_cmd = f"pip install {' '.join(dev_packages)}"
    if not run_command(dev_cmd, "Installing development dependencies"):
        return False
    
    return True

def setup_pre_commit():
    """Set up pre-commit hooks"""
    print("🪝 Setting up pre-commit hooks...")
    
    # Create pre-commit config
    config_content = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=100]
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=100]
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203,W503]
"""
    
    with open(".pre-commit-config.yaml", "w") as f:
        f.write(config_content)
    
    # Install pre-commit hooks
    run_command("pre-commit install", "Installing pre-commit hooks", ignore_errors=True)
    return True

def setup_development_config():
    """Create development configuration files"""
    print("⚙️ Setting up development configuration...")
    
    # Create .flake8 config
    flake8_config = """[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    venv,
    .venv,
    build,
    dist
"""
    with open(".flake8", "w") as f:
        f.write(flake8_config)
    
    # Create pyproject.toml for black and isort
    pyproject_config = """[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311', 'py312']

[tool.isort]
profile = "black"
line_length = 100
"""
    with open("pyproject.toml", "w") as f:
        f.write(pyproject_config)
    
    return True

def run_initial_checks():
    """Run initial health checks and formatting"""
    print("🔍 Running initial checks...")
    
    # Format code
    run_command("black --line-length=100 *.py", "Formatting Python files", ignore_errors=True)
    run_command("isort *.py", "Sorting imports", ignore_errors=True)
    
    # Run health check
    run_command("python scripts/health_check.py", "Running health check")
    
    return True

def main():
    """Main setup function"""
    print("🚀 LNCT Attendance System Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup virtual environment (optional)
    setup_virtual_environment()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup pre-commit
    setup_pre_commit()
    
    # Setup development config
    setup_development_config()
    
    # Run initial checks
    run_initial_checks()
    
    print("\n" + "=" * 50)
    print("🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Use 'make help' to see available commands")
    print("2. Use 'make quick-start' to run a development server")
    print("3. Use 'make test' to run tests")
    print("4. Use 'make format' to format code")
    print("\nHappy coding! 🎯")

if __name__ == "__main__":
    main()