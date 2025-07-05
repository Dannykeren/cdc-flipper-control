cat > install.sh << 'EOF'
#!/bin/bash

echo "========================================="
echo "  CEC Flipper Control - Minimal Setup"
echo "   Fresh Raspberry Pi Zero W"
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

echo "🔧 Configuring USB gadget mode..."

# Detect Pi model and use correct USB overlay
PI_MODEL=$(cat /proc/device-tree/model)
echo "Detected: $PI_MODEL"

if [[ "$PI_MODEL" == *"Pi Zero 2"* ]]; then
    # Pi Zero 2 W uses dwc2
    USB_OVERLAY="dwc2"
    USB_MODULE="libcomposite"
    echo "Using dwc2 overlay for Pi Zero 2 W"
else
    # Other Pi models use dwc2
    USB_OVERLAY="dwc2"
    USB_MODULE="libcomposite"
    echo "Using dwc2 overlay for this Pi model"
fi

# Add USB overlay to boot config
if ! grep -q "^dtoverlay=$USB_OVERLAY" /boot/config.txt; then
    # Remove any existing USB overlays first
    sed -i '/^dtoverlay=dwc/d' /boot/config.txt
    echo "dtoverlay=$USB_OVERLAY" >> /boot/config.txt
    echo "✅ Added $USB_OVERLAY overlay to boot config"
fi

# Add required modules
if ! grep -q "^libcomposite" /etc/modules; then
    echo "libcomposite" >> /etc/modules
    echo "✅ Added libcomposite to modules"
fi

if [[ "$USB_MODULE" == "dwc_otg" ]] && ! grep -q "^dwc_otg" /etc/modules; then
    echo "dwc_otg" >> /etc/modules
    echo "✅ Added dwc_otg to modules"
fi

INSTALL_DIR="/opt/cec-flipper"
mkdir -p $INSTALL_DIR

python3 -m venv $INSTALL_DIR/venv
source $INSTALL_DIR/venv/bin/activate
pip install pyserial

cat > /usr/local/bin/setup-usb-gadget.sh << 'EOFINNER'
#!/bin/bash
cd /sys/kernel/config/usb_gadget/
mkdir -p cec_flipper 2>/dev/null || true
cd cec_flipper

echo 0x1d6b > idVendor
echo 0x0104 > idProduct
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

mkdir -p strings/0x409
echo "CEC Flipper" > strings/0x409/manufacturer
echo "RPi CEC Interface" > strings/0x409/product
echo "001" > strings/0x409/serialnumber

mkdir -p configs/c.1/strings/0x409
echo "CEC Config" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

mkdir -p functions/acm.usb0
ln -sf functions/acm.usb0 configs/c.1/ 2>/dev/null || true

ls /sys/class/udc > UDC 2>/dev/null || true

sleep 2
if [ -e /dev/ttyGS0 ]; then
    chmod 666 /dev/ttyGS0
fi
EOFINNER

chmod +x /usr/local/bin/setup-usb-gadget.sh

echo "📥 Downloading application files..."

# Download files with proper error handling
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

# Download HTTP test server
if curl -sSL "https://raw.githubusercontent.com/dannykeren/cec-flipper-control/main/rpi/http_test.py" > $INSTALL_DIR/http_test.py; then
    echo "✅ Downloaded http_test.py"
else
    echo "❌ Failed to download http_test.py"
    exit 1
fi

chmod +x $INSTALL_DIR/http_test.py

cat > /etc/systemd/system/usb-gadget.service << 'EOFINNER'
[Unit]
Description=Setup USB Gadget for CEC Control
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-usb-gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOFINNER

cat > /etc/systemd/system/cec-flipper.service << EOFINNER
[Unit]
Description=CEC Flipper Control
After=usb-gadget.service
Requires=usb-gadget.service

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

systemctl enable usb-gadget.service
systemctl enable cec-flipper.service

CURRENT_USER=$(logname 2>/dev/null || echo "pi")
usermod -a -G dialout,tty $CURRENT_USER

echo "Setup complete! Reboot required."
read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  reboot
fi
EOF
