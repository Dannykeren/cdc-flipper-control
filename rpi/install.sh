#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - Graphics Ready"
echo "   Clean Field Deployment Solution"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

# Detect actual username
ACTUAL_USER=$(logname 2>/dev/null || echo "admin")
USER_HOME="/home/$ACTUAL_USER"

echo "🔄 Updating system for user: $ACTUAL_USER..."
apt update && apt upgrade -y

echo "📦 Installing required packages..."
apt install -y cec-utils python3-pip python3-venv git
apt install -y xorg feh imagemagick openbox xinit xserver-xorg-legacy

echo "🔧 Enabling UART for Flipper communication..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Remove conflicting settings
sed -i '/dtoverlay=miniuart-bt/d' "$CONFIG_FILE"
sed -i '/enable_uart/d' "$CONFIG_FILE"
sed -i '/dtoverlay=disable-bt/d' "$CONFIG_FILE"
sed -i '/dtparam=uart/d' "$CONFIG_FILE"

# Add UART settings
echo "enable_uart=1" >> "$CONFIG_FILE"
echo "dtoverlay=disable-bt" >> "$CONFIG_FILE"
echo "dtparam=uart=on" >> "$CONFIG_FILE"

echo "🖥️ Configuring HDMI output..."
# Remove existing HDMI settings
sed -i '/hdmi_force_hotplug/d' "$CONFIG_FILE"
sed -i '/hdmi_drive/d' "$CONFIG_FILE"
sed -i '/hdmi_group/d' "$CONFIG_FILE"
sed -i '/hdmi_mode/d' "$CONFIG_FILE"

# Add HDMI settings
echo "hdmi_force_hotplug=1" >> "$CONFIG_FILE"
echo "hdmi_drive=2" >> "$CONFIG_FILE"
echo "hdmi_group=2" >> "$CONFIG_FILE"
echo "hdmi_mode=82" >> "$CONFIG_FILE"

# Fix cmdline.txt
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_FILE" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

sed -i 's/console=serial0,115200 //' "$CMDLINE_FILE"
sed -i 's/console=ttyAMA0,115200 //' "$CMDLINE_FILE"
sed -i 's/8250.nr_uarts=0/8250.nr_uarts=1/' "$CMDLINE_FILE"

if ! grep -q "8250.nr_uarts" "$CMDLINE_FILE"; then
    sed -i 's/rootwait/rootwait 8250.nr_uarts=1/' "$CMDLINE_FILE"
fi

echo "🏗️ Setting up CEC application..."
INSTALL_DIR="/opt/cec-flipper"
mkdir -p $INSTALL_DIR

python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install pyserial

echo "📥 Downloading CEC application files..."
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/cec_control.py" > $INSTALL_DIR/cec_control.py; then
    echo "✅ Downloaded cec_control.py"
else
    echo "❌ Failed to download cec_control.py"
    exit 1
fi

echo "🎨 Creating professional graphics display system..."

# Create status images
echo "Creating status images..."

# Ready state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill green -geometry +0+450 -annotate 0 '✅ System Ready' \
  -pointsize 28 -geometry +0+500 -annotate 0 '📱 Use Flipper Zero for control' \
  "$USER_HOME/status_ready.png"

# Sending state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill yellow -geometry +0+450 -annotate 0 '⚡ Processing Command...' \
  -pointsize 28 -geometry +0+500 -annotate 0 '🔄 Please wait' \
  "$USER_HOME/status_sending.png"

# Success state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill green -geometry +0+450 -annotate 0 '✅ Command Successful' \
  -pointsize 28 -geometry +0+500 -annotate 0 '📊 Check Flipper for details' \
  "$USER_HOME/status_success.png"

# Error state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill red -geometry +0+450 -annotate 0 '❌ Command Failed' \
  -pointsize 28 -geometry +0+500 -annotate 0 '🔧 Check connections' \
  "$USER_HOME/status_error.png"

echo "✅ Status images created"

