#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bgpstuff
import unittest
from bgpbot import *

small_txt = "this is some text"


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.client = bgpstuff.Client()

    def test_quote(self):
        self.assertEqual((f"```{small_txt}```"), quote(small_txt))

    def test_red_quote(self):
        self.assertEqual((f"```🔴 {small_txt}```"), red_quote(small_txt))


if __name__ == '__main__':
    unittest.main()
