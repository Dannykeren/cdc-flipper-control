#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - HDMI Auto-Fix"
echo "   Fixing HDMI Display Auto-Launch"
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

# Install minimal X11 and browser without full desktop
echo "🖥️ Installing minimal display environment..."
apt install -y xorg xserver-xorg-legacy chromium-browser openbox xinit

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

echo "🖥️ Setting up AUTO-LAUNCH HDMI display..."

# Configure auto-login for pi user (no login screen)
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOFINNER
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
EOFINNER

# Create auto-start X11 script for pi user
cat > /home/pi/.bash_profile << EOFINNER
# Auto-start X11 with CEC display on login
if [ -z "\$DISPLAY" ] && [ "\$(tty)" = "/dev/tty1" ]; then
    startx
fi
EOFINNER

# Create X11 startup script
cat > /home/pi/.xinitrc << EOFINNER
#!/bin/bash
# Disable screen blanking
xset s off
xset s noblank
xset -dpms

# Start window manager
openbox &

# Wait for CEC service to be ready
sleep 10

# Launch CEC display in fullscreen browser
chromium-browser \\
    --kiosk \\
    --disable-infobars \\
    --disable-session-crashed-bubble \\
    --disable-web-security \\
    --disable-features=TranslateUI \\
    --disable-ipc-flooding-protection \\
    --window-position=0,0 \\
    --window-size=1920,1080 \\
    http://localhost:8080/display &

# Keep X11 running
wait
EOFINNER

chmod +x /home/pi/.xinitrc
chown pi:pi /home/pi/.xinitrc
chown pi:pi /home/pi/.bash_profile

# Set auto-login target
systemctl set-default multi-user.target

# Create additional CEC HDMI service for redundancy
cat > /etc/systemd/system/cec-hdmi-autostart.service << EOFINNER
[Unit]
Description=CEC HDMI Auto Display
After=cec-flipper.service
Wants=cec-flipper.service
Conflicts=getty@tty1.service

[Service]
Type=simple
User=pi
Group=pi
Environment=HOME=/home/pi
WorkingDirectory=/home/pi
ExecStartPre=/bin/sleep 15
ExecStart=/usr/bin/startx
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFINNER

systemctl enable cec-hdmi-autostart.service

# Add user to required groups
usermod -a -G dialout,tty,video pi

echo "📺 Testing browser installation..."
if command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium browser installed successfully"
else
    echo "⚠️ Browser installation may have issues"
fi

# Create manual start script for testing
cat > /home/pi/start_cec_display.sh << EOFINNER
#!/bin/bash
export DISPLAY=:0
chromium-browser --kiosk --disable-infobars http://localhost:8080/display &
EOFINNER

chmod +x /home/pi/start_cec_display.sh
chown pi:pi /home/pi/start_cec_display.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "📌 HDMI Auto-Launch Features:"
echo "   ✅ Auto-login configured (no login screen)"
echo "   ✅ CEC display launches automatically on boot"
echo "   ✅ Professional interface always visible"
echo "   ✅ No manual 'Show on TV' needed"
echo ""
echo "📺 HDMI Display Features:"
echo "   🖥️ Professional interface with your logo"
echo "   📊 Real-time command logging and statistics"
echo "   🔄 Auto-refreshes every 3 seconds"
echo "   🚀 Launches automatically on boot"
echo ""
echo "🔗 Access Methods:"
echo "   📱 Flipper: Commands will show on HDMI automatically"
echo "   🌐 Browser: http://[PI_IP]:8080/display"
echo "   ⌨️ Manual test: /home/pi/start_cec_display.sh"
echo ""
echo "🔧 If HDMI display doesn't work after reboot:"
echo "   ssh pi@[PI_IP]"
echo "   ./start_cec_display.sh"
echo ""
echo "🔄 Reboot required to enable all features"
echo ""

read -p "Reboot now to activate auto HDMI display? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting to activate auto HDMI display..."
  reboot
fi
