import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from .power_manager import PowerManager
from .theme_manager import ThemeManager
from .indicator import CPUProfileIndicator
from .menu import IndicatorMenu

def setup_logging():
    log_dir = os.path.expanduser("~/.cache")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "gnome-toolbelt.log")
        
        # Keep logs at max 512KB and backup last 1 file
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=512 * 1024,
            backupCount=1,
            encoding='utf-8'
        )
    except Exception as e:
        print("Warning: Could not create rotating log file handler, logging to stderr only:", e)
        file_handler = None

    stream_handler = logging.StreamHandler(sys.stderr)
    
    handlers = [stream_handler]
    if file_handler:
        handlers.append(file_handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized.")

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Initializing Gnome Toolbelt indicator...")
    
    # 1. Initialize logic managers
    power_mgr = PowerManager()
    theme_mgr = ThemeManager()
    
    # 2. Initialize AppIndicator with starting CPU profile
    initial_profile = power_mgr.get_active_profile()
    indicator = CPUProfileIndicator(initial_profile)
    
    # 3. Initialize custom GTK Menu, providing updater callbacks
    menu = IndicatorMenu(
        power_manager=power_mgr,
        theme_manager=theme_mgr,
        indicator_updater=indicator.update_profile
    )
    
    # 4. Attach menu to indicator
    indicator.set_menu(menu)
    
    # 5. Run GTK main loop
    logger.info("Entering Gtk main loop.")
    try:
        Gtk.main()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting.")
    finally:
        logger.info("Gtk main loop terminated. Cleaning up managers and exiting application.")
        try:
            power_mgr.close()
        except Exception:
            logger.debug("PowerManager.close() raised during shutdown; continuing.")
        try:
            theme_mgr.close()
        except Exception:
            logger.debug("ThemeManager.close() raised during shutdown; continuing.")

if __name__ == '__main__':
    main()
