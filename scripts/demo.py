#!/usr/bin/env python3
"""
Automation Demo Script for LNCT Attendance System
Showcases the automated development workflow
"""

import subprocess
import time
import sys

def run_demo_command(command, description):
    """Run a command and show the output"""
    print(f"\n🔧 {description}")
    print("=" * 60)
    print(f"Command: {command}")
    print("-" * 60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("✅ Success!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
    
    time.sleep(1)

def main():
    print("🚀 LNCT Attendance System - Automation Demo")
    print("=" * 60)
    print("This demo shows how automation makes development fast and easy!")
    print()
    
    # Show available commands
    run_demo_command("make help", "1. Show all available automation commands")
    
    # Run tests
    run_demo_command("make test", "2. Run automated tests")
    
    # Run health checks
    run_demo_command("make health-check", "3. Run service health checks")
    
    # Show project structure
    run_demo_command("ls -la", "4. Show project structure with automation files")
    
    print("\n" + "=" * 60)
    print("🎉 Automation Demo Complete!")
    print("\nKey Benefits:")
    print("✅ One-command setup: make setup")
    print("✅ Interactive server selection: make quick-start")
    print("✅ Automated testing: make test")
    print("✅ Code quality: make format && make lint")
    print("✅ Easy deployment: make deploy-heroku")
    print("✅ Health monitoring: make health-check")
    print("\n🎯 Development is now fast and easy!")

if __name__ == "__main__":
    main()