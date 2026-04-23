#!/usr/bin/env python3
"""Tests for sif-code-scan scan.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TEST_DIR, "fixtures")
ACTION_DIR = os.path.join(os.path.dirname(os.path.dirname(TEST_DIR)), ".github", "actions", "sif-code-scan")
SCAN_PY = os.path.join(ACTION_DIR, "scan.py")

ALLOWED_FNR = "03021700214"
NON_ALLOWED_FNR = "01017000108"
INVALID_FNR = "12345678901"
H_NUMMER = "01417000190"  # Fiktivt H-nummer (maaned+40), skal ikke flagges
D_NUMMER = "41017000010"  # D-nummer (dag+40), er skarpt FNR og skal flagges


class ScanTestBase(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.workdir, ".git"))

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def run_scan(self):
        return subprocess.run(
            [sys.executable, SCAN_PY],
            cwd=self.workdir,
            capture_output=True,
            text=True,
        )

    def assert_scan_passes(self):
        result = self.run_scan()
        self.assertEqual(result.returncode, 0, f"Scan should pass.\nstdout: {result.stdout}\nstderr: {result.stderr}")

    def assert_scan_fails(self):
        result = self.run_scan()
        self.assertNotEqual(result.returncode, 0, f"Scan should fail.\nstdout: {result.stdout}\nstderr: {result.stderr}")

    def write_file(self, name, content):
        path = os.path.join(self.workdir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def copy_fixture(self, fixture_name, dest_name=None):
        shutil.copy(
            os.path.join(FIXTURES_DIR, fixture_name),
            os.path.join(self.workdir, dest_name or fixture_name),
        )


class TestTextFiles(ScanTestBase):
    def test_clean_file(self):
        self.write_file("clean.kt", 'val x = "hello world"\n')
        self.assert_scan_passes()

    def test_allowed_fnr(self):
        self.write_file("allowed.kt", f'val testFnr = "{ALLOWED_FNR}"\n')
        self.assert_scan_passes()

    def test_non_allowed_fnr(self):
        self.write_file("bad.kt", f'val fnr = "{NON_ALLOWED_FNR}"\n')
        self.assert_scan_fails()

    def test_invalid_fnr_passes(self):
        self.write_file("invalid.kt", f'val num = "{INVALID_FNR}"\n')
        self.assert_scan_passes()

    def test_mixed_allowed_and_non_allowed(self):
        self.write_file("mixed.json", f'{{"allowed": "{ALLOWED_FNR}", "bad": "{NON_ALLOWED_FNR}"}}\n')
        self.assert_scan_fails()

    def test_h_nummer_passes(self):
        self.write_file("h_nummer.kt", f'val fnr = "{H_NUMMER}"\n')
        self.assert_scan_passes()

    def test_d_nummer_fails(self):
        self.write_file("d_nummer.kt", f'val fnr = "{D_NUMMER}"\n')
        self.assert_scan_fails()


class TestXlsxFiles(ScanTestBase):
    def test_allowed_fnr_in_xlsx(self):
        self.copy_fixture("allowed.xlsx", "test.xlsx")
        self.assert_scan_passes()

    def test_non_allowed_fnr_in_xlsx(self):
        self.copy_fixture("non_allowed.xlsx", "test.xlsx")
        self.assert_scan_fails()


class TestDocxFiles(ScanTestBase):
    def test_allowed_fnr_in_docx(self):
        self.copy_fixture("allowed.docx", "test.docx")
        self.assert_scan_passes()

    def test_non_allowed_fnr_in_docx(self):
        self.copy_fixture("non_allowed.docx", "test.docx")
        self.assert_scan_fails()


class TestExcludedDirs(ScanTestBase):
    def test_non_allowed_fnr_in_target_dir(self):
        self.write_file("target/bad.kt", f'val fnr = "{NON_ALLOWED_FNR}"\n')
        self.assert_scan_passes()
