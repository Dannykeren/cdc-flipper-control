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

# Download main application with graphics integration
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/main.py" > $INSTALL_DIR/main.py; then
    echo "✅ Downloaded main.py"
else
    echo "❌ Failed to download main.py"
    exit 1
fi

# Download display update script
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/update_display.py" > "$USER_HOME/update_display.py"; then
    echo "✅ Downloaded update_display.py"
else
    echo "❌ Failed to download update_display.py"
    exit 1
fi

# Download graphics creation script
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/create_graphics.sh" > /tmp/create_graphics.sh; then
    echo "✅ Downloaded create_graphics.sh"
else
    echo "❌ Failed to download create_graphics.sh"
    exit 1
fi

chmod +x $INSTALL_DIR/main.py "$USER_HOME/update_display.py" /tmp/create_graphics.sh

echo "🎨 Creating professional graphics display system..."
bash /tmp/create_graphics.sh

# Set proper ownership
chown $ACTUAL_USER:$ACTUAL_USER "$USER_HOME"/*.png "$USER_HOME/update_display.py"

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
cat > "$USER_HOME/start_display.sh" << EOF
#!/bin/bash
export DISPLAY=:0
export HOME=$USER_HOME

# Start X11 in background
startx -- :0 vt1 &
sleep 15

# Disable screensaver
DISPLAY=:0 xset s off
DISPLAY=:0 xset s noblank  
DISPLAY=:0 xset -dpms

# Start with ready status
python3 $USER_HOME/update_display.py ready
EOF

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
