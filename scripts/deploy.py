#!/usr/bin/env python3
"""
Deployment automation script for LNCT Attendance System
Handles deployment to multiple platforms
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def run_command(command, description=""):
    """Run a shell command and handle errors"""
    print(f"🚀 {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False, e.stderr

def check_git_status():
    """Check if git repo is clean"""
    success, output = run_command("git status --porcelain", "Checking git status")
    if not success:
        return False
    
    if output.strip():
        print("⚠️  Warning: You have uncommitted changes")
        print("   Consider committing your changes before deployment")
        return False
    
    print("✅ Git repository is clean")
    return True

def run_tests():
    """Run tests before deployment"""
    print("🧪 Running tests before deployment...")
    success, _ = run_command("python scripts/health_check.py", "Running health checks")
    if not success:
        print("❌ Tests failed! Aborting deployment.")
        return False
    
    print("✅ All tests passed!")
    return True

def deploy_to_heroku():
    """Deploy to Heroku"""
    print("\n🟢 Deploying to Heroku...")
    
    # Check if Heroku CLI is installed
    success, _ = run_command("heroku --version", "Checking Heroku CLI")
    if not success:
        print("❌ Heroku CLI not found. Install it from https://devcenter.heroku.com/articles/heroku-cli")
        return False
    
    # Check if heroku remote exists
    success, _ = run_command("git remote get-url heroku", "Checking Heroku remote")
    if not success:
        print("⚠️  Heroku remote not configured")
        print("   Configure it with: heroku git:remote -a your-app-name")
        return False
    
    # Deploy
    success, _ = run_command("git push heroku HEAD:main", "Pushing to Heroku")
    if success:
        print("✅ Deployed to Heroku successfully!")
        run_command("heroku open", "Opening Heroku app")
    
    return success

def deploy_to_vercel():
    """Deploy to Vercel"""
    print("\n⚡ Deploying to Vercel...")
    
    # Check if Vercel CLI is installed
    success, _ = run_command("vercel --version", "Checking Vercel CLI")
    if not success:
        print("❌ Vercel CLI not found. Install it with: npm i -g vercel")
        return False
    
    # Deploy
    success, _ = run_command("vercel --prod", "Deploying to Vercel")
    if success:
        print("✅ Deployed to Vercel successfully!")
    
    return success

def show_render_instructions():
    """Show instructions for Render deployment"""
    print("\n🟣 Render Deployment Instructions:")
    print("   1. Connect your GitHub repository to Render dashboard")
    print("   2. Create a new Web Service")
    print("   3. Use the render.yaml configuration file")
    print("   4. Your app will be automatically deployed on every push to main")
    print("   📁 Configuration file: render.yaml")

def create_deployment_summary():
    """Create a deployment summary"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "git_commit": "",
        "deployment_targets": [],
        "status": "completed"
    }
    
    # Get current git commit
    success, commit = run_command("git rev-parse HEAD", "Getting current commit")
    if success:
        summary["git_commit"] = commit.strip()
    
    return summary

def main():
    """Main deployment function"""
    if len(sys.argv) < 2:
        print("🚀 LNCT Attendance System Deployment")
        print("=" * 50)
        print("Usage: python scripts/deploy.py <platform>")
        print("\nAvailable platforms:")
        print("  heroku  - Deploy to Heroku")
        print("  vercel  - Deploy to Vercel")
        print("  render  - Show Render instructions")
        print("  all     - Deploy to all platforms")
        print("\nExample: python scripts/deploy.py heroku")
        sys.exit(1)
    
    platform = sys.argv[1].lower()
    
    print("🚀 LNCT Attendance System Deployment")
    print("=" * 50)
    print(f"Target platform: {platform}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Pre-deployment checks
    if not check_git_status():
        print("⚠️  Proceeding with uncommitted changes...")
    
    if not run_tests():
        sys.exit(1)
    
    # Deploy based on platform
    success = True
    
    if platform == "heroku":
        success = deploy_to_heroku()
    elif platform == "vercel":
        success = deploy_to_vercel()
    elif platform == "render":
        show_render_instructions()
    elif platform == "all":
        print("\n🌐 Deploying to all platforms...")
        heroku_success = deploy_to_heroku()
        vercel_success = deploy_to_vercel()
        show_render_instructions()
        success = heroku_success and vercel_success
    else:
        print(f"❌ Unknown platform: {platform}")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 50)
    if success:
        print("🎉 Deployment completed successfully!")
    else:
        print("❌ Deployment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()