#!/bin/bash

echo "========================================="
echo "  CEC HDMI Display Setup"
echo "  Installing browser and display files"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

echo "📦 Installing browser for HDMI display..."
apt update
apt install -y chromium-browser

echo "📁 Setting up HDMI display files..."
INSTALL_DIR="/opt/cec-flipper"

# Copy HDMI template to install directory
if [ -f "hdmi_display_template.html" ]; then
    cp hdmi_display_template.html $INSTALL_DIR/
    echo "✅ Copied HDMI template"
else
    echo "❌ hdmi_display_template.html not found in current directory"
    exit 1
fi

# Copy HDMI display module
if [ -f "hdmi_display.py" ]; then
    cp hdmi_display.py $INSTALL_DIR/
    echo "✅ Copied HDMI display module"
else
    echo "❌ hdmi_display.py not found in current directory"
    exit 1
fi

echo "🖥️ Configuring HDMI output..."
# Force HDMI output in config.txt
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Add HDMI settings if not present
if ! grep -q "hdmi_force_hotplug=1" "$CONFIG_FILE"; then
    echo "hdmi_force_hotplug=1" >> "$CONFIG_FILE"
fi
if ! grep -q "hdmi_drive=2" "$CONFIG_FILE"; then
    echo "hdmi_drive=2" >> "$CONFIG_FILE"
fi

echo "🚀 Setting up auto-launch service..."
cat > /etc/systemd/system/cec-hdmi-display.service << EOF
[Unit]
Description=CEC HDMI Display
After=cec-flipper.service graphical-session.target
Wants=cec-flipper.service

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 10
ExecStart=/usr/bin/chromium-browser --kiosk --disable-infobars --disable-session-crashed-bubble http://localhost:8080/display
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# Enable the service
systemctl enable cec-hdmi-display.service

echo "🔧 Setting up desktop environment..."
# Ensure desktop environment is enabled
systemctl set-default graphical.target

# Create autostart for user session (fallback)
USER_HOME="/home/pi"
AUTOSTART_DIR="$USER_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
chown pi:pi "$AUTOSTART_DIR"

cat > "$AUTOSTART_DIR/cec-hdmi-display.desktop" << EOF
[Desktop Entry]
Type=Application
Name=CEC HDMI Display
Exec=chromium-browser --kiosk --disable-infobars http://localhost:8080/display
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

chown pi:pi "$AUTOSTART_DIR/cec-hdmi-display.desktop"
chmod +x "$AUTOSTART_DIR/cec-hdmi-display.desktop"

echo "📺 Testing browser installation..."
if command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium browser installed successfully"
else
    echo "⚠️ Browser installation may have issues"
fi

echo ""
echo "✅ HDMI Display setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Connect HDMI cable to display/TV"
echo "2. Reboot Pi: sudo reboot"
echo "3. Use Flipper app and select '📺 Show Logs on HDMI'"
echo "4. Or browse to: http://[PI_IP]:8080/display"
echo ""
echo "🔧 Manual browser launch: chromium-browser --kiosk http://localhost:8080/display"
echo ""

read -p "Reboot now to enable HDMI display? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting..."
  reboot
fi
