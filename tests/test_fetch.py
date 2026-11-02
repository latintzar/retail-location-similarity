"""A failed/changed download must preserve existing user files and leave no partials."""
from io import BytesIO
from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
import os
import stat

p = Path(__file__).resolve().parents[1] / 'tools/fetch_london.py'
spec = importlib.util.spec_from_file_location('fetch_london', p)
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class MatrixFetchTest(unittest.TestCase):
    def test_valid_bytes_are_verified_and_existing_verified_copy_is_reused(self):
        data = b'tiny test transport payload'
        manifest = {'download_url': 'https://example.org/fixture', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'matrix.parquet'
            fetcher.fetch(output, manifest=manifest, opener=lambda *a, **k: BytesIO(data))
            self.assertEqual(output.read_bytes(), data)
            fetcher.fetch(output, manifest=manifest, opener=lambda *a, **k: self.fail('verified copy must be reused'))
            self.assertEqual(list(Path(directory).glob('*.part')), [])

    def test_mismatched_or_excess_bytes_never_install_a_matrix(self):
        expected = b'expected'
        manifest = {'download_url': 'https://example.org/fixture', 'bytes': len(expected), 'sha256': hashlib.sha256(expected).hexdigest()}
        for payload in [b'changed!', b'too long payload', b'short']:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'matrix.parquet'
                with self.assertRaises(ValueError):
                    fetcher.fetch(output, manifest=manifest, opener=lambda *a, **k: BytesIO(payload))
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_existing_different_or_concurrently_created_file_is_preserved(self):
        data = b'payload'
        manifest = {'download_url': 'https://example.org/fixture', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'matrix.parquet'
            output.write_bytes(b'user original')
            with self.assertRaises(ValueError):
                fetcher.fetch(output, manifest=manifest, opener=lambda *a, **k: self.fail('must preserve existing file'))
            self.assertEqual(output.read_bytes(), b'user original')
            output.unlink()
            def racing_response(*args, **kwargs):
                output.write_bytes(b'concurrent user file')
                return BytesIO(data)
            with self.assertRaises(FileExistsError):
                fetcher.fetch(output, manifest=manifest, opener=racing_response)
            self.assertEqual(output.read_bytes(), b'concurrent user file')
            self.assertEqual(list(Path(directory).glob('*.part')), [])

    def test_post_link_replacement_keeps_foreign_file_and_mode_unchanged(self):
        data = b'payload'
        manifest = {'download_url': 'https://example.org/fixture', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'matrix.parquet'
            victim = Path(directory) / 'unrelated-user-file'
            victim.write_bytes(b'private original')
            victim.chmod(0o600)
            original_link = os.link
            def replace_after_link(source, target):
                original_link(source, target)
                Path(target).unlink()
                Path(target).symlink_to(victim)
            with patch.object(fetcher.os, 'link', side_effect=replace_after_link):
                with self.assertRaises(FileExistsError):
                    fetcher.fetch(output, manifest=manifest, opener=lambda *a, **k: BytesIO(data))
            self.assertTrue(output.is_symlink())
            self.assertEqual(victim.read_bytes(), b'private original')
            self.assertEqual(stat.S_IMODE(victim.stat().st_mode), 0o600)
            self.assertEqual(list(Path(directory).glob('*.part')), [])


if __name__ == '__main__':
    unittest.main()
