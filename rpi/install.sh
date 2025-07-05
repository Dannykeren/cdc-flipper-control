#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - Complete Setup"
echo "   Fresh Raspberry Pi Zero W"
echo "   + HDMI Professional Display"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

echo "🔄 Updating system..."
apt update && apt upgrade -y

echo "📦 Installing required packages..."
apt install -y cec-utils python3-pip python3-venv git

# Check if we're on Pi OS Lite (no GUI)
if ! dpkg -l | grep -q "raspberrypi-ui-mods"; then
    echo "🖥️ Installing desktop environment for HDMI display..."
    apt install -y raspberrypi-ui-mods chromium-browser
else
    echo "🖥️ Desktop environment detected, installing browser..."
    apt install -y chromium-browser
fi

echo "🔧 Enabling UART for Flipper communication..."
# Remove conflicting overlay first (check both config locations)
sed -i '/dtoverlay=miniuart-bt/d' /boot/config.txt 2>/dev/null || true
sed -i '/dtoverlay=miniuart-bt/d' /boot/firmware/config.txt 2>/dev/null || true

# Enable UART in the correct config file location
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Add UART settings to correct config file
if ! grep -q "enable_uart=1" "$CONFIG_FILE"; then
    echo "enable_uart=1" >> "$CONFIG_FILE"
fi
if ! grep -q "dtoverlay=disable-bt" "$CONFIG_FILE"; then
    echo "dtoverlay=disable-bt" >> "$CONFIG_FILE"
fi
if ! grep -q "dtparam=uart=on" "$CONFIG_FILE"; then
    echo "dtparam=uart=on" >> "$CONFIG_FILE"
fi

echo "🖥️ Configuring HDMI output for professional display..."
# Add HDMI settings for reliable output
if ! grep -q "hdmi_force_hotplug=1" "$CONFIG_FILE"; then
    echo "hdmi_force_hotplug=1" >> "$CONFIG_FILE"
fi
if ! grep -q "hdmi_drive=2" "$CONFIG_FILE"; then
    echo "hdmi_drive=2" >> "$CONFIG_FILE"
fi
# Set common resolution for professional displays
if ! grep -q "hdmi_group=2" "$CONFIG_FILE"; then
    echo "hdmi_group=2" >> "$CONFIG_FILE"
fi
if ! grep -q "hdmi_mode=82" "$CONFIG_FILE"; then
    echo "hdmi_mode=82" >> "$CONFIG_FILE"  # 1920x1080 60Hz
fi

# Fix cmdline.txt in correct location
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if [ ! -f "$CMDLINE_FILE" ]; then
    CMDLINE_FILE="/boot/cmdline.txt"
fi

# Remove console from UART and fix nr_uarts
sed -i 's/console=serial0,115200 //' "$CMDLINE_FILE"
sed -i 's/console=ttyAMA0,115200 //' "$CMDLINE_FILE"
sed -i 's/8250.nr_uarts=0/8250.nr_uarts=1/' "$CMDLINE_FILE"
# Add nr_uarts=1 if not present
if ! grep -q "8250.nr_uarts" "$CMDLINE_FILE"; then
    sed -i 's/rootwait/rootwait 8250.nr_uarts=1/' "$CMDLINE_FILE"
fi

echo "🏗️ Setting up application..."
INSTALL_DIR="/opt/cec-flipper"
mkdir -p $INSTALL_DIR

python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install pyserial

echo "📥 Downloading application files..."

# Download main application files
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/cec_control.py" > $INSTALL_DIR/cec_control.py; then
    echo "✅ Downloaded cec_control.py"
else
    echo "❌ Failed to download cec_control.py"
    exit 1
fi

if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/main.py" > $INSTALL_DIR/main.py; then
    echo "✅ Downloaded main.py"
else
    echo "❌ Failed to download main.py"
    exit 1
fi

chmod +x $INSTALL_DIR/main.py

# Download HDMI display files
echo "📺 Setting up HDMI professional display..."

