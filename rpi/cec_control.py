#!/usr/bin/env python3
"""
Simple CEC Control for Flipper
"""
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cec_control")

def execute_cec_command(command, timeout=5):
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

def scan_devices():
    return execute_cec_command("scan")

def get_power_status():
    return execute_cec_command("pow")

def send_custom_command(command):
    return execute_cec_command(command)
