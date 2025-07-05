#!/usr/bin/env python3
"""
Enhanced CEC Control with Vendor-Specific Commands, Logging, and Command Tracking
"""
import subprocess
import time
import logging
import json
import os
from datetime import datetime

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/cec_commands.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cec_control")

# Global command history for tracking successful commands
COMMAND_HISTORY = []
SUCCESSFUL_COMMANDS = []

def log_command(command, result, success=False, vendor="unknown"):
    """Log command with timestamp and result"""
    timestamp = datetime.now().isoformat()
    command_entry = {
        "timestamp": timestamp,
        "command": command,
        "result": result,
        "success": success,
        "vendor": vendor,
        "raw_cec_command": command if command.startswith("tx ") else None
    }
    
    # Add to history
    COMMAND_HISTORY.append(command_entry)
    
    # Track successful commands separately
    if success:
        SUCCESSFUL_COMMANDS.append(command_entry)
    
    # Log to file
    logger.info(f"CEC_CMD: {command} | SUCCESS: {success} | VENDOR: {vendor}")
    
    return command_entry

def get_command_history(successful_only=False):
    """Get command history in various formats"""
    commands = SUCCESSFUL_COMMANDS if successful_only else COMMAND_HISTORY
    return commands

def export_successful_commands():
    """Export successful commands for BrightSign"""
    successful = get_command_history(successful_only=True)
    
    export_data = {
        "export_time": datetime.now().isoformat(),
        "total_successful_commands": len(successful),
        "commands": successful,
        "brightsign_format": []
    }
    
    # Convert to BrightSign format
    for cmd in successful:
        if cmd.get("raw_cec_command"):
            # Convert tx commands to BrightSign ASCII format
            cec_cmd = cmd["raw_cec_command"]
            if cec_cmd.startswith("tx "):
                # Remove "tx " and convert to ASCII string
                hex_part = cec_cmd[3:].replace(":", "")
                brightsign_cmd = {
                    "description": f"Vendor: {cmd['vendor']} | Original: {cec_cmd}",
                    "brightsign_ascii": hex_part,
                    "brightsign_command": f'BrightControl Send Ascii String "{hex_part}"',
                    "timestamp": cmd["timestamp"]
                }
                export_data["brightsign_format"].append(brightsign_cmd)
    
    return export_data

def save_command_log(filename=None):
    """Save command history to file"""
    if not filename:
        filename = f"/tmp/cec_commands_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    export_data = export_successful_commands()
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    logger.info(f"Command history saved to {filename}")
    return filename

# Vendor-specific configurations
VENDOR_CONFIGS = {
    "optoma": {
        "power_on_sequence": [
            "tx 10:04",        # Image View On
            "tx 10:82:10:00",  # Active Source HDMI1
            "tx 10:04",        # Image View On (retry)
        ],
        "power_on_delay": 1.0,
        "retry_count": 3,
        "power_off_delay": 0.5
    },
    "nec": {
        "power_on_sequence": [
            "tx 10:04",        # Image View On
            "tx 10:82:10:00",  # Active Source HDMI1
        ],
        "power_on_delay": 2.0,  # NEC needs longer delays
        "retry_count": 2,
        "power_off_delay": 1.0,
        "requires_cec_version": "1.4"  # NEC often needs specific CEC version
    },
    "epson": {
        "power_on_sequence": [
            "tx 10:8C",       # CEC wake-up (Get Vendor ID)
            "tx 10:04",       # Image View On
            "tx 10:82:10:00", # Active Source HDMI1
            "tx 10:8C",       # CEC confirm (Get Vendor ID again)
        ],
        "power_on_delay": 1.5,
        "retry_count": 2,
        "requires_cec_reset": True,
        "link_buffer_optimization": True
    },
    "samsung": {
        "input_commands": {
            "hdmi1": "tx 4F:82:10:00",
            "hdmi2": "tx 4F:82:20:00", 
            "hdmi3": "tx 4F:82:30:00",
            "hdmi4": "tx 4F:82:40:00",
            "tv": "tx 4F:9D:00:00"
        }
    },
    "lg": {
        "input_commands": {
            "hdmi1": "tx 10:44:F1",
            "hdmi2": "tx 10:44:F2",
            "hdmi3": "tx 10:44:F3",
            "hdmi4": "tx 10:44:F4"
        }
    }
}