if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/hdmi_display_template.html" > $INSTALL_DIR/hdmi_display_template.html; then
    echo "✅ Downloaded HDMI display template"
else
    echo "❌ Failed to download HDMI display template"
    exit 1
fi

if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/hdmi_display.py" > $INSTALL_DIR/hdmi_display.py; then
    echo "✅ Downloaded HDMI display module"
else
    echo "❌ Failed to download HDMI display module"
    exit 1
fi

# Download HTTP test server
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/http_test.py" > $INSTALL_DIR/http_test.py; then
    echo "✅ Downloaded http_test.py"
else
    echo "❌ Failed to download http_test.py"
    exit 1
fi

chmod +x $INSTALL_DIR/http_test.py

echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/cec-flipper.service << EOFINNER
[Unit]
Description=CEC Flipper Control
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
WorkingDirectory=$INSTALL_DIR
Restart=always
RestartSec=5
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOFINNER

systemctl enable cec-flipper.service

echo "🖥️ Setting up HDMI display auto-launch..."

# Enable desktop environment for HDMI display
systemctl set-default graphical.target

# Check if desktop packages are installed
if dpkg -l | grep -q "raspberrypi-ui-mods"; then
    echo "✅ Desktop environment available for HDMI display"
    
    # Create HDMI display service
    cat > /etc/systemd/system/cec-hdmi-display.service << EOFINNER
[Unit]
Description=CEC HDMI Professional Display
After=cec-flipper.service graphical-session.target
Wants=cec-flipper.service

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/chromium-browser --kiosk --disable-infobars --disable-session-crashed-bubble --disable-web-security http://localhost:8080/display
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
EOFINNER

    systemctl enable cec-hdmi-display.service
    echo "✅ HDMI auto-launch service enabled"
else
    echo "⚠️ No desktop environment - HDMI display available via browser only"
    echo "💡 Access at: http://[PI_IP]:8080/display"
fi

# Create user autostart directory and file (fallback)
CURRENT_USER=$(logname 2>/dev/null || echo "pi")
USER_HOME="/home/$CURRENT_USER"
AUTOSTART_DIR="$USER_HOME/.config/autostart"

mkdir -p "$AUTOSTART_DIR"
chown $CURRENT_USER:$CURRENT_USER "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/cec-hdmi-display.desktop" << EOFINNER
[Desktop Entry]
Type=Application
Name=CEC HDMI Display
Exec=chromium-browser --kiosk --disable-infobars http://localhost:8080/display
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOFINNER

chown $CURRENT_USER:$CURRENT_USER "$AUTOSTART_DIR/cec-hdmi-display.desktop"
chmod +x "$AUTOSTART_DIR/cec-hdmi-display.desktop"

# Add user to required groups
usermod -a -G dialout,tty $CURRENT_USER

echo "📺 Testing browser installation..."
if command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium browser installed successfully"
else
    echo "⚠️ Browser installation may have issues"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📌 Features installed:"
echo "   ✅ UART enabled for Flipper communication"
echo "   ✅ HTTP server available on port 8080"
echo "   ✅ Professional HDMI display with auto-launch"
echo "   ✅ Samsung DB10E volume commands (tx 0F:44:41)"
echo "   ✅ No auto-detection - fast command execution"
echo ""
echo "📺 HDMI Display Features:"
echo "   🖥️ Professional interface with your logo"
echo "   📊 Real-time command logging and statistics"
echo "   🔄 Auto-refreshes every 3 seconds"
echo "   🚀 Auto-launches in browser on boot"
echo ""
echo "🔗 Access Methods:"
echo "   📱 Flipper: Select '📺 Show Logs on HDMI'"
echo "   🌐 Browser: http://[PI_IP]:8080/display"
echo "   ⌨️ Manual: chromium-browser --kiosk http://localhost:8080/display"
echo ""
echo "🔄 Reboot required to enable UART and HDMI display"
echo ""

read -p "Reboot now to complete setup? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting to activate all features..."
  reboot
fi
