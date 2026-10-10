#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from unittest.mock import MagicMock

# Mock discord module before importing bgpbot
mock_discord = MagicMock()
mock_discord.ext.commands.Bot = MagicMock()
sys.modules["discord"] = mock_discord
sys.modules["discord.ext"] = MagicMock()
sys.modules["discord.ext.commands"] = mock_discord.ext.commands

import bgpbot
import unittest
from unittest.mock import patch

small_txt = "this is some text"


class ClientTest(unittest.TestCase):

    def test_quotes(self):
        self.assertEqual(f"```{small_txt}```", bgpbot.quote(small_txt))
        self.assertEqual(f"```🟢 {small_txt}```", bgpbot.green_quote(small_txt))
        self.assertEqual(f"```🟡 {small_txt}```", bgpbot.yellow_quote(small_txt))
        self.assertEqual(f"```🔴 {small_txt}```", bgpbot.red_quote(small_txt))

    @patch('bgpstuff.Client')
    def test_totals(self, mock_client):
        mock_bgp = mock_client.return_value
        mock_bgp.status_code = 200
        mock_bgp.total_v4 = 100
        mock_bgp.total_v6 = 200

        result = bgpbot.get_totals(mock_bgp)
        expected = bgpbot.BotResponse("I see 100 IPv4 and 200 IPv6 prefixes active", "green")
        self.assertEqual(expected, result)

    @patch('bgpstuff.Client')
    def test_bogon_ip_rejection(self, mock_client):
        mock_bgp = mock_client.return_value

        # Test private IPv4 in route
        res = bgpbot.get_route("10.0.0.1", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("10.0.0.1 is a bogon: RFC 1918 (Private-Use)", res.text)
        mock_bgp.get_route.assert_not_called()

        # Test loopback in origin
        res = bgpbot.get_origin("127.0.0.1", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("127.0.0.1 is a bogon: RFC 1122 (Loopback)", res.text)
        mock_bgp.get_origin.assert_not_called()

        # Test carrier grade NAT in geoip
        res = bgpbot.get_geoip("100.64.0.1", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("100.64.0.1 is a bogon: RFC 6598 (Shared Address Space / CGNAT)", res.text)
        mock_bgp.get_geoip.assert_not_called()

        # Test documentation IPv6 in roa
        res = bgpbot.get_roa("2001:db8::1", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("2001:db8::1 is a bogon: RFC 3849 (Documentation)", res.text)
        mock_bgp.get_roa.assert_not_called()

        # Test invalid string in aspath
        res = bgpbot.get_aspath("invalid-ip", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("invalid-ip is a bogon: Invalid prefix syntax", res.text)
        mock_bgp.get_as_path.assert_not_called()

    @patch('bgpstuff.Client')
    def test_bogon_asn_rejection(self, mock_client):
        mock_bgp = mock_client.return_value

        # Reserved ASN 0
        res = bgpbot.get_asname(0, mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("AS0 is a reserved/bogon ASN: RFC 6483 / RFC 7607 (Reserved ASN 0)", res.text)
        mock_bgp.get_as_name.assert_not_called()

        # 16-bit Private ASN as string with "AS" prefix
        res = bgpbot.get_invalids("AS64512", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("AS64512 is a reserved/bogon ASN: RFC 1930 / RFC 6996 (Private-Use 16-bit)", res.text)

        # 32-bit Documentation ASN in asdot notation "1.0" = 65536
        res = bgpbot.get_vrps("1.0", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("AS65536 is a reserved/bogon ASN: RFC 5398 (Documentation 32-bit)", res.text)
        mock_bgp.get_vrps.assert_not_called()

        # Last 16-bit ASN 65535 in sourced
        res = bgpbot.get_sourced("65535", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("AS65535 is a reserved/bogon ASN: RFC 7300 (Reserved 16-bit Last ASN)", res.text)
        mock_bgp.get_sourced_prefixes.assert_not_called()

        # Non-numeric/malformed ASN
        res = bgpbot.get_asname("not-an-asn", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("not-an-asn is not a valid ASN", res.text)

    @patch('bgpstuff.Client')
    def test_valid_public_asn_handling(self, mock_client):
        mock_bgp = mock_client.return_value
        mock_bgp.status_code = 200
        mock_bgp.exists = True
        mock_bgp.as_name = "GOOGLE"

        # AS15169 as string with prefix
        res = bgpbot.get_asname("AS15169", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual("The AS name for AS15169 is GOOGLE", res.text)
        mock_bgp.get_as_name.assert_called_with(15169)


if __name__ == '__main__':
    unittest.main()
