#!/usr/bin/env python3
"""
CEC Flipper Control v3.0 - With HDMI Display Integration
"""
import time
import logging
import sys
import signal
import json
import threading
import serial
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import urllib.parse
import socket

# Import HDMI display module
try:
    from hdmi_display import create_hdmi_display, serve_hdmi_display_http, auto_launch_hdmi_display
except ImportError:
    print("HDMI display module not found - display features disabled")
    def create_hdmi_display(state): return None
    def serve_hdmi_display_http(handler): pass
    def auto_launch_hdmi_display(ip): return "HDMI module not available"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Logging files
FLIPPER_LOG_FILE = "/tmp/flipper_cec_log.txt"

# Global state for HDMI display
display_state = {
    "device_info": {
        "vendor": "Unknown",
        "model": "Unknown",
        "power_status": "Unknown",
        "active_source": "Unknown",
        "cec_version": "1.4"
    },
    "last_command": {
        "vendor": "",
        "command": "",
        "status": "",
        "success": False,
        "timestamp": ""
    },
    "command_stats": {
        "total": 0,
        "successful": 0
    },
    "log_entries": []
}

def write_flipper_log(message):
    """Write log message to Flipper-accessible file"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(FLIPPER_LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
        
        # Also add to display state
        add_log_entry(message, "info")
    except Exception as e:
        logger.error(f"Failed to write Flipper log: {e}")

def add_log_entry(message, entry_type="info"):
    """Add entry to log and update display state"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Determine log type and icon
    if "✅" in message or "successful" in message.lower():
        entry_type = "success"
    elif "❌" in message or "failed" in message.lower():
        entry_type = "error"
    elif "ℹ️" in message or "trying" in message.lower():
        entry_type = "info"
    
    log_entry = {
        "timestamp": timestamp,
        "message": message,
        "type": entry_type
    }
    
    display_state["log_entries"].append(log_entry)
    
    # Keep only last 50 entries
    if len(display_state["log_entries"]) > 50:
        display_state["log_entries"] = display_state["log_entries"][-50:]

def get_flipper_log():
    """Get recent Flipper log entries"""
    try:
        if os.path.exists(FLIPPER_LOG_FILE):
            with open(FLIPPER_LOG_FILE, "r") as f:
                lines = f.readlines()
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
        
        # Clear display state
        display_state["log_entries"] = []
        display_state["command_stats"] = {"total": 0, "successful": 0}
        
        add_log_entry("🗑️ Logs cleared", "info")
        return "✅ Logs cleared"
    except Exception as e:
        return f"❌ Error clearing logs: {e}"

