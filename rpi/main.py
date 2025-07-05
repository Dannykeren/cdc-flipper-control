#!/usr/bin/env python3
"""
CEC Flipper Control v3.0 - HDMI Display + Fixed Samsung Commands
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
import webbrowser
import tempfile

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

# Logging files
FLIPPER_LOG_FILE = "/tmp/flipper_cec_log.txt"
HDMI_DISPLAY_FILE = "/tmp/cec_display.html"

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

def create_hdmi_display():
    """Create/update the HDMI display HTML file"""
    try:
        # Calculate success rate
        total = display_state["command_stats"]["total"]
        successful = display_state["command_stats"]["successful"]
        success_rate = f"{int((successful/total)*100)}%" if total > 0 else "0%"
        
        # Get recent log entries (last 10)
        recent_logs = display_state["log_entries"][-10:] if display_state["log_entries"] else []
        
        # Generate log HTML
        log_html = ""
        for entry in recent_logs:
            log_html += f'''
            <div class="log-entry {entry['type']}">
                <span class="log-time">{entry['timestamp']}</span>
                <span class="log-message">{entry['message']}</span>
            </div>'''
        
        if not log_html:
            log_html = '<div class="log-entry info"><span class="log-time">--:--:--</span><span class="log-message">No log entries yet</span></div>'
        
        # Create complete HTML
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CEC Test Tool</title>
    <meta http-equiv="refresh" content="3">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; height: 100vh; overflow: hidden; display: flex; flex-direction: column;
        }}
        .header {{
            background: rgba(0, 0, 0, 0.3); padding: 20px 40px; display: flex;
            align-items: center; justify-content: space-between;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }}
        .logo-section {{ display: flex; align-items: center; gap: 20px; }}
        .logo {{
            width: 80px; height: 80px; background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            border-radius: 20px; display: flex; align-items: center; justify-content: center;
            font-size: 36px; font-weight: bold; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .title-section h1 {{ font-size: 48px; font-weight: 300; margin-bottom: 5px; text-shadow: 0 2px 4px rgba(0,0,0,0.3); }}
        .title-section p {{ font-size: 18px; opacity: 0.8; font-weight: 300; }}
        .status-indicator {{ display: flex; align-items: center; gap: 10px; font-size: 18px; }}
        .status-dot {{
            width: 16px; height: 16px; border-radius: 50%; background: #4ecdc4;
            box-shadow: 0 0 20px rgba(78, 205, 196, 0.5); animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 20px rgba(78, 205, 196, 0.5); }}
            50% {{ box-shadow: 0 0 30px rgba(78, 205, 196, 0.8); }}
            100% {{ box-shadow: 0 0 20px rgba(78, 205, 196, 0.5); }}
        }}
        .main-content {{
            flex: 1; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;
            gap: 20px; padding: 20px; height: calc(100vh - 140px);
        }}
        .panel {{
            background: rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 30px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); display: flex; flex-direction: column;
        }}
        .panel h2 {{ font-size: 28px; margin-bottom: 20px; color: #4ecdc4; display: flex; align-items: center; gap: 15px; }}
        .panel-icon {{ font-size: 32px; }}
        .cec-info {{ grid-column: 1; grid-row: 1; }}
        .last-command {{ grid-column: 2; grid-row: 1; }}
        .log-panel {{ grid-column: 1 / -1; grid-row: 2; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; flex: 1; }}
        .info-item {{
            background: rgba(0, 0, 0, 0.2); padding: 20px; border-radius: 12px;
            border-left: 4px solid #4ecdc4;
        }}
        .info-label {{ font-size: 14px; opacity: 0.7; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }}
        .info-value {{ font-size: 20px; font-weight: 600; color: #4ecdc4; }}
        .command-display {{
            background: rgba(0, 0, 0, 0.3); padding: 25px; border-radius: 15px;
            border: 2px solid #4ecdc4; margin-bottom: 20px; text-align: center;
        }}
        .command-vendor {{ font-size: 16px; opacity: 0.8; margin-bottom: 10px; }}
        .command-text {{
            font-size: 24px; font-weight: bold; color: #4ecdc4;
            font-family: 'Courier New', monospace; margin-bottom: 10px;
        }}
        .command-time {{ font-size: 14px; opacity: 0.6; }}
        .command-status {{
            display: flex; align-items: center; justify-content: center; gap: 10px;
            margin-top: 15px; font-size: 18px;
        }}
        .status-success {{ color: #4ecdc4; }}
        .status-error {{ color: #ff6b6b; }}
        .log-container {{
            flex: 1; background: rgba(0, 0, 0, 0.4); border-radius: 12px; padding: 20px;
            overflow-y: auto; font-family: 'Courier New', monospace; line-height: 1.6;
        }}
        .log-entry {{ margin-bottom: 12px; padding: 10px; border-radius: 8px; border-left: 3px solid transparent; }}
        .log-entry.success {{ background: rgba(78, 205, 196, 0.1); border-left-color: #4ecdc4; }}
        .log-entry.error {{ background: rgba(255, 107, 107, 0.1); border-left-color: #ff6b6b; }}
        .log-entry.info {{ background: rgba(255, 255, 255, 0.05); border-left-color: rgba(255, 255, 255, 0.3); }}
        .log-time {{ color: #4ecdc4; font-size: 12px; margin-right: 10px; }}
        .log-message {{ font-size: 14px; }}
        .connection-status {{
            background: rgba(78, 205, 196, 0.2); padding: 15px; border-radius: 10px;
            margin-bottom: 20px; text-align: center; border: 1px solid #4ecdc4;
        }}
        .footer {{ text-align: center; padding: 10px; font-size: 12px; opacity: 0.5; background: rgba(0, 0, 0, 0.2); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-section">
            <div class="logo">CEC</div>
            <div class="title-section">
                <h1>CEC Test Tool</h1>
                <p>Professional HDMI-CEC Testing & Control</p>
            </div>
        </div>
        <div class="status-indicator">
            <div class="status-dot"></div>
            <span>Connected & Ready</span>
        </div>
    </div>
    
    <div class="main-content">
        <div class="panel cec-info">
            <h2><span class="panel-icon">📡</span>CEC Device Info</h2>
            <div class="connection-status">
                <strong>{display_state["device_info"]["vendor"]} {display_state["device_info"]["model"]} Connected</strong><br>
                Physical Address: 1.0.0.0
            </div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Vendor</div>
                    <div class="info-value">{display_state["device_info"]["vendor"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Model</div>
                    <div class="info-value">{display_state["device_info"]["model"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Power Status</div>
                    <div class="info-value">{display_state["device_info"]["power_status"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Active Source</div>
                    <div class="info-value">{display_state["device_info"]["active_source"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">CEC Version</div>
                    <div class="info-value">{display_state["device_info"]["cec_version"]}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Commands Tested</div>
                    <div class="info-value">{total}</div>
                </div>
            </div>
        </div>
        
        <div class="panel last-command">
            <h2><span class="panel-icon">⚡</span>Last Command</h2>
            <div class="command-display">
                <div class="command-vendor">{display_state["last_command"]["vendor"]}</div>
                <div class="command-text">{display_state["last_command"]["command"]}</div>
                <div class="command-time">{display_state["last_command"]["timestamp"]}</div>
                <div class="command-status">
                    <span class="{'status-success' if display_state["last_command"]["success"] else 'status-error'}">{display_state["last_command"]["status"]}</span>
                </div>
            </div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Success Rate</div>
                    <div class="info-value">{success_rate}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Total Commands</div>
                    <div class="info-value">{total}</div>
                </div>
            </div>
        </div>
        
        <div class="panel log-panel">
            <h2><span class="panel-icon">📝</span>Command Log</h2>
            <div class="log-container">
                {log_html}
            </div>
        </div>
    </div>
    
    <div class="footer">
        CEC Test Tool v3.0 | Flipper Zero + Raspberry Pi | Last Updated: {datetime.now().strftime("%H:%M:%S")}
    </div>
</body>
</html>'''
        
        # Write to file
        with open(HDMI_DISPLAY_FILE, "w") as f:
            f.write(html_content)
        
        logger.info(f"HDMI display updated: {HDMI_DISPLAY_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create HDMI display: {e}")
        return False

def display_on_hdmi():
    """Display the CEC tool interface on HDMI using browser"""
    try:
        # Create/update the display
        if create_hdmi_display():
            # Try to open in browser (if display is available)
            try:
                # For Raspberry Pi with desktop environment
                subprocess.run(['chromium-browser', '--kiosk', '--disable-infobars', f'file://{HDMI_DISPLAY_FILE}'], 
                             timeout=5, capture_output=True)
            except:
                try:
                    # Alternative browser
                    subprocess.run(['firefox', f'file://{HDMI_DISPLAY_FILE}'], 
                                 timeout=5, capture_output=True)
                except:
                    # If no GUI browser available, at least log the file location
                    add_log_entry(f"📺 HDMI display created: {HDMI_DISPLAY_FILE}", "info")
                    add_log_entry("💡 Open this file in a browser on HDMI display", "info")
            
            return f"✅ HDMI display activated: {HDMI_DISPLAY_FILE}"
        else:
            return "❌ Failed to create HDMI display"
    except Exception as e:
        return f"❌ Error displaying on HDMI: {e}"

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
                result = display_on_hdmi()
                response = {"status": "success", "result": result}
            
            # Always update HDMI display after command
            create_hdmi_display()
            
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
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'STATUS':
                result = get_power_status()
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'GET_FLIPPER_LOG':
                result = get_flipper_log()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CLEAR_FLIPPER_LOG':
                result = clear_flipper_log()
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'DISPLAY_LOGS_ON_HDMI':
                result = display_on_hdmi()
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
                    create_hdmi_display()
                    return json.dumps({"status": "success", "result": result})
                else:
                    return json.dumps({"status": "error", "result": "No CEC command provided"})
            
            # Handle direct commands - simple execution
            elif cmd_type == 'POWER_ON':
                result = execute_cec_command("on 0", vendor)
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'POWER_OFF':
                result = execute_cec_command("standby 0", vendor)
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            # HDMI input switching - direct commands
            elif cmd_type == 'HDMI_1':
                result = execute_cec_command("tx 4F:82:10:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 1"
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_2':
                result = execute_cec_command("tx 4F:82:20:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 2"
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_3':
                result = execute_cec_command("tx 4F:82:30:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 3"
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_4':
                result = execute_cec_command("tx 4F:82:40:00", "Samsung")
                display_state["device_info"]["active_source"] = "HDMI 4"
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            # Volume commands - direct execution, no auto-testing
            elif cmd_type == 'VOLUME_UP':
                result = execute_cec_command("volup", "Generic")
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'VOLUME_DOWN':
                result = execute_cec_command("voldown", "Generic")
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'MUTE':
                result = execute_cec_command("mute", "Generic")
                create_hdmi_display()
                return json.dumps({"status": "success", "result": result})
            
            else:
                return json.dumps({"status": "error", "result": f"Unknown command: {cmd_type}"})
                
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "result": "Invalid JSON"})
        except Exception as e:
            add_log_entry(f"❌ ERROR: {str(e)}", "error")
            return json.dumps({"status": "error", "result": str(e)})
    
    def start_http_server(self):
        """Start HTTP server for testing"""
        ip_address = get_ip_address()
        self.http_server = HTTPServer(('0.0.0.0', 8080), CECHandler)
        
        http_thread = threading.Thread(target=self.http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        
        logger.info(f"HTTP server running on http://{ip_address}:8080")
        print(f"HDMI Display URL: http://{ip_address}:8080?cmd=DISPLAY_HDMI")
        print(f"Test commands: curl 'http://{ip_address}:8080?cmd=PING'")
    
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
        create_hdmi_display()
        
        # Start all interfaces
        self.start_http_server()
        self.start_uart_interface()
        
        logger.info("CEC Controller v3.0 running - Simple & Fast Mode")
        
        # Keep running and update display periodically
        while self.running:
            time.sleep(5)
            # Update display every 5 seconds
            create_hdmi_display()
    
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
