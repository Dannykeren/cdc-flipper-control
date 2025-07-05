#!/usr/bin/env python3
"""
CEC Flipper Control - Main Application
Multi-interface CEC controller (HTTP, UART, GPIO)
"""
import time
import logging
import sys
import signal
import json
import threading
import serial
import cec_control
from http.server import HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

class CECController:
    def __init__(self):
        self.running = False
        self.http_server = None
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
                if self.uart_serial.in_waiting > 0:
                    line = self.uart_serial.readline().decode('utf-8').strip()
                    if line:
                        logger.info(f"UART received: '{line}' (length: {len(line)})")
                        response = self.process_command(line)
                        self.uart_serial.write((response + '\n').encode('utf-8'))
                        logger.info(f"UART sent: {response}")
                    else:
                        logger.info("UART received empty line")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"UART error: {e}")
                time.sleep(1)
    
    def process_command(self, command_json):
        """Process CEC command and return response"""
        try:
            command = json.loads(command_json)
            cmd_type = command.get('command', '').upper()
            
            if cmd_type == 'POWER_ON':
                result = cec_control.power_on()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'POWER_OFF':
                result = cec_control.power_off()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'SCAN':
                result = cec_control.scan_devices()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'STATUS':
                result = cec_control.get_power_status()
                return json.dumps({"status": "success", "result": result})
            elif cmd_type == 'PING':
                return json.dumps({"status": "success", "result": "pong"})
            else:
                return json.dumps({"status": "error", "result": "Unknown command"})
                
        except Exception as e:
            return json.dumps({"status": "error", "result": str(e)})
    
    def start_http_server(self):
        """Start HTTP server in background thread"""
        from http_test import CECHandler, get_ip_address
        
        ip_address = get_ip_address()
        self.http_server = HTTPServer(('0.0.0.0', 8080), CECHandler)
        
        http_thread = threading.Thread(target=self.http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        
        logger.info(f"HTTP server running on http://{ip_address}:8080")
    
    def start_gpio_interface(self):
        """Future: GPIO interface for physical buttons"""
        logger.info("GPIO interface ready (placeholder)")
    
    def run(self):
        """Main application loop"""
        self.running = True
        
        # Start all interfaces
        self.start_http_server()
        self.start_uart_interface()
        self.start_gpio_interface()
        
        logger.info("CEC Controller running with all interfaces")
        
        # Keep running
        while self.running:
            time.sleep(1)
    
    def stop(self):
        """Stop all interfaces"""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
        if self.uart_serial:
            self.uart_serial.close()
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