# Create display update script
cat > "$USER_HOME/update_display.py" << 'EOF'
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
            
            subprocess.run(['pkill', '-f', 'feh'], check=False)
            subprocess.Popen([
                'feh', '--fullscreen', '--hide-pointer', 
                image_map[status]
            ], env=env)
            
        except Exception as e:
            print(f"Display update failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        update_display(sys.argv[1])
    else:
        update_display('ready')
EOF

chmod +x "$USER_HOME/update_display.py"
chown $ACTUAL_USER:$ACTUAL_USER "$USER_HOME"/*.png "$USER_HOME/update_display.py"

# Create integrated main application
cat > $INSTALL_DIR/main.py << 'EOF'
#!/usr/bin/env python3
"""
CEC Flipper Control v3.0 - With Graphics Display Integration
Clean field-ready solution with instant visual feedback
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
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

def update_hdmi_display(status):
    """Update HDMI display status"""
    try:
        # Get the actual user home directory
        actual_user = os.environ.get('SUDO_USER', 'admin')
        user_home = f"/home/{actual_user}"
        script_path = f"{user_home}/update_display.py"
        
        if os.path.exists(script_path):
            subprocess.run([
                'python3', script_path, status
            ], check=False, capture_output=True)
    except Exception as e:
        logger.error(f"Failed to update display: {e}")

def execute_cec_command(command, vendor="Unknown", timeout=10):
    """Execute CEC command with display feedback"""
    try:
        logger.info(f"Executing CEC command: {command}")
        
        # Show sending status
        update_hdmi_display('sending')
        
        process = subprocess.Popen(
            ['cec-client', '-s', '-d', '1'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        stdout, stderr = process.communicate(input=command + '\n', timeout=timeout)
        
        if process.returncode == 0:
            update_hdmi_display('success')
            logger.info(f"✅ Command successful: {command}")
            return f"✅ Command executed: {command}"
        else:
            update_hdmi_display('error')
            logger.error(f"❌ Command failed: {command} - {stderr}")
            return f"❌ Command failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        process.kill()
        update_hdmi_display('error')
        return f"❌ Command timed out: {command}"
    except Exception as e:
        update_hdmi_display('error')
        return f"❌ Error executing command: {str(e)}"

class CECController:
    def __init__(self):
        self.running = False
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
        """Process CEC command with graphics feedback"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            vendor = "Unknown"
            
            if cmd_type == 'PING':
                return json.dumps({"status": "success", "result": "pong"})
            
            elif cmd_type == 'SCAN':
                result = execute_cec_command("scan", "System", timeout=15)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'STATUS':
                result = execute_cec_command("pow 0", "System", timeout=5)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'CUSTOM':
                cec_command = command.get('cec_command', '')
                if cec_command:
                    # Simple vendor detection
                    if "4F:" in cec_command:
                        vendor = "Samsung"
                    elif "0F:" in cec_command:
                        vendor = "Samsung DB Series"
                    elif "10:" in cec_command:
                        vendor = "Generic/Projector"
                    
                    result = execute_cec_command(cec_command, vendor)
                    return json.dumps({"status": "success", "result": result})
                else:
                    return json.dumps({"status": "error", "result": "No CEC command provided"})
            
            # Direct power commands
            elif cmd_type == 'POWER_ON':
                result = execute_cec_command("on 0", vendor)
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'POWER_OFF':
                result = execute_cec_command("standby 0", vendor)
                return json.dumps({"status": "success", "result": result})
            
            # HDMI input switching
            elif cmd_type == 'HDMI_1':
                result = execute_cec_command("tx 4F:82:10:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_2':
                result = execute_cec_command("tx 4F:82:20:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_3':
                result = execute_cec_command("tx 4F:82:30:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'HDMI_4':
                result = execute_cec_command("tx 4F:82:40:00", "Samsung")
                return json.dumps({"status": "success", "result": result})
            
            # Volume commands
            elif cmd_type == 'VOLUME_UP':
                result = execute_cec_command("volup", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'VOLUME_DOWN':
                result = execute_cec_command("voldown", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            elif cmd_type == 'MUTE':
                result = execute_cec_command("mute", "Generic")
                return json.dumps({"status": "success", "result": result})
            
            else:
                return json.dumps({"status": "error", "result": f"Unknown command: {cmd_type}"})
                
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "result": "Invalid JSON"})
        except Exception as e:
            logger.error(f"Command processing error: {str(e)}")
            return json.dumps({"status": "error", "result": str(e)})
    
    def run(self):
        """Main application loop"""
        self.running = True
        
        logger.info("🚀 CEC Controller v3.0 - Graphics Mode")
        
        # Initialize display to ready state
        update_hdmi_display('ready')
        
        # Start UART interface
        self.start_uart_interface()
        
        logger.info("CEC Controller running with graphics display")
        
        # Keep running
        while self.running:
            time.sleep(1)
    
    def stop(self):
        """Stop all interfaces"""
        self.running = False
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
EOF

chmod +x $INSTALL_DIR/main.py

echo "🔧 Creating CEC service..."
cat > /etc/systemd/system/cec-flipper.service << 'EOF'
[Unit]
Description=CEC Flipper Control - Graphics Mode
After=network.target

[Service]
Type=simple
ExecStart=/opt/cec-flipper/venv/bin/python /opt/cec-flipper/main.py
WorkingDirectory=/opt/cec-flipper
Restart=always
RestartSec=5
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

systemctl enable cec-flipper.service

echo "🖥️ Setting up graphics display auto-start..."

# Configure auto-login
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $ACTUAL_USER --noclear %I \$TERM
EOF

# Configure X11 permissions
cat > /etc/X11/Xwrapper.config << 'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF

# Create display startup script
cat > "$USER_HOME/start_display.sh" << 'EOF'
#!/bin/bash
export DISPLAY=:0
export HOME=HOME_PLACEHOLDER

# Start X11 in background
startx -- :0 vt1 &
sleep 15

# Disable screensaver
DISPLAY=:0 xset s off
DISPLAY=:0 xset s noblank  
DISPLAY=:0 xset -dpms

# Start with ready status
python3 HOME_PLACEHOLDER/update_display.py ready
EOF

# Replace placeholder with actual home
sed -i "s|HOME_PLACEHOLDER|$USER_HOME|g" "$USER_HOME/start_display.sh"
chmod +x "$USER_HOME/start_display.sh"

# Create auto-start on login
cat > "$USER_HOME/.bash_profile" << EOF
if [ -z "\$DISPLAY" ] && [ "\$(tty)" = "/dev/tty1" ]; then
    $USER_HOME/start_display.sh
fi
EOF

chown $ACTUAL_USER:$ACTUAL_USER "$USER_HOME/.bash_profile" "$USER_HOME/start_display.sh"

# Add user to required groups
usermod -a -G dialout,tty,video $ACTUAL_USER

systemctl set-default multi-user.target

echo ""
echo "✅ CLEAN GRAPHICS SETUP COMPLETE!"
echo ""
echo "🎯 FIELD-READY FEATURES:"
echo "   ✅ Professional graphics display with instant feedback"
echo "   ✅ 4 status states: Ready, Sending, Success, Error"  
echo "   ✅ Auto-start on boot (no manual intervention)"
echo "   ✅ Zero browser dependencies (native graphics)"
echo "   ✅ Bulletproof reliability for field deployment"
echo ""
echo "📱 OPERATION:"
echo "   🔌 Power on → Graphics display shows 'Ready'"
echo "   📱 Use Flipper → Display shows real-time status"
echo "   ✅ Instant visual feedback for every command"
echo "   🔧 No WiFi/SSH needed in field"
echo ""
echo "🔄 Reboot required to activate all features"
echo ""

read -p "Reboot now to activate graphics display? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting to graphics mode..."
  reboot
fi
