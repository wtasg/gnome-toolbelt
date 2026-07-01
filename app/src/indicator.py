import sys
import logging
import gi

logger = logging.getLogger(__name__)

try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
    logger.info("Loaded AyatanaAppIndicator3 library.")
except (ValueError, ImportError):
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
        logger.info("Loaded AppIndicator3 library.")
    except (ValueError, ImportError):
        logger.critical("Fatal: AppIndicator3 or AyatanaAppIndicator3 library is required but was not found.")
        sys.exit(1)

class CPUProfileIndicator:
    def __init__(self, initial_profile):
        logger.info("Initializing Top-Bar AppIndicator...")
        
        # Dynamically resolve category to support different AppIndicator/Ayatana versions robustly
        category = getattr(AppIndicator.IndicatorCategory, 'APPLICATION_STATUS',
                           getattr(AppIndicator.IndicatorCategory, 'SYSTEM_SERVICES',
                                   AppIndicator.IndicatorCategory.OTHER))
        
        self.indicator = AppIndicator.Indicator.new(
            "cpu-profile-theme-indicator",
            self.get_icon_name(initial_profile),
            category
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        logger.info("Top-Bar AppIndicator created successfully with category: %s", category)

    def update_profile(self, profile):
        icon_name = self.get_icon_name(profile)
        logger.info("Updating AppIndicator icon to '%s' (profile: %s)", icon_name, profile)
        self.indicator.set_icon_full(icon_name, f"CPU: {profile.capitalize()}")

    def get_icon_name(self, profile):
        if profile == 'performance':
            return 'power-profile-performance-symbolic'
        elif profile == 'power-saver':
            return 'power-profile-power-saver-symbolic'
        else:
            return 'power-profile-balanced-symbolic'

    def set_menu(self, menu):
        logger.info("Binding GTK Menu to AppIndicator.")
        self.indicator.set_menu(menu)
