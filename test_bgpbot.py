#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bgpbot
import bgpstuff
import unittest
from unittest.mock import Mock, patch

small_txt = "this is some text"


class ClientTest(unittest.TestCase):

    def test_quote(self):
        self.assertEqual((f"```{small_txt}```"), bgpbot.quote(small_txt))

    def test_red_quote(self):
        self.assertEqual((f"```🔴 {small_txt}```"), bgpbot.red_quote(small_txt))

    @patch.object(bgpstuff.Client, 'get_totals')
    def test_totals(self):
        mock_bgp = Mock()
        totals.ret
        self.assertEqual("something", bgpbot.totals(mock_bgp))


if __name__ == '__main__':
    unittest.main()
