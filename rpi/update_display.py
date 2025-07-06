#!/usr/bin/env python3
import subprocess
import sys
import os

def update_display(status):
    """Update HDMI display with pre-made status image"""
    user_home = os.path.expanduser('~')
    image_map = {
        'ready': f'{user_home}/status_ready.png',
        'sending': f'{user_home}/status_sending.png',
        'success': f'{user_home}/status_success.png',
        'error': f'{user_home}/status_error.png'
    }
    
    if status in image_map:
        try:
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            env['HOME'] = user_home
            
            # Kill existing feh processes first
            subprocess.run(['pkill', '-f', 'feh'], check=False)
            
            # Start new feh process
            subprocess.Popen([
                'feh', '--fullscreen', '--hide-pointer', 
                image_map[status]
            ], env=env)
            
            print(f"Display updated to: {status}")
        except Exception as e:
            print(f"Display update failed: {e}")
    else:
        print(f"Unknown status: {status}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        update_display(sys.argv[1])
    else:
        update_display('ready')
