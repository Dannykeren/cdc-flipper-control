#!/bin/bash

echo "========================================="
echo "     ICSS Professional CEC Tool"
echo "    Static Display - Field Ready"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

# Detect actual username
ACTUAL_USER=$(logname 2>/dev/null || echo "admin")
USER_HOME="/home/$ACTUAL_USER"

echo "🔄 Installing for user: $ACTUAL_USER..."
apt update && apt upgrade -y

echo "📦 Installing required packages..."
apt install -y cec-utils python3-pip python3-venv
apt install -y xorg feh imagemagick openbox xinit xserver-xorg-legacy

echo "🔧 Enabling UART for Flipper communication..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Clean UART setup
sed -i '/dtoverlay=miniuart-bt/d' "$CONFIG_FILE"
sed -i '/enable_uart/d' "$CONFIG_FILE"
sed -i '/dtoverlay=disable-bt/d' "$CONFIG_FILE"
sed -i '/dtparam=uart/d' "$CONFIG_FILE"

echo "enable_uart=1" >> "$CONFIG_FILE"
echo "dtoverlay=disable-bt" >> "$CONFIG_FILE"
echo "dtparam=uart=on" >> "$CONFIG_FILE"

echo "🖥️ Configuring HDMI output..."
sed -i '/hdmi_force_hotplug/d' "$CONFIG_FILE"
sed -i '/hdmi_drive/d' "$CONFIG_FILE"
sed -i '/hdmi_group/d' "$CONFIG_FILE"
sed -i '/hdmi_mode/d' "$CONFIG_FILE"

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

echo "📥 Downloading CEC application..."
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/main.py" > $INSTALL_DIR/main.py; then
    echo "✅ Downloaded main.py"
else
    echo "❌ Failed to download main.py"
    exit 1
fi

chmod +x $INSTALL_DIR/main.py

echo "🎨 Creating ICSS professional display..."

# Download logo files
echo "📥 Downloading ICSS logos..."
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/logos/icss_logo.png" > /tmp/icss_logo.png; then
    echo "✅ Downloaded ICSS logo"
else
    echo "⚠️ Logo download failed, creating text-only version"
fi

# Create the static ICSS professional display with logo
if [ -f "/tmp/icss_logo.png" ]; then
    echo "🎨 Creating display with logo..."
    convert -size 1920x1080 xc:'#1e3c72' \
      \( /tmp/icss_logo.png -resize 400x400 \) -gravity northwest -geometry +100+100 -composite \
      -gravity center \
      -pointsize 120 -fill white -annotate +0-200 'ICSS' \
      -pointsize 90 -fill white -annotate +0-100 'Integrated Control Solutions' \
      -pointsize 70 -fill '#4ecdc4' -annotate +0+20 'Professional HDMI CEC Test Tool' \
      -pointsize 55 -fill white -annotate +0+120 'Powered by Raspberry Pi Zero 2 and Flipper Zero' \
      -pointsize 45 -fill '#4ecdc4' -annotate +0+200 'Designed by ICSS - Danny Keren' \
      -pointsize 40 -fill white -annotate +0+280 'Ready for Professional Field Testing' \
      -pointsize 35 -fill '#aaaaaa' -annotate +0+350 'Use Flipper Zero to control CEC devices' \
      "$USER_HOME/icss_display.png"
else
    echo "🎨 Creating text-only display (logo not available)..."
    convert -size 1920x1080 xc:'#1e3c72' \
      -gravity center \
      -pointsize 140 -fill white -annotate +0-250 'ICSS' \
      -pointsize 100 -fill white -annotate +0-120 'Integrated Control Solutions' \
      -pointsize 70 -fill '#4ecdc4' -annotate +0+20 'Professional HDMI CEC Test Tool' \
      -pointsize 55 -fill white -annotate +0+120 'Powered by Raspberry Pi Zero 2 and Flipper Zero' \
      -pointsize 45 -fill '#4ecdc4' -annotate +0+200 'Designed by ICSS - Danny Keren' \
      -pointsize 40 -fill white -annotate +0+280 'Ready for Professional Field Testing' \
      -pointsize 35 -fill '#aaaaaa' -annotate +0+350 'Use Flipper Zero to control CEC devices' \
      "$USER_HOME/icss_display.png"
fi

# Clean up temporary files
rm -f /tmp/icss_logo.png

echo "✅ Created ICSS professional display"

echo "🔧 Creating CEC service..."
cat > /etc/systemd/system/cec-flipper.service << 'EOF'
[Unit]
Description=ICSS CEC Professional Tool
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

echo "🖥️ Setting up display auto-start..."

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
cat > "$USER_HOME/start_icss_display.sh" << EOF
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

# Show static ICSS display
DISPLAY=:0 feh --fullscreen --hide-pointer $USER_HOME/icss_display.png &
EOF

chmod +x "$USER_HOME/start_icss_display.sh"

# Create auto-start on login
cat > "$USER_HOME/.bash_profile" << EOF
if [ -z "\$DISPLAY" ] && [ "\$(tty)" = "/dev/tty1" ]; then
    $USER_HOME/start_icss_display.sh
fi
EOF

chown $ACTUAL_USER:$ACTUAL_USER "$USER_HOME/.bash_profile" "$USER_HOME/start_icss_display.sh" "$USER_HOME/icss_display.png"

# Add user to required groups
usermod -a -G dialout,tty,video $ACTUAL_USER

systemctl set-default multi-user.target

echo ""
echo "✅ ICSS PROFESSIONAL SETUP COMPLETE!"
echo ""
echo "🎯 PROFESSIONAL FEATURES:"
echo "   ✅ ICSS branded professional display"
echo "   ✅ Static, reliable, never fails"
echo "   ✅ Auto-start on boot - zero maintenance"
echo "   ✅ Clean field deployment solution"
echo ""
echo "📱 OPERATION:"
echo "   🔌 Power on → Professional ICSS display appears"
echo "   📱 Use Flipper Zero → Commands processed via UART"
echo "   ✅ Reliable feedback via Flipper display"
echo "   🏢 Professional appearance for client demos"
echo ""
echo "🔄 Reboot required to activate display"
echo ""

read -p "Reboot now to activate ICSS professional display? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting to ICSS professional mode..."
  reboot
fi
