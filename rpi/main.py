#!/usr/bin/env python3
"""
CEC Flipper Control v2.0 - Fast & Simple Backend
No auto-detection, direct CEC commands, much faster
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Simple logging to files
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
        return "✅ Logs cleared"
    except Exception as e:
        return f"❌ Error clearing logs: {e}"

def execute_cec_command(command, timeout=10):
    """Execute CEC command directly - no auto-detection"""
    try:
        logger.info(f"Executing CEC command: {command}")
        write_flipper_log(f"CMD: {command}")
        
        process = subprocess.Popen(
            ['cec-client', '-s', '-d', '1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(input=command + '\n', timeout=timeout)
        
        if process.returncode == 0:
            write_flipper_log(f"✅ Success: {command}")
            return f"✅ Command executed: {command}"
        else:
            write_flipper_log(f"❌ Failed: {command}")
            return f"❌ Command failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        write_flipper_log(f"❌ Timeout: {command}")
        return f"❌ Command timed out: {command}"
    except Exception as e:
        write_flipper_log(f"❌ Error: {str(e)}")
        return f"❌ Error executing command: {str(e)}"

def scan_devices():
    """Simple device scanning"""
    write_flipper_log("CMD: SCAN")
    result = execute_cec_command("scan", timeout=15)
    
    # Extract useful info from scan
    if "device #" in result:
        write_flipper_log("✅ Scan completed")
        return result
    else:
        write_flipper_log("❌ Scan failed")
        return "❌ No devices found or scan failed"

def get_power_status():
    """Get power status"""
    write_flipper_log("CMD: STATUS")
    result = execute_cec_command("pow 0", timeout=5)
    write_flipper_log("✅ Status checked")
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
    """HTTP handler for testing"""
    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            
            command = query.get('cmd', [''])[0].upper()
            
            response = {"status": "error", "message": "Unknown command"}
            
            if command == "PING":
                response = {"status": "success", "result": "pong"}
            elif command == "SCAN":
                result = scan_devices()
                response = {"status": "success", "result": result}
            elif command == "POWER_ON":
                result = execute_cec_command("on 0")
                response = {"status": "success", "result": result}
            elif command == "POWER_OFF":
                result = execute_cec_command("standby 0")
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
        """Process CEC command - fast and simple"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            
            if cmd_type == 'PING':
                return json.dumps({"status": "success", "result": "pong"})
            
            elif cmd_type == 'SCAN':
                result = scan_devices()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'STATUS':
                result = get_power_status()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'GET_FLIPPER_LOG':
                result = get_flipper_log()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CLEAR_FLIPPER_LOG':
                result = clear_flipper_log()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CUSTOM':
                # Direct CEC command execution
                cec_command = command.get('cec_command', '')
                if cec_command:
                    result = execute_cec_command(cec_command)
                    return json.dumps({"status": "success", "result": result})
                else:
                    return json.dumps({"status": "error", "result": "No CEC command provided"})
            
            # Handle direct power commands
            elif cmd_type == 'POWER_ON':
                result = execute_cec_command("on 0")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'POWER_OFF':
                result = execute_cec_command("standby 0")
                return json.dumps({"status": "success", "result": result})
            
            # Handle direct input switching
            elif cmd_type == 'HDMI_1':
                result = execute_cec_command("tx 4F:82:10:00")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_2':
                result = execute_cec_command("tx 4F:82:20:00")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_3':
                result = execute_cec_command("tx 4F:82:30:00")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_4':
                result = execute_cec_command("tx 4F:82:40:00")
                return json.dumps({"status": "success", "result": result})
            
            # Handle volume commands
            elif cmd_type == 'VOLUME_UP':
                result = execute_cec_command("volup")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'VOLUME_DOWN':
                result = execute_cec_command("voldown")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'MUTE':
                result = execute_cec_command("mute")
                return json.dumps({"status": "success", "result": result})
            
            else:
                return json.dumps({"status": "error", "result": f"Unknown command: {cmd_type}"})
                
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "result": "Invalid JSON"})
        except Exception as e:
            write_flipper_log(f"ERROR: {str(e)}")
            return json.dumps({"status": "error", "result": str(e)})
    
    def start_http_server(self):
        """Start HTTP server for testing"""
        ip_address = get_ip_address()
        self.http_server = HTTPServer(('0.0.0.0', 8080), CECHandler)
        
        http_thread = threading.Thread(target=self.http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        
        logger.info(f"HTTP server running on http://{ip_address}:8080")
        print(f"Test with: curl 'http://{ip_address}:8080?cmd=PING'")
    
    def run(self):
        """Main application loop"""
        self.running = True
        
        # Start all interfaces
        self.start_http_server()
        self.start_uart_interface()
        
        logger.info("CEC Controller v2.0 running - Fast & Simple")
        
        # Keep running
        while self.running:
            time.sleep(1)
    
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
