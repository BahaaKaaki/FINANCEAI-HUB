#!/usr/bin/env python3
"""
Simple health check script for deployment monitoring.
"""

import sys
import requests
import os

def health_check():
    """Perform basic health check."""
    try:
        # Get port from environment or default to 8000
        port = os.environ.get('PORT', '8000')
        url = f"http://localhost:{port}/health"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') in ['healthy', 'ok']:
                print("✅ Health check passed")
                return True
        
        print(f"❌ Health check failed: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)