import unittest
from app.src.power_manager import PowerManager
from app.src.theme_manager import ThemeManager


class FakeProxy:
    def __init__(self):
        self._next_id = 1
        self._connected = {}
        self.disconnect_calls = []

    def connect(self, signal_name, callback):
        hid = self._next_id
        self._next_id += 1
        self._connected[hid] = (signal_name, callback)
        return hid

    def disconnect(self, hid):
        self.disconnect_calls.append(hid)
        if hid in self._connected:
            del self._connected[hid]

    # provide minimal get_cached_property used by PowerManager tests
    def get_cached_property(self, name):
        class V:
            def unpack(self):
                return 'balanced'
        return V()


class FakeSettings:
    def __init__(self):
        self._next_id = 1
        self._connected = {}
        self.disconnect_calls = []

    def connect(self, signal_name, callback):
        hid = self._next_id
        self._next_id += 1
        self._connected[hid] = (signal_name, callback)
        return hid

    def disconnect(self, hid):
        self.disconnect_calls.append(hid)
        if hid in self._connected:
            del self._connected[hid]

    def get_string(self, key):
        return 'default'

    def set_string(self, key, val):
        return True


class IntegrationLifecycleTest(unittest.TestCase):
    def test_startup_and_shutdown_cleans_handlers(self):
        # Start managers with fake system objects (headless)
        fake_proxy = FakeProxy()
        fake_settings = FakeSettings()

        pm = PowerManager(proxy=fake_proxy)
        tm = ThemeManager(settings=fake_settings)

        # connecting external callbacks (simulating menu attach)
        pm.connect_changed(lambda v: None)
        tm.connect_changed(lambda v: None)

        # Ensure handlers were connected (ids stored)
        self.assertIsNotNone(pm._properties_changed_handler_id)
        self.assertIn(pm._properties_changed_handler_id, fake_proxy._connected)
        self.assertIsNotNone(tm._changed_handler_id)
        self.assertIn(tm._changed_handler_id, fake_settings._connected)

        # Now shutdown / cleanup
        pm.close()
        tm.close()

        # After close, handlers should have been disconnected and references cleared
        self.assertNotIn(pm._properties_changed_handler_id, getattr(fake_proxy, '_connected', {}))
        self.assertNotIn(tm._changed_handler_id, getattr(fake_settings, '_connected', {}))
        self.assertIsNone(pm.on_changed_callback)
        self.assertIsNone(tm.on_changed_callback)
        self.assertIsNone(pm.power_proxy)
        self.assertIsNone(tm.theme_settings)


if __name__ == '__main__':
    unittest.main()
