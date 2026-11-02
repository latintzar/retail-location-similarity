"""Browser/network entry is an explicit action; plain invocation stays local CLI guidance."""
from pathlib import Path
import subprocess
import sys
import unittest


class DefaultEntryTest(unittest.TestCase):
    def test_server_requires_explicit_local_map_mode(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, str(root / 'server.py')], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--local-map', result.stderr)
        self.assertIn('location.py', result.stderr)


if __name__ == '__main__':
    unittest.main()
