#!/bin/bash

echo "🎨 Creating CEC Tool Status Graphics..."

# Detect user
ACTUAL_USER=$(logname 2>/dev/null || echo "admin")
USER_HOME="/home/$ACTUAL_USER"

echo "Creating graphics for user: $ACTUAL_USER"

# 1. Ready state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill green -geometry +0+450 -annotate 0 '✅ System Ready' \
  -pointsize 28 -geometry +0+500 -annotate 0 '📱 Use Flipper Zero for control' \
  "$USER_HOME/status_ready.png"

echo "✅ Created status_ready.png"

# 2. Sending state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill yellow -geometry +0+450 -annotate 0 '⚡ Processing Command...' \
  -pointsize 28 -geometry +0+500 -annotate 0 '🔄 Please wait' \
  "$USER_HOME/status_sending.png"

echo "✅ Created status_sending.png"

# 3. Success state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill green -geometry +0+450 -annotate 0 '✅ Command Successful' \
  -pointsize 28 -geometry +0+500 -annotate 0 '📊 Check Flipper for details' \
  "$USER_HOME/status_success.png"

echo "✅ Created status_success.png"

# 4. Error state
convert -size 1920x1080 xc:'#1e3c72' \
  -gravity center \
  -pointsize 200 -fill white -annotate 0 'CEC' \
  -pointsize 60 -geometry +0+200 -annotate 0 'Professional HDMI-CEC Tool' \
  -pointsize 40 -geometry +0+300 -annotate 0 'Flipper Zero + Raspberry Pi' \
  -pointsize 32 -fill red -geometry +0+450 -annotate 0 '❌ Command Failed' \
  -pointsize 28 -geometry +0+500 -annotate 0 '🔧 Check connections' \
  "$USER_HOME/status_error.png"

echo "✅ Created status_error.png"

# Set proper ownership
chown $ACTUAL_USER:$ACTUAL_USER "$USER_HOME"/status_*.png

echo ""
echo "🎯 Graphics system ready!"
echo "   ✅ 4 status images created in $USER_HOME"
echo "   ✅ Ready for instant display updates"
echo ""
echo "Test with: python3 $USER_HOME/update_display.py ready"