# Core command library
CORE_COMMANDS = {
    # Power Control
    "POWER_ON": "on 0",
    "POWER_OFF": "standby 0",
    "POWER_STATUS": "pow 0",
    
    # Input Control (Universal)
    "HDMI_1": "tx 4F:82:10:00",
    "HDMI_2": "tx 4F:82:20:00",
    "HDMI_3": "tx 4F:82:30:00",
    "HDMI_4": "tx 4F:82:40:00",
    "ACTIVE_SOURCE": "as",
    "INACTIVE_SOURCE": "is",
    
    # Volume Control
    "VOLUME_UP": "volup",
    "VOLUME_DOWN": "voldown",
    "MUTE": "mute",
    
    # System Information
    "SCAN": "scan",
    "VENDOR_ID": "tx 10:8C",
    "PHYSICAL_ADDRESS": "tx 10:83",
    "OSD_NAME": "tx 10:46",
    "CEC_VERSION": "tx 10:9F",
    
    # Navigation
    "UP": "tx 10:44:01",
    "DOWN": "tx 10:44:02", 
    "LEFT": "tx 10:44:03",
    "RIGHT": "tx 10:44:04",
    "SELECT": "tx 10:44:00",
    "BACK": "tx 10:44:0D",
    "MENU": "tx 10:44:09",
    "EXIT": "tx 10:44:0D",
    
    # Numbers
    "NUMBER_0": "tx 10:44:20",
    "NUMBER_1": "tx 10:44:21",
    "NUMBER_2": "tx 10:44:22",
    "NUMBER_3": "tx 10:44:23",
    "NUMBER_4": "tx 10:44:24",
    "NUMBER_5": "tx 10:44:25",
    "NUMBER_6": "tx 10:44:26",
    "NUMBER_7": "tx 10:44:27",
    "NUMBER_8": "tx 10:44:28",
    "NUMBER_9": "tx 10:44:29",
}

def execute_cec_command(command, timeout=15, vendor="unknown"):
    """Execute CEC command and return result with logging"""
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
        
        success = process.returncode == 0
        result = f"Command executed: {command}\nOutput: {stdout}" if success else f"Command failed: {stderr}"
        
        # Log the command
        log_command(command, result, success, vendor)
        
        return result
            
    except subprocess.TimeoutExpired:
        process.kill()
        result = f"Command timed out: {command}"
        log_command(command, result, False, vendor)
        return result
    except Exception as e:
        result = f"Error executing command: {str(e)}"
        log_command(command, result, False, vendor)
        return result

def get_device_vendor():
    """Detect device vendor from CEC scan"""
    try:
        scan_result = execute_cec_command("scan", timeout=10)
        vendor_lower = scan_result.lower()
        
        if "optoma" in vendor_lower:
            return "optoma"
        elif "nec" in vendor_lower:
            return "nec"
        elif "epson" in vendor_lower:
            return "epson"
        elif "samsung" in vendor_lower:
            return "samsung"
        elif "lg" in vendor_lower:
            return "lg"
        else:
            return "generic"
    except Exception as e:
        logger.error(f"Error detecting vendor: {e}")
        return "generic"

def epson_cec_reset():
    """Reset CEC link for Epson projectors (simulates manual CEC toggle)"""
    logger.info("Performing Epson CEC reset sequence")
    reset_commands = [
        "tx 10:8C",  # Get Vendor ID
        "tx 10:83",  # Get Physical Address
        "tx 10:46",  # Get OSD Name
    ]
    
    for cmd in reset_commands:
        execute_cec_command(cmd)
        time.sleep(0.5)
    
    logger.info("Epson CEC reset complete")

def vendor_specific_power_on(vendor="generic"):
    """Execute vendor-specific power-on sequence with logging"""
    if vendor not in VENDOR_CONFIGS:
        return execute_cec_command("on 0", vendor=vendor)
    
    config = VENDOR_CONFIGS[vendor]
    results = []
    
    logger.info(f"Starting {vendor} power-on sequence")
    
    # Epson-specific: Perform CEC reset first
    if vendor == "epson" and config.get("requires_cec_reset", False):
        epson_cec_reset()
        time.sleep(1)  # Wait after reset
    
    # Set CEC version if required (NEC projectors)
    if "requires_cec_version" in config:
        version_cmd = f"cec-ctl -d0 --tv --cec-version-{config['requires_cec_version']}"
        try:
            subprocess.run(version_cmd.split(), check=True)
            logger.info(f"Set CEC version to {config['requires_cec_version']}")
        except Exception as e:
            logger.warning(f"Failed to set CEC version: {e}")
    
    # Execute power-on sequence
    for attempt in range(config.get("retry_count", 1)):
        logger.info(f"Power-on attempt {attempt + 1} for {vendor}")
        
        sequence_success = True
        for cmd in config["power_on_sequence"]:
            result = execute_cec_command(cmd, vendor=vendor)
            results.append(result)
            
            # Check if individual command succeeded
            if "failed" in result.lower() or "error" in result.lower():
                sequence_success = False
            
            time.sleep(config.get("power_on_delay", 0.5))
        
        # Check if successful
        time.sleep(2)  # Wait for device to respond
        status = execute_cec_command("pow 0", vendor=vendor)
        if "on" in status.lower():
            # Log successful sequence
            sequence_cmd = " && ".join(config["power_on_sequence"])
            log_command(f"SEQUENCE: {sequence_cmd}", f"Power-on successful after {attempt + 1} attempts", True, vendor)
            return f"✅ Power-on successful after {attempt + 1} attempts\n" + "\n".join(results)
    
    # Log failed sequence
    sequence_cmd = " && ".join(config["power_on_sequence"])
    log_command(f"SEQUENCE: {sequence_cmd}", f"Power-on failed after {config.get('retry_count', 1)} attempts", False, vendor)
    return f"❌ Power-on failed after {config.get('retry_count', 1)} attempts\n" + "\n".join(results)