def execute_cec_command(command, vendor="Unknown", timeout=10):
    """Execute CEC command directly - simple and fast"""
    try:
        logger.info(f"Executing CEC command: {command}")
        
        # Update command stats
        display_state["command_stats"]["total"] += 1
        
        # Log command attempt
        add_log_entry(f"CMD: {command} ({vendor})", "info")
        
        process = subprocess.Popen(
            ['cec-client', '-s', '-d', '1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(input=command + '\n', timeout=timeout)
        
        if process.returncode == 0:
            display_state["command_stats"]["successful"] += 1
            success_msg = f"✅ {command} successful ({vendor})"
            add_log_entry(success_msg, "success")
            
            # Update last command
            display_state["last_command"] = {
                "vendor": vendor,
                "command": command,
                "status": "✅ Success",
                "success": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return f"✅ Command executed: {command}"
        else:
            error_msg = f"❌ {command} failed ({vendor}): {stderr}"
            add_log_entry(error_msg, "error")
            
            # Update last command
            display_state["last_command"] = {
                "vendor": vendor,
                "command": command,
                "status": f"❌ Failed: {stderr}",
                "success": False,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return f"❌ Command failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        timeout_msg = f"❌ {command} timed out ({vendor})"
        add_log_entry(timeout_msg, "error")
        return f"❌ Command timed out: {command}"
    except Exception as e:
        error_msg = f"❌ Error executing {command}: {str(e)}"
        add_log_entry(error_msg, "error")
        return f"❌ Error executing command: {str(e)}"

def scan_devices():
    """Simple device scanning - no auto-detection"""
    add_log_entry("🔍 Scanning for CEC devices...", "info")
    result = execute_cec_command("scan", "System", timeout=15)
    
    if "device #" in result:
        add_log_entry("✅ CEC scan completed - devices found", "success")
        return result
    else:
        add_log_entry("❌ CEC scan failed - no devices found", "error")
        return "❌ No devices found or scan failed"

def get_power_status():
    """Get power status - simple check"""
    add_log_entry("ℹ️ Checking power status...", "info")
    result = execute_cec_command("pow 0", "System", timeout=5)
    
    # Simple power status update
    if "on" in result.lower():
        display_state["device_info"]["power_status"] = "ON"
    elif "standby" in result.lower():
        display_state["device_info"]["power_status"] = "STANDBY"
    else:
        display_state["device_info"]["power_status"] = "Unknown"
    
    return result

def get_ip_address():
    """Get Pi IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

class CECHandler(BaseHTTPRequestHandler):
    """HTTP handler with HDMI display serving"""
    
    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            
            # Serve the HDMI display directly
            if self.path == '/display' or self.path == '/hdmi':
                serve_hdmi_display_http(self)
                return
            
            # Handle API commands
            query = urllib.parse.parse_qs(parsed_path.query)
            command = query.get('cmd', [''])[0].upper()
            
            response = {"status": "error", "message": "Unknown command"}
            
            if command == "PING":
                response = {"status": "success", "result": "pong"}
            elif command == "SCAN":
                result = scan_devices()
                response = {"status": "success", "result": result}
            elif command == "POWER_ON":
                result = execute_cec_command("on 0", "System")
                response = {"status": "success", "result": result}
            elif command == "POWER_OFF":
                result = execute_cec_command("standby 0", "System")
                response = {"status": "success", "result": result}
            elif command == "STATUS":
                result = get_power_status()
                response = {"status": "success", "result": result}
            elif command == "GET_FLIPPER_LOG":
                result = get_flipper_log()
                response = {"status": "success", "result": result}
            elif command == "CLEAR_FLIPPER_LOG":
                result = clear_flipper_log()
                response = {"status": "success", "result": result}
            elif command == "DISPLAY_HDMI":
                ip = get_ip_address()
                result = auto_launch_hdmi_display(ip)
                response = {"status": "success", "result": result}
            
            # Always update HDMI display after command
            create_hdmi_display(display_state)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode())

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
                if self.uart_serial and self.uart_serial.in_waiting > 0:
                    line = self.uart_serial.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"UART received: '{line}'")
                        response = self.process_command(line)
                        if self.uart_serial:
                            self.uart_serial.write((response + '\n').encode('utf-8'))
                            logger.info(f"UART sent: {response}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"UART error: {e}")
                time.sleep(1)
    
    def process_command(self, command_json):
        """Process CEC command - simple and direct execution"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            vendor = "Unknown"
            
            if cmd_type == 'PING':
                return json.dumps({"status": "success", "result": "pong"})
            
            elif cmd_type == 'SCAN':
                result = scan_devices()
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'STATUS':
                result = get_power_status()
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'GET_FLIPPER_LOG':
                result = get_flipper_log()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CLEAR_FLIPPER_LOG':
                result = clear_flipper_log()
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'DISPLAY_LOGS_ON_HDMI':
                ip = get_ip_address()
                result = auto_launch_hdmi_display(ip)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CUSTOM':
                # Direct CEC command execution - no auto-detection
                cec_command = command.get('cec_command', '')
                if cec_command:
                    # Simple vendor detection from command pattern
                    if "4F:" in cec_command:
                        vendor = "Samsung"
                    elif "0F:" in cec_command:
                        vendor = "Samsung DB Series"
                    elif "10:" in cec_command:
                        vendor = "Generic/Projector"
                    
                    result = execute_cec_command(cec_command, vendor)
                    create_hdmi_display(display_state)
                    return json.dumps({"status": "success", "result": result})
                else:
                    return json.dumps({"status": "error", "result": "No CEC command provided"})
            
            # Handle direct commands - simple execution
            elif cmd_type == 'POWER_ON':
                result = execute_cec_command("on 0", vendor)
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'POWER_OFF':
                result = execute_cec_command("standby 0", vendor)
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            # HDMI input switching - direct commands
            elif cmd_type == 'HDMI_1':
                result = execute_cec_command("tx 4F:82:10:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 1"
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_2':
                result = execute_cec_command("tx 4F:82:20:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 2"
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_3':
                result = execute_cec_command("tx 4F:82:30:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 3"
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_4':
                result = execute_cec_command("tx 4F:82:40:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 4"
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            # Volume commands - direct execution, no auto-testing
            elif cmd_type == 'VOLUME_UP':
                result = execute_cec_command("volup", "Generic")
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'VOLUME_DOWN':
                result = execute_cec_command("voldown", "Generic")
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'MUTE':
                result = execute_cec_command("mute", "Generic")
                create_hdmi_display(display_state)
                return json.dumps({"status": "success", "result": result})
            
            else:
                return json.dumps({"status": "error", "result": f"Unknown command: {cmd_type}"})
                
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "result": "Invalid JSON"})
        except Exception as e:
            add_log_entry(f"❌ ERROR: {str(e)}", "error")
            return json.dumps({"status": "error", "result": str(e)})
    
    def start_http_server(self):
        """Start HTTP server with HDMI display serving"""
        ip_address = get_ip_address()
        self.http_server = HTTPServer(('0.0.0.0', 8080), CECHandler)
        
        http_thread = threading.Thread(target=self.http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        
        logger.info(f"HTTP server running on http://{ip_address}:8080")
        print(f"🖥️  HDMI Display: http://{ip_address}:8080/display")
        print(f"📺 Test commands: curl 'http://{ip_address}:8080?cmd=PING'")
    
    def run(self):
        """Main application loop"""
        self.running = True
        
        # Initialize display state - simple, no auto-detection
        display_state["device_info"]["vendor"] = "Unknown"
        display_state["device_info"]["model"] = "Unknown"
        add_log_entry("🚀 CEC Test Tool v3.0 started - Simple & Fast", "info")
        add_log_entry("📺 HDMI display available", "info")
        add_log_entry("⚡ No auto-detection - commands execute directly", "info")
        
        # Create initial HDMI display
        create_hdmi_display(display_state)
        
        # Start all interfaces
        self.start_http_server()
        self.start_uart_interface()
        
        logger.info("CEC Controller v3.0 running - Simple & Fast Mode")
        
        # Keep running and update display periodically
        while self.running:
            time.sleep(5)
            # Update display every 5 seconds
            create_hdmi_display(display_state)
    
    def stop(self):
        """Stop all interfaces"""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
        if self.uart_serial:
            try:
                self.uart_serial.close()
            except:
                pass
        logger.info("CEC Controller stopped")

def signal_handler(sig, frame):
    global controller
    logger.info("Shutting down...")
    if 'controller' in globals():
        controller.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    controller = CECController()
    
    try:
        controller.run()
    except KeyboardInterrupt:
        pass
    finally:
        controller.stop()
