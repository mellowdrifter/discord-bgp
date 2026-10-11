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
        mock_bgp.get_stats.return_value = [{"totals": {"ipv4_count": 100, "ipv6_count": 200}}]

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

        # IANA Reserved 32-bit ASN 65552
        res = bgpbot.get_asname("65552", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("AS65552 is a reserved/bogon ASN: RFC 7249 / IANA (Reserved 32-bit)", res.text)
        mock_bgp.get_as_name.assert_not_called()

        # Non-numeric/malformed ASN
        res = bgpbot.get_asname("not-an-asn", mock_bgp)
        self.assertEqual(res.type, "red")
        self.assertIn("not-an-asn is not a valid ASN", res.text)

    @patch('bgpstuff.Client')
    def test_valid_public_asn_handling(self, mock_client):
        mock_bgp = mock_client.return_value
        mock_bgp.get_as_name.return_value = {"as_name": "GOOGLE", "as_number": 15169}

        # AS15169 as string with prefix
        res = bgpbot.get_asname("AS15169", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual("The AS name for AS15169 is GOOGLE", res.text)
        mock_bgp.get_as_name.assert_called_with(15169)

    @patch('bgpstuff.Client')
    def test_valid_ip_handling(self, mock_client):
        mock_bgp = mock_client.return_value

        # Test route
        mock_bgp.get_route.return_value = {"routes": [{"prefix": "8.8.8.0/24"}]}
        res = bgpbot.get_route("8.8.8.8", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "The route for 8.8.8.8 is 8.8.8.0/24")

        # Test origin
        mock_bgp.get_origin.return_value = {"origin": 15169}
        res = bgpbot.get_origin("8.8.8.8", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "The origin AS for 8.8.8.8 is AS15169")

        # Test geoip
        mock_bgp.get_geoip.return_value = {"city": "Mountain View", "country": "United States"}
        res = bgpbot.get_geoip("8.8.8.8", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "8.8.8.8 might be located in Mountain View, United States")

        # Test aspath
        mock_bgp.get_as_path.return_value = {"as_path": [54054, 15169]}
        res = bgpbot.get_aspath("8.8.8.8", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "The AS path for 8.8.8.8 is 54054 15169")

        # Test roa
        mock_bgp.get_roa.return_value = {"roa": "valid"}
        res = bgpbot.get_roa("8.8.8.8", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "The ROA status for 8.8.8.8 is VALID")

        # Test sourced
        mock_bgp.get_sourced_prefixes.return_value = {"routes": [{"prefix": "8.8.8.0/24"}]}
        res = bgpbot.get_sourced("15169", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual(res.text, "AS15169 is sourcing the following prefixes:\n\t8.8.8.0/24")

    @patch('bgpstuff.Client')
    def test_nonexistent_handling(self, mock_client):
        mock_bgp = mock_client.return_value

        mock_bgp.get_route.return_value = {"routes": []}
        res = bgpbot.get_route("1.2.3.4", mock_bgp)
        self.assertEqual(res.type, "yellow")
        self.assertEqual(res.text, "No prefix exists for 1.2.3.4")

        mock_bgp.get_as_name.return_value = None
        res = bgpbot.get_asname("12345", mock_bgp)
        self.assertEqual(res.type, "yellow")
        self.assertEqual(res.text, "No AS name exists for AS12345")

    @patch('bgpstuff.Client')
    def test_invalids_handling(self, mock_client):
        mock_bgp = mock_client.return_value

        # originating invalids
        mock_bgp.get_invalids.return_value = [{"prefix": "1.2.3.0/24", "rpki": "invalid"}]
        res = bgpbot.get_invalids("15169", mock_bgp)
        self.assertEqual(res.type, "yellow")
        self.assertIn("1.2.3.0/24", res.text)

        # no invalids
        mock_bgp.get_invalids.return_value = []
        res = bgpbot.get_invalids("15170", mock_bgp)
        self.assertEqual(res.type, "green")
        self.assertEqual("AS15170 is not originating any invalid prefixes", res.text)

    @patch('bgpstuff.Client')
    def test_vrps_handling(self, mock_client):
        mock_bgp = mock_client.return_value
        mock_bgp.get_vrps.side_effect = NotImplementedError("VRPs are not supported in the v3 API.")
        res = bgpbot.get_vrps("15169", mock_bgp)
        self.assertEqual(res.type, "yellow")
        self.assertEqual("VRPs are not supported in the bgpstuff.net v3 API", res.text)


if __name__ == '__main__':
    unittest.main()
