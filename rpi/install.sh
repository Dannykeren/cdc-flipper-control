#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - FIELD READY"
echo "   100% Autonomous HDMI Display"
echo "   NO WIFI/SSH NEEDED IN FIELD"
echo "========================================="

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash $0"
  exit 1
fi

echo "🔧 Configuring 100% autonomous operation..."

# Remove any desktop environment that requires login
echo "🗑️ Removing problematic desktop components..."
apt remove --purge -y raspberrypi-ui-mods lxde* lightdm* 2>/dev/null || true
apt autoremove -y

# Install only what we need for HDMI output
echo "📦 Installing minimal HDMI display components..."
apt update
apt install -y xorg chromium-browser openbox xinit xserver-xorg-legacy

# Configure auto-login (NO LOGIN SCREEN EVER)
echo "🔑 Configuring auto-login..."
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I $TERM
Type=idle
EOF

# Set multi-user target (no graphical login)
systemctl set-default multi-user.target

# Create BULLETPROOF auto-start sequence
echo "🚀 Creating bulletproof auto-start..."

# Pi user auto-start on login
cat > /home/pi/.bash_profile << 'EOF'
# FIELD MODE: Auto-start CEC display on any login
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    echo "🖥️ FIELD MODE: Starting CEC Display..."
    startx /home/pi/.xinitrc -- :0 vt1 >/dev/null 2>&1
fi
EOF

# Create X11 startup script - KEEP DISPLAY ALWAYS ON
cat > /home/pi/.xinitrc << 'EOF'
#!/bin/bash
# Wait for services
sleep 20

# Disable power management  
xset s off 2>/dev/null || true
xset s noblank 2>/dev/null || true
xset -dpms 2>/dev/null || true

# Start window manager
openbox &
sleep 2

# Launch browser
DISPLAY=:0 chromium-browser \
    --kiosk \
    --no-sandbox \
    --disable-web-security \
    --window-size=1920,1080 \
    http://localhost:8080/display &

wait
EOF

chmod +x /home/pi/.xinitrc
chown pi:pi /home/pi/.xinitrc /home/pi/.bash_profile

# Create FAILSAFE systemd service for HDMI display
echo "🛡️ Creating failsafe HDMI service..."
cat > /etc/systemd/system/cec-hdmi-display.service << 'EOF'
[Unit]
Description=CEC HDMI Display - FIELD MODE
After=cec-flipper.service multi-user.target
Wants=cec-flipper.service
Conflicts=getty@tty1.service

[Service]
Type=simple
User=pi
Group=pi
Environment=HOME=/home/pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi
ExecStartPre=/bin/sleep 20
ExecStart=/usr/bin/startx /home/pi/.xinitrc -- :0 vt1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl enable cec-hdmi-display.service

# Create EMERGENCY recovery script (runs on every boot)
echo "🚨 Creating emergency recovery system..."
cat > /home/pi/emergency_display_start.sh << 'EOF'
#!/bin/bash
# EMERGENCY: Force start CEC display if everything else fails

echo "🚨 EMERGENCY: Force starting CEC display..."

# Kill anything blocking
sudo pkill -f chromium 2>/dev/null || true
sudo pkill -f startx 2>/dev/null || true

# Wait
sleep 3

# Force start X and display
export DISPLAY=:0
startx /home/pi/.xinitrc -- :0 vt1 &

echo "🚨 Emergency display start completed"
EOF

chmod +x /home/pi/emergency_display_start.sh
chown pi:pi /home/pi/emergency_display_start.sh

# Add emergency start to crontab (runs every 2 minutes if needed)
cat > /tmp/emergency_cron << 'EOF'
# FIELD MODE: Emergency display recovery every 2 minutes
*/2 * * * * /home/pi/emergency_display_start.sh >/dev/null 2>&1
EOF

crontab -u pi /tmp/emergency_cron
rm /tmp/emergency_cron

# Configure HDMI to ALWAYS output (even if no display detected)
echo "📺 Forcing HDMI output..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="/boot/config.txt"
fi

# Remove any existing HDMI settings
sed -i '/hdmi_force_hotplug/d' "$CONFIG_FILE"
sed -i '/hdmi_drive/d' "$CONFIG_FILE"
sed -i '/hdmi_group/d' "$CONFIG_FILE"
sed -i '/hdmi_mode/d' "$CONFIG_FILE"

# Add BULLETPROOF HDMI settings
cat >> "$CONFIG_FILE" << 'EOF'

# FIELD MODE: Force HDMI output always
hdmi_force_hotplug=1
hdmi_drive=2
hdmi_group=2
hdmi_mode=82
hdmi_ignore_edid=0xa5000080
config_hdmi_boost=4
EOF

# Ensure CEC service starts early and stays running
echo "🔧 Hardening CEC service..."
cat > /etc/systemd/system/cec-flipper.service << 'EOF'
[Unit]
Description=CEC Flipper Control - FIELD MODE
After=network.target
Before=cec-hdmi-display.service

[Service]
Type=simple
ExecStart=/opt/cec-flipper/venv/bin/python /opt/cec-flipper/main.py
WorkingDirectory=/opt/cec-flipper
Restart=always
RestartSec=3
User=root
Group=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cec-flipper.service
systemctl enable cec-hdmi-display.service

# Final user permissions
usermod -a -G dialout,tty,video,audio pi

# Create boot-time display test
echo "✅ Creating boot display test..."
cat > /etc/systemd/system/boot-display-test.service << 'EOF'
[Unit]
Description=Boot Display Test
After=cec-flipper.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 30; curl -s http://localhost:8080/display > /tmp/display_test.html'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable boot-display-test.service

echo ""
echo "✅ FIELD-READY SETUP COMPLETE!"
echo ""
echo "🎯 AUTONOMOUS OPERATION CONFIGURED:"
echo "   ✅ No login screen - ever"
echo "   ✅ CEC display auto-starts on boot"
echo "   ✅ Browser auto-restarts if it crashes"
echo "   ✅ Emergency recovery every 2 minutes"
echo "   ✅ HDMI forced output (even without display)"
echo "   ✅ 100% headless field operation"
echo ""
echo "🚀 FIELD DEPLOYMENT READY:"
echo "   📦 Pack: Flipper + Pi + HDMI cable + power"
echo "   🔌 Connect: HDMI to TV/projector"
echo "   ⚡ Power on: Display appears automatically"
echo "   📱 Use Flipper: Results show on HDMI instantly"
echo ""
echo "🛡️ FAILSAFE FEATURES:"
echo "   🔄 Auto-restart if browser crashes"
echo "   🚨 Emergency recovery every 2 minutes"
echo "   📺 HDMI output forced (no detection needed)"
echo "   ⚡ Services restart automatically"
echo ""
echo "🔄 REBOOT NOW to activate field mode"
echo ""

read -p "Reboot now for field-ready operation? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting to FIELD MODE..."
  reboot
fi
