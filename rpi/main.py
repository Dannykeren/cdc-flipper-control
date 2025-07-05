#!/usr/bin/env python3
"""
CEC Flipper Control - Main Application
Multi-interface CEC controller (HTTP, UART, GPIO)
"""
import time
import logging
import sys
import signal
import cec_control
from http.server import HTTPServer
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

class CECController:
    def __init__(self):
        self.running = False
        self.http_server = None
    
    def start_http_server(self):
        """Start HTTP server in background thread"""
        # Import and start the HTTP server from http_test.py logic
        from http_test import CECHandler, get_ip_address
        
        ip_address = get_ip_address()
        self.http_server = HTTPServer(('0.0.0.0', 8080), CECHandler)
        
        http_thread = threading.Thread(target=self.http_server.serve_forever)
        http_thread.daemon = True
        http_thread.start()
        
        logger.info(f"HTTP server running on http://{ip_address}:8080")
    
    def start_uart_interface(self):
        """Future: UART interface for Flipper Zero"""
        logger.info("UART interface ready (placeholder)")
        # TODO: Implement UART communication
    
    def start_gpio_interface(self):
        """Future: GPIO interface for physical buttons"""
        logger.info("GPIO interface ready (placeholder)")
        # TODO: Implement GPIO button handling
    
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
