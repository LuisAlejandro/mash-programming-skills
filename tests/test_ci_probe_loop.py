"""CI probe: deliberate failing test to exercise the autonomous CI-fix loop.

The assertion below is intentionally wrong. The Cursor "Mash Programming
Skills PR CI fixes" automation is expected to correct it so the suite goes
green. Safe to delete once the probe has served its purpose.
"""

import unittest


def probe_value():
    return "ci-probe-ok"


class CiProbeLoopTest(unittest.TestCase):
    def test_probe_value(self):
        self.assertEqual(probe_value(), "ci-probe-ok")


if __name__ == "__main__":
    unittest.main()
