#!/usr/bin/env python3
"""
CEC Flipper Control - Main Application
Multi-interface CEC controller with Flipper SD card logging
"""
import time
import logging
import sys
import signal
import json
import threading
import serial
import os
import cec_control
from http.server import HTTPServer
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Flipper SD card logging
FLIPPER_LOG_FILE = "/tmp/flipper_cec_log.txt"
FLIPPER_EXPORT_FILE = "/tmp/flipper_brightsign_export.json"

def write_flipper_log(message):
    """Write log message to Flipper-accessible file"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(FLIPPER_LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        logger.error(f"Failed to write Flipper log: {e}")

def save_flipper_export():
    """Save BrightSign export to Flipper-accessible file"""
    try:
        export_data = cec_control.get_brightsign_export()
        with open(FLIPPER_EXPORT_FILE, "w") as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"BrightSign export saved to {FLIPPER_EXPORT_FILE}")
    except Exception as e:
        logger.error(f"Failed to save Flipper export: {e}")

def get_flipper_log():
    """Get recent Flipper log entries"""
    try:
        if os.path.exists(FLIPPER_LOG_FILE):
            with open(FLIPPER_LOG_FILE, "r") as f:
                lines = f.readlines()
            # Return last 20 lines
            return "".join(lines[-20:]) if lines else "No log entries"
        else:
            return "Log file not found"
    except Exception as e:
        return f"Error reading log: {e}"

def clear_flipper_log():
    """Clear Flipper log file"""
    try:
        if os.path.exists(FLIPPER_LOG_FILE):
            os.remove(FLIPPER_LOG_FILE)
        if os.path.exists(FLIPPER_EXPORT_FILE):
            os.remove(FLIPPER_EXPORT_FILE)
        return "Logs cleared"
    except Exception as e:
        return f"Error clearing logs: {e}"

class CECController:
    def __init__(self):
        self.running = False
        self.http_server = None
        self.uart_serial = None
    
    def start_uart_interface(self):
        """Start UART interface for Flipper Zero"""
        try:
            self.uart_serial = serial.Serial('/dev/ttyAMA0', 115200, timeout=1)
            uart_thread = threading.Thread(target=self.uart_loop)
            uart_thread.daemon = True
            uart_thread.start()
            logger.info("UART interface started on /dev/ttyAMA0")
        except Exception as e:
            logger.error(f"Failed to start UART: {e}")
    
    def uart_loop(self):
        """Handle UART communication with Flipper"""
        while self.running:
            try:
                if self.uart_serial.in_waiting > 0:
                    line = self.uart_serial.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"UART received: '{line}' (length: {len(line)})")
                        response = self.process_command(line)
                        self.uart_serial.write((response + '\n').encode('utf-8'))
                        logger.info(f"UART sent: {response}")
                    else:
                        logger.info("UART received empty line")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"UART error: {e}")
                time.sleep(1)
    
    def process_command(self, command_json):
        """Process CEC command and return response with Flipper logging"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            
            # Log command to Flipper log
            write_flipper_log(f"CMD: {cmd_type}")
            
            if cmd_type == 'POWER_ON':
                result = cec_control.power_on()
                success = "✅" if "successful" in result else "❌"
                write_flipper_log(f"POWER_ON: {success}")
                save_flipper_export()  # Update export after successful command
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'POWER_OFF':
                result = cec_control.power_off()
                success = "✅" if "successful" in result else "❌"
                write_flipper_log(f"POWER_OFF: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'SCAN':
                result = cec_control.scan_devices()
                write_flipper_log(f"SCAN: ✅")
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'STATUS':
                result = cec_control.get_power_status()
                write_flipper_log(f"STATUS: ✅")
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'DEVICE_INFO':
                result = cec_control.get_device_info()
                write_flipper_log(f"DEVICE_INFO: ✅")
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'VOLUME_UP':
                result = cec_control.send_core_command("VOLUME_UP")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"VOL_UP: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'VOLUME_DOWN':
                result = cec_control.send_core_command("VOLUME_DOWN")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"VOL_DOWN: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'MUTE':
                result = cec_control.send_core_command("MUTE")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"MUTE: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'HDMI_1':
                result = cec_control.switch_input("HDMI1")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"HDMI_1: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'HDMI_2':
                result = cec_control.switch_input("HDMI2")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"HDMI_2: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'HDMI_3':
                result = cec_control.switch_input("HDMI3")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"HDMI_3: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'HDMI_4':
                result = cec_control.switch_input("HDMI4")
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"HDMI_4: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'CORE_COMMAND':
                command_name = command.get('command_name', '')
                result = cec_control.send_core_command(command_name)
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"CORE_{command_name}: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'CUSTOM':
                cec_command = command.get('cec_command', '')
                result = cec_control.send_custom_command(cec_command)
                success = "✅" if "executed" in result else "❌"
                write_flipper_log(f"CUSTOM_{cec_command}: {success}")
                save_flipper_export()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'GET_FLIPPER_LOG':
                result = get_flipper_log()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'GET_FLIPPER_EXPORT':
                try:
                    with open(FLIPPER_EXPORT_FILE, "r") as f:
                        result = f.read()
                    return json.dumps({"status": "success", "result": result})
                except:
                    return json.dumps({"status": "success", "result": "No export file found"})
            elif cmd_type == 'CLEAR_FLIPPER_LOG':
                result = clear_flipper_log()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'GET_COMMAND_LOG':
                result = cec_control.get_command_log()
                return json.dumps(
