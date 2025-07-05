#!/usr/bin/env python3
"""
Simple CEC Control for Flipper
"""
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cec_control")

def execute_cec_command(command, timeout=15):
    """Execute CEC command and return result"""
    try:
        logger.info(f"Executing CEC command: {command}")
        
        process = subprocess.Popen(
            ['cec-client', '-s', '-d', '1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(input=command + '\n', timeout=timeout)
        
        if process.returncode == 0:
            return f"Command executed: {command}\nOutput: {stdout}"
        else:
            return f"Command failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        return f"Command timed out: {command}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def power_on():
    return execute_cec_command("on 0")

def power_off():
    return execute_cec_command("standby 0")

def get_power_status():
    return execute_cec_command("pow")

def send_custom_command(command):
    return execute_cec_command(command)

def scan_devices():
    """Scan for CEC devices and return clean results"""
    raw_result = execute_cec_command("scan", timeout=15)
    
    # Parse and extract useful info
    devices = []
    lines = raw_result.split('\n')
    
    current_device = {}
    for line in lines:
        line = line.strip()
        if line.startswith('device #'):
            if current_device:
                devices.append(current_device)
            current_device = {'number': line.split(':')[0].replace('device #', '')}
        elif line.startswith('address:'):
            current_device['address'] = line.split(':', 1)[1].strip()
        elif line.startswith('vendor:'):
            current_device['vendor'] = line.split(':', 1)[1].strip()
        elif line.startswith('osd string:'):
            current_device['name'] = line.split(':', 1)[1].strip()
        elif line.startswith('power status:'):
            current_device['power'] = line.split(':', 1)[1].strip()
    
    if current_device:
        devices.append(current_device)
    
    # Filter out the Pi itself (CECTester, Pulse Eight, or any Recorder device)
    real_devices = []
    for device in devices:
        name = device.get('name', '').lower()
        vendor = device.get('vendor', '').lower()
        if 'cectester' not in name and 'pulse eight' not in vendor and 'recorder' not in name:
            real_devices.append(device)
    
    # Return clean summary of actual devices
    if real_devices:
        summary = ""
        for device in real_devices:
            summary += f"• {device.get('name', 'Unknown')} ({device.get('vendor', 'Unknown')}) - {device.get('power', 'unknown')}\n"
        return summary.strip()
    else:
        return "No external CEC devices found"
