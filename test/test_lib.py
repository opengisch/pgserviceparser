#! /usr/bin/env python
import os
import unittest
from pathlib import Path

from pgserviceparser import service_names

PGSERVICEPARSER_SRC_PATH = Path(os.environ["PGSERVICEPARSER_SRC_DIR"])


class TestLib(unittest.TestCase):
    def setUp(self):
        os.environ["PGSERVICEFILE"] = str(PGSERVICEPARSER_SRC_PATH / "test" / "data" / "service_base.txt")

    def test_service_names(self):
        self.assertEqual(service_names(), ["service_1", "service_2", "service_3"])
