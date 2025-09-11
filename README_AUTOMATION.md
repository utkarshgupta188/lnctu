# LNCT Attendance System - Automated Development & Deployment

🎯 **Fast and Easy Development Automation for LNCT University Attendance Checker**

This repository provides multiple API implementations for checking attendance from LNCT University's portal, with comprehensive automation for development and deployment.

## 🚀 Quick Start

### One-Command Setup
```bash
# Complete project setup
make setup
```

### Start Development Server
```bash
# Interactive server selection
make quick-start

# Or run specific services
make run-main     # Flask app (port 5000)
make run-api      # API Flask (port 5001)  
make run-fastapi  # FastAPI (port 8000)
make run-bot      # Bot Flask (port 5002)
```

## 📋 Available Services

| Service | File | Framework | Port | Description |
|---------|------|-----------|------|-------------|
| Main | `main.py` | Flask | 5000 | Main attendance service with rate limiting |
| API | `api.py` | Flask | 5001 | Clean API implementation |
| FastAPI | `at.py` | FastAPI | 8000 | High-performance async API |
| Bot | `bot.py` | Flask | 5002 | Bot service with caching |

## 🛠️ Development Automation

### Make Commands
```bash
make help          # Show all available commands
make install       # Install dependencies
make dev-install   # Install dev dependencies + tools
make test          # Run tests
make lint          # Run linting checks
make format        # Format code (black + isort)
make clean         # Clean temporary files
make health-check  # Run health checks
```

### Scripts
```bash
# Complete project setup
python scripts/setup.py

# Health checks
python scripts/health_check.py

# Deployment
python scripts/deploy.py heroku
python scripts/deploy.py vercel
python scripts/deploy.py all
```

## 🚀 Deployment Automation

### Supported Platforms

#### Heroku
```bash
# Setup Heroku remote
heroku git:remote -a your-app-name

# Deploy
make deploy-heroku
# or
python scripts/deploy.py heroku
```

#### Vercel
```bash
# Deploy
make deploy-vercel
# or
python scripts/deploy.py vercel
```

#### Render.com
- Configuration: `render.yaml`
- Connect GitHub repo to Render dashboard
- Automatic deployments on push to main

## 🔄 CI/CD Pipeline

### GitHub Actions
- **Automated Testing**: Tests on Python 3.9, 3.10, 3.11, 3.12
- **Code Quality**: Linting, formatting, import sorting
- **Security Scanning**: Safety and Bandit checks
- **Deployment Verification**: Config validation

### Pre-commit Hooks
- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- Trailing whitespace removal
- Large file checks

## 🧪 Testing & Quality

### Automated Checks
- Module import validation
- Flask/FastAPI app creation
- Code formatting verification
- Security vulnerability scanning

### Manual Testing
```bash
# Run health checks
make health-check

# Test specific service
curl http://localhost:5000/health  # Main Flask
curl http://localhost:8000/docs    # FastAPI docs
```

## 📁 Project Structure

```
lnctu/
├── 📄 main.py              # Main Flask app with rate limiting
├── 📄 api.py               # Clean API implementation
├── 📄 at.py                # FastAPI implementation
├── 📄 bot.py               # Bot service with caching
├── 📄 test.py              # Test implementation
├── 🔧 Makefile             # Development automation
├── 📋 requirements.txt     # Python dependencies
├── 🚀 Procfile             # Heroku deployment
├── 🟣 render.yaml          # Render.com deployment
├── ⚡ vercel.json          # Vercel deployment
├── 🗂️ .github/workflows/   # GitHub Actions
├── 🛠️ scripts/             # Automation scripts
│   ├── setup.py            # Project setup
│   ├── health_check.py     # Health checks
│   └── deploy.py           # Deployment automation
└── 📚 README_AUTOMATION.md # This file
```

## ⚙️ Configuration

### Development Tools
- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **pre-commit**: Git hooks

### Environment Variables
Create `.env` file for local development:
```bash
FLASK_ENV=development
FLASK_DEBUG=1
```

## 🔐 Security

### Automated Security Scanning
- **Safety**: Dependency vulnerability scanning
- **Bandit**: Python security linting
- **Pre-commit**: Prevents large file commits

### Best Practices
- All dependencies pinned
- SSL warnings disabled only for internal services
- Rate limiting implemented
- Session management

## 📊 Monitoring

### Health Endpoints
- Main Flask: `GET /health`
- FastAPI: `GET /health` and `GET /docs`

### Logging
- Structured logging with timestamps
- Error tracking and reporting
- Performance monitoring

## 🤝 Contributing

### Development Workflow
1. **Setup**: `make setup`
2. **Code**: Make your changes
3. **Format**: `make format`
4. **Test**: `make test`
5. **Commit**: Pre-commit hooks run automatically
6. **Push**: CI/CD pipeline runs tests

### Code Standards
- Python 3.9+ required
- Line length: 100 characters
- Black code formatting
- Type hints recommended
- Docstrings for public functions

## 🆘 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Reinstall dependencies
make clean
make install
```

#### Deployment Failures
```bash
# Check deployment configs
make deploy-check

# Verify all tests pass
make test
```

#### Port Conflicts
```bash
# Kill processes on ports
sudo lsof -ti:5000 | xargs kill -9
sudo lsof -ti:8000 | xargs kill -9
```

## 📚 API Documentation

### FastAPI
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Flask APIs
- **Health Check**: `GET /health`
- **Attendance**: `POST /attendance`

## 🎯 Performance Optimization

### Implemented Features
- Session caching (TTL-based)
- Rate limiting
- Connection pooling
- Async support (FastAPI)

### Monitoring
- Response time logging
- Error rate tracking
- Health check automation

---

## 🏆 Benefits of This Automation

✅ **Fast Setup**: One command project setup  
✅ **Easy Development**: Interactive server selection  
✅ **Quality Assurance**: Automated testing and linting  
✅ **Multi-Platform Deployment**: Heroku, Vercel, Render  
✅ **CI/CD Pipeline**: GitHub Actions automation  
✅ **Security**: Automated vulnerability scanning  
✅ **Documentation**: Self-documenting APIs  
✅ **Monitoring**: Health checks and logging  

**Start developing with confidence! 🚀**