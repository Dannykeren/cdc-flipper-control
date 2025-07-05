#!/usr/bin/env python3
"""
HDMI Display Module for CEC Test Tool
Creates professional full-screen interface for HDMI output
"""
import os
import json
from datetime import datetime

# File paths
HDMI_TEMPLATE_FILE = "/opt/cec-flipper/hdmi_display_template.html"
HDMI_OUTPUT_FILE = "/tmp/cec_display.html"

def create_hdmi_display(display_state):
    """
    Create HDMI display HTML from template and current state
    
    Args:
        display_state: Dictionary containing device info, logs, etc.
    
    Returns:
        str: Path to created HTML file
    """
    try:
        # Read template
        if not os.path.exists(HDMI_TEMPLATE_FILE):
            raise FileNotFoundError(f"Template not found: {HDMI_TEMPLATE_FILE}")
        
        with open(HDMI_TEMPLATE_FILE, 'r') as f:
            template = f.read()
        
        # Calculate success rate
        total = display_state.get("command_stats", {}).get("total", 0)
        successful = display_state.get("command_stats", {}).get("successful", 0)
        success_rate = f"{int((successful/total)*100)}%" if total > 0 else "0%"
        
        # Get recent log entries (last 10)
        recent_logs = display_state.get("log_entries", [])[-10:]
        
        # Generate log HTML
        log_html = ""
        for entry in recent_logs:
            log_html += f'''
            <div class="log-entry {entry.get('type', 'info')}">
                <span class="log-time">{entry.get('timestamp', '--:--:--')}</span>
                <span class="log-message">{entry.get('message', '')}</span>
            </div>'''
        
        if not log_html:
            log_html = '''
            <div class="log-entry info">
                <span class="log-time">--:--:--</span>
                <span class="log-message">No log entries yet</span>
            </div>'''
        
        # Get device info
        device_info = display_state.get("device_info", {})
        last_command = display_state.get("last_command", {})
        
        # Determine status class for last command
        status_class = "status-success" if last_command.get("success", False) else "status-error"
        
        # Replace template variables
        replacements = {
            "{{DEVICE_VENDOR}}": device_info.get("vendor", "Unknown"),
            "{{DEVICE_MODEL}}": device_info.get("model", "Unknown"),
            "{{POWER_STATUS}}": device_info.get("power_status", "Unknown"),
            "{{ACTIVE_SOURCE}}": device_info.get("active_source", "Unknown"),
            "{{CEC_VERSION}}": device_info.get("cec_version", "1.4"),
            "{{TOTAL_COMMANDS}}": str(total),
            "{{LAST_VENDOR}}": last_command.get("vendor", ""),
            "{{LAST_COMMAND}}": last_command.get("command", "No commands yet"),
            "{{LAST_TIME}}": last_command.get("timestamp", ""),
            "{{LAST_STATUS}}": last_command.get("status", "Ready"),
            "{{LAST_STATUS_CLASS}}": status_class,
            "{{SUCCESS_RATE}}": success_rate,
            "{{LOG_ENTRIES}}": log_html,
            "{{TIMESTAMP}}": datetime.now().strftime("%H:%M:%S")
        }
        
        # Apply replacements
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, str(value))
        
        # Write output file
        with open(HDMI_OUTPUT_FILE, 'w') as f:
            f.write(template)
        
        return HDMI_OUTPUT_FILE
        
    except Exception as e:
        print(f"Error creating HDMI display: {e}")
        # Create minimal fallback display
        fallback_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>CEC Test Tool</title></head>
        <body style="font-family: Arial; padding: 50px; background: #1e3c72; color: white;">
            <h1>CEC Test Tool</h1>
            <p>Error creating display: {e}</p>
            <p>Last updated: {datetime.now().strftime("%H:%M:%S")}</p>
        </body>
        </html>
        """
        
        with open(HDMI_OUTPUT_FILE, 'w') as f:
            f.write(fallback_html)
        
        return HDMI_OUTPUT_FILE

def serve_hdmi_display_http(handler_self):
    """
    Serve HDMI display via HTTP handler
    
    Args:
        handler_self: HTTP handler instance
    """
    try:
        if os.path.exists(HDMI_OUTPUT_FILE):
            with open(HDMI_OUTPUT_FILE, 'r') as f:
                html_content = f.read()
            
            handler_self.send_response(200)
            handler_self.send_header('Content-type', 'text/html')
            handler_self.send_header('Access-Control-Allow-Origin', '*')
            handler_self.end_headers()
            handler_self.wfile.write(html_content.encode())
        else:
            handler_self.send_response(404)
            handler_self.send_header('Content-type', 'text/html')
            handler_self.end_headers()
            error_html = """
            <html><body style="font-family: Arial; padding: 50px; background: #1e3c72; color: white;">
                <h1>CEC Test Tool</h1>
                <p>HDMI Display Not Ready</p>
                <p>Please run a CEC command first to initialize the display.</p>
            </body></html>
            """
            handler_self.wfile.write(error_html.encode())
            
    except Exception as e:
        handler_self.send_response(500)
        handler_self.send_header('Content-type', 'text/html')
        handler_self.end_headers()
        error_html = f"""
        <html><body style="font-family: Arial; padding: 50px; background: #1e3c72; color: white;">
            <h1>Error</h1>
            <p>{str(e)}</p>
        </body></html>
        """
        handler_self.wfile.write(error_html.encode())

def auto_launch_hdmi_display(pi_ip):
    """
    Attempt to auto-launch HDMI display in browser
    
    Args:
        pi_ip: Raspberry Pi IP address
    
    Returns:
        str: Status message
    """
    import subprocess
    
    display_url = f"http://{pi_ip}:8080/display"
    
    try:
        # Try Chromium in kiosk mode
        subprocess.run([
            'chromium-browser', 
            '--kiosk', 
            '--disable-infobars', 
            '--disable-session-crashed-bubble',
            display_url
        ], timeout=5, capture_output=True)
        
        return f"✅ HDMI display launched: {display_url}"
        
    except:
        try:
            # Try Firefox
            subprocess.run(['firefox', display_url], timeout=5, capture_output=True)
            return f"✅ HDMI display launched: {display_url}"
            
        except:
            try:
                # Try Midori (lightweight)
                subprocess.run(['midori', '-e', 'Fullscreen', '-a', display_url], 
                             timeout=5, capture_output=True)
                return f"✅ HDMI display launched: {display_url}"
                
            except:
                return f"💡 HDMI display ready at: {display_url}\n(Open in browser manually)"

def setup_hdmi_autostart():
    """
    Create autostart file for HDMI display on boot
    
    Returns:
        str: Status message
    """
    try:
        autostart_dir = "/home/pi/.config/autostart"
        os.makedirs(autostart_dir, exist_ok=True)
        
        autostart_content = """[Desktop Entry]
Type=Application
Name=CEC HDMI Display
Exec=chromium-browser --kiosk --disable-infobars http://localhost:8080/display
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
        
        autostart_file = f"{autostart_dir}/cec-hdmi-display.desktop"
        with open(autostart_file, 'w') as f:
            f.write(autostart_content)
        
        os.chmod(autostart_file, 0o755)
        
        return f"✅ Auto-start configured: {autostart_file}"
        
    except Exception as e:
        return f"❌ Failed to setup auto-start: {e}"
