#!/usr/bin/env python3
"""
LNCT Attendance Automation Script
Provides command-line tools for common automation tasks
"""

import argparse
import requests
import json
import sys
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

def check_health():
    """Check API health status"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ API is healthy")
            print(f"   Active sessions: {data['metrics']['active_sessions']}")
            print(f"   Cached data: {data['metrics']['cached_data_count']}")
            print(f"   Background tasks: {data['metrics']['background_tasks_running']}")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def get_attendance(username, password, use_cache=True):
    """Get attendance for a single user"""
    try:
        url = f"{API_BASE}/attendance"
        params = {"username": username, "password": password}
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                attendance = data['data']
                cache_status = " (cached)" if data.get('cached', False) else " (fresh)"
                
                print(f"✅ Attendance for {username}{cache_status}:")
                print(f"   Total Classes: {attendance['total_classes']}")
                print(f"   Present: {attendance['present']}")
                print(f"   Absent: {attendance['absent']}")
                print(f"   Percentage: {attendance['percentage']}%")
                print(f"   Last Updated: {attendance['last_updated']}")
                return True
            else:
                print(f"❌ Failed to get attendance: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error getting attendance: {e}")
        return False

def batch_attendance(user_file):
    """Process batch attendance from file"""
    try:
        with open(user_file, 'r') as f:
            lines = f.readlines()
        
        users = []
        for line in lines:
            line = line.strip()
            if line and ':' in line:
                username, password = line.split(':', 1)
                users.append(f"{username.strip()}:{password.strip()}")
        
        if not users:
            print("❌ No valid users found in file")
            return False
        
        users_param = ','.join(users)
        url = f"{API_BASE}/batch-attendance"
        
        print(f"🔄 Processing {len(users)} users...")
        response = requests.get(url, params={"users": users_param}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                results = data['results']
                successful = 0
                failed = 0
                
                for username, result in results.items():
                    if result['success']:
                        attendance = result['data']
                        cache_status = " (cached)" if result.get('cached', False) else " (fresh)"
                        print(f"✅ {username}{cache_status}: {attendance['percentage']}% ({attendance['present']}/{attendance['total_classes']})")
                        successful += 1
                    else:
                        print(f"❌ {username}: {result['error']}")
                        failed += 1
                
                print(f"\n📊 Summary: {successful} successful, {failed} failed")
                return True
            else:
                print(f"❌ Batch request failed: {data.get('message', 'Unknown error')}")
                return False
        else:
            print(f"❌ API request failed: {response.status_code}")
            return False
            
    except FileNotFoundError:
        print(f"❌ File not found: {user_file}")
        return False
    except Exception as e:
        print(f"❌ Error processing batch: {e}")
        return False

def cleanup():
    """Force cleanup of expired sessions and cache"""
    try:
        response = requests.get(f"{API_BASE}/cleanup", timeout=10)
        if response.status_code == 200:
            data = response.json()
            cleaned = data['cleaned']
            remaining = data['remaining']
            
            print("✅ Cleanup completed")
            print(f"   Cleaned sessions: {cleaned['sessions']}")
            print(f"   Cleaned cache entries: {cleaned['cache_entries']}")
            print(f"   Remaining sessions: {remaining['sessions']}")
            print(f"   Remaining cache: {remaining['cache_entries']}")
            return True
        else:
            print(f"❌ Cleanup failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return False

def monitor(interval=30):
    """Monitor API status continuously"""
    print(f"🔍 Monitoring API status (checking every {interval} seconds)")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}]", end=" ")
            check_health()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

def main():
    parser = argparse.ArgumentParser(description='LNCT Attendance Automation Tools')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health check
    subparsers.add_parser('health', help='Check API health status')
    
    # Single user attendance
    attendance_parser = subparsers.add_parser('get', help='Get attendance for a user')
    attendance_parser.add_argument('username', help='Username')
    attendance_parser.add_argument('password', help='Password')
    
    # Batch processing
    batch_parser = subparsers.add_parser('batch', help='Process batch attendance from file')
    batch_parser.add_argument('file', help='File with username:password pairs (one per line)')
    
    # Cleanup
    subparsers.add_parser('cleanup', help='Force cleanup expired sessions and cache')
    
    # Monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitor API status')
    monitor_parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds')
    
    # API base URL
    parser.add_argument('--api', default='http://localhost:8000', help='API base URL')
    
    args = parser.parse_args()
    
    if args.api:
        global API_BASE
        API_BASE = args.api
    
    if args.command == 'health':
        success = check_health()
    elif args.command == 'get':
        success = get_attendance(args.username, args.password)
    elif args.command == 'batch':
        success = batch_attendance(args.file)
    elif args.command == 'cleanup':
        success = cleanup()
    elif args.command == 'monitor':
        monitor(args.interval)
        return
    else:
        parser.print_help()
        return
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()