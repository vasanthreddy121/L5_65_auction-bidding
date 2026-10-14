"""Regression tests for auction bid validation and output escaping."""

import unittest

import auction_system
from auction_system import (
    bidder_badge,
    bid,
    create_auction,
    render_listing,
    top_bidders,
)


class AuctionBiddingTests(unittest.TestCase):
    """Exercise bid validation, sale outcomes, and escaped output."""

    def setUp(self):
        auction_system.auctions.clear()
        self.auction = create_auction(
            "LOT",
            "Test item",
            "seller",
            5000,
            "2026-12-01 18:00",
        )

    def test_first_bid_below_reserve_is_recorded_but_not_a_sale(self):
        """A valid bid can be below reserve without completing a sale."""
        self.assertTrue(bid("LOT", "asha", 3000, "2026-12-01 10:00"))
        self.assertEqual(self.auction.bids[0][0:2], ("asha", 3000))
        self.assertIsNone(self.auction.winner())
        self.assertEqual(self.auction.final_price(), 0)

    def test_bid_at_or_above_reserve_can_complete_sale(self):
        """Meeting the reserve makes an accepted bid eligible to win."""
        self.assertTrue(bid("LOT", "asha", 5000, "2026-12-01 10:00"))
        self.assertEqual(self.auction.winner(), "asha")
        self.assertEqual(self.auction.final_price(), 5250)

    def test_subsequent_bid_must_meet_minimum_increment(self):
        """Equal and sub-increment bids are rejected."""
        self.assertTrue(bid("LOT", "asha", 3000, "2026-12-01 10:00"))
        self.assertFalse(bid("LOT", "ben", 3000, "2026-12-01 10:05"))
        self.assertFalse(bid("LOT", "ben", 3050, "2026-12-01 10:05"))
        self.assertTrue(bid("LOT", "ben", 3100, "2026-12-01 10:05"))
        self.assertIsNone(self.auction.winner())
        self.assertTrue(
            bid("LOT", "carl", 5100, "2026-12-01 10:06")
        )
        self.assertEqual(self.auction.winner(), "carl")

    def test_seller_cannot_bid_on_own_auction(self):
        """The seller cannot create a bid or become the winner."""
        self.assertFalse(bid("LOT", "seller", 5000, "2026-12-01 10:00"))
        self.assertEqual(self.auction.bids, [])

    def test_zero_and_negative_bids_are_rejected(self):
        """Only positive bid amounts can be recorded."""
        self.assertFalse(bid("LOT", "asha", 0, "2026-12-01 10:00"))
        self.assertFalse(bid("LOT", "asha", -1, "2026-12-01 10:00"))
        self.assertEqual(self.auction.bids, [])

    def test_bid_before_close_is_accepted_and_late_bid_is_rejected(self):
        """A valid pre-close timestamp is accepted and a late one is not."""
        self.assertTrue(bid("LOT", "asha", 4500, "2026-12-01 9:30"))
        self.assertFalse(bid("LOT", "ben", 5000, "2026-12-02 09:00"))
        self.assertEqual(self.auction.bids[0][0], "asha")

    def test_bid_at_closing_time_is_accepted(self):
        """The auction remains open through its exact closing instant."""
        self.assertTrue(bid("LOT", "asha", 5000, "2026-12-01 18:00"))

    def test_malformed_timestamp_is_rejected(self):
        """Unparseable bid times are rejected without modifying bid history."""
        self.assertFalse(bid("LOT", "asha", 5000, "not-a-timestamp"))
        self.assertEqual(self.auction.bids, [])

    def test_empty_auction_has_no_winner_or_sale(self):
        """An auction with no bids remains unsold and has no ranking."""
        self.assertIsNone(self.auction.winner())
        self.assertEqual(self.auction.final_price(), 0)
        self.assertEqual(top_bidders("LOT"), [])

    def test_rankings_include_only_accepted_bids_in_bid_order(self):
        """Rejected bids do not appear in bidder rankings."""
        self.assertTrue(bid("LOT", "asha", 3000, "2026-12-01 10:00"))
        self.assertFalse(bid("LOT", "ben", 3050, "2026-12-01 10:05"))
        self.assertTrue(bid("LOT", "ben", 3100, "2026-12-01 10:05"))
        self.assertEqual(top_bidders("LOT"), ["ben", "asha"])

    def test_listing_and_badge_escape_untrusted_html(self):
        """Untrusted title and bidder data are rendered as escaped text."""
        self.auction.title = "<script>alert(1)</script>"
        listing = render_listing("LOT")
        badge = bidder_badge("<img src=x onerror=alert(1)>")
        self.assertIn("&lt;script&gt;", listing)
        self.assertNotIn("<script>", listing)
        self.assertIn("&lt;img", badge)
        self.assertNotIn("<img", badge)


if __name__ == "__main__":
    unittest.main()