def vendor_specific_power_off(vendor="generic"):
    """Execute vendor-specific power-off sequence"""
    if vendor not in VENDOR_CONFIGS:
        return execute_cec_command("standby 0", vendor=vendor)
    
    config = VENDOR_CONFIGS[vendor]
    
    # Add delay before power-off for some vendors
    if "power_off_delay" in config:
        time.sleep(config["power_off_delay"])
    
    result = execute_cec_command("standby 0", vendor=vendor)
    
    # NEC projectors sometimes need a second command
    if vendor == "nec" and "failed" in result.lower():
        time.sleep(1)
        result = execute_cec_command("standby 0", vendor=vendor)
    
    return result

def vendor_specific_input(vendor="generic", input_name="hdmi1"):
    """Execute vendor-specific input switching"""
    if vendor in VENDOR_CONFIGS and "input_commands" in VENDOR_CONFIGS[vendor]:
        input_cmd = VENDOR_CONFIGS[vendor]["input_commands"].get(input_name)
        if input_cmd:
            return execute_cec_command(input_cmd, vendor=vendor)
    
    # Fall back to generic command
    generic_inputs = {
        "hdmi1": "tx 4F:82:10:00",
        "hdmi2": "tx 4F:82:20:00",
        "hdmi3": "tx 4F:82:30:00",
        "hdmi4": "tx 4F:82:40:00"
    }
    
    if input_name in generic_inputs:
        return execute_cec_command(generic_inputs[input_name], vendor=vendor)
    
    return f"Unknown input: {input_name}"

def power_on():
    """Smart power-on with vendor detection and logging"""
    vendor = get_device_vendor()
    logger.info(f"Detected vendor: {vendor}")
    return vendor_specific_power_on(vendor)

def power_off():
    """Smart power-off with vendor detection and logging"""
    vendor = get_device_vendor()
    logger.info(f"Detected vendor: {vendor}")
    return vendor_specific_power_off(vendor)

def get_power_status():
    """Get power status with enhanced info and logging"""
    vendor = get_device_vendor()
    result = execute_cec_command("pow 0", vendor=vendor)
    
    # Add vendor info
    return f"Vendor: {vendor}\n{result}"

def switch_input(input_name):
    """Smart input switching with vendor detection and logging"""
    vendor = get_device_vendor()
    logger.info(f"Switching to {input_name} on {vendor} device")
    return vendor_specific_input(vendor, input_name.lower())

def send_custom_command(command):
    """Send custom CEC command with logging"""
    vendor = get_device_vendor()
    return execute_cec_command(command, vendor=vendor)

def send_core_command(command_name):
    """Send predefined core command with logging"""
    vendor = get_device_vendor()
    if command_name.upper() in CORE_COMMANDS:
        return execute_cec_command(CORE_COMMANDS[command_name.upper()], vendor=vendor)
    else:
        return f"Unknown command: {command_name}"

def scan_devices():
    """Enhanced device scanning with vendor detection"""
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
    
    # Filter out the Pi itself
    real_devices = []
    for device in devices:
        name = device.get('name', '').lower()
        vendor = device.get('vendor', '').lower()
        if 'cectester' not in name and 'pulse eight' not in vendor and 'recorder' not in name:
            real_devices.append(device)
    
    # Enhanced output with vendor detection
    if real_devices:
        summary = "🔍 Detected CEC Devices:\n"
        for device in real_devices:
            vendor_name = device.get('vendor', 'Unknown')
            device_name = device.get('name', 'Unknown')
            power_status = device.get('power', 'unknown')
            
            # Add vendor-specific notes
            vendor_note = ""
            if "optoma" in vendor_name.lower():
                vendor_note = " (May need special power-on sequence)"
            elif "nec" in vendor_name.lower():
                vendor_note = " (May need CEC v1.4 and longer delays)"
            elif "epson" in vendor_name.lower():
                vendor_note = " (May need CEC reset after power cycle)"
            elif "samsung" in vendor_name.lower():
                vendor_note = " (Supports Anynet+ commands)"
            elif "lg" in vendor_name.lower():
                vendor_note = " (Supports SimpLink commands)"
            
            summary += f"• {device_name} ({vendor_name}) - {power_status}{vendor_note}\n"
        
        return summary.strip()
    else:
        return "No external CEC devices found"

def get_brightsign_export():
    """Get successful commands in BrightSign format"""
    return export_successful_commands()

def get_command_log():
    """Get recent command history"""
    return {
        "recent_commands": COMMAND_HISTORY[-10:],  # Last 10 commands
        "successful_commands": len(SUCCESSFUL_COMMANDS),
        "total_commands": len(COMMAND_HISTORY)
    }

def get_device_info():
    """Get comprehensive device information"""
    info = {
        "scan": scan_devices(),
        "vendor_id": execute_cec_command("tx 10:8C"),
        "physical_address": execute_cec_command("tx 10:83"),
        "osd_name": execute_cec_command("tx 10:46"),
        "cec_version": execute_cec_command("tx 10:9F")
    }
    
    return json.dumps(info, indent=2)
