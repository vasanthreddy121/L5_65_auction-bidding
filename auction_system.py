"""Online auction demo with validation and safer rendering."""

import json
import math
import time
from datetime import datetime

from jinja2 import Environment
from markupsafe import escape

MIN_INCREMENT = 100


class Auction:
    """Represent a single auction item and its bid history."""

    def __init__(self, item_id, title, seller, reserve_price, ends_at):
        self.item_id = item_id
        self.title = title
        self.seller = seller
        self.reserve_price = reserve_price
        self.ends_at = self._parse_datetime(ends_at)
        self.bids = []
        self.leading_bid = None

    @property
    def highest_bid(self):
        """Return the latest accepted leading bid amount, or zero."""
        if self.leading_bid is None:
            return 0
        return self.leading_bid[1]

    @property
    def leader(self):
        """Return the bidder attached to the latest accepted leading bid."""
        if self.leading_bid is None:
            return None
        return self.leading_bid[0]

    @staticmethod
    def _parse_datetime(value):
        """Parse a datetime passed as a string or object."""
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise TypeError("Timestamp must be a string or datetime object")
        return datetime.strptime(value, "%Y-%m-%d %H:%M")

    def place_bid(self, bidder, amount, at):
        """Record a valid bid, including bids that have not met the reserve."""
        if not isinstance(bidder, str) or not bidder.strip():
            raise ValueError("Bidder must be a non-empty string")

        if bidder == self.seller:
            raise ValueError("Seller cannot bid on own auction")

        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("Bid amount must be a positive finite number")
        try:
            finite_amount = math.isfinite(amount)
        except OverflowError:
            finite_amount = False
        if not finite_amount or amount <= 0:
            raise ValueError("Bid amount must be a positive finite number")

        bid_time = self._parse_datetime(at)
        if bid_time > self.ends_at:
            raise ValueError("Auction closed")

        if self.highest_bid and amount < self.highest_bid + MIN_INCREMENT:
            raise ValueError(
                "Bid must exceed the current highest bid by the "
                "minimum increment"
            )

        self.leading_bid = (bidder, amount, bid_time)
        self.bids.append(self.leading_bid)
        return True

    def winner(self):
        """Return the current winning bidder, if the reserve is met."""
        if not self.bids or self.highest_bid < self.reserve_price:
            return None
        return self.leader

    def final_price(self):
        """Return the final price with buyer's premium, if sold."""
        if self.winner() is None:
            return 0
        return round(self.highest_bid * 1.05, 2)


auctions = {}


def create_auction(item_id, title, seller, reserve_price, ends_at):
    """Create and store a new auction instance."""
    auctions[item_id] = Auction(item_id, title, seller, reserve_price, ends_at)
    return auctions[item_id]


def bid(item_id, bidder, amount, at):
    """Submit a bid while converting invalid actions into False."""
    try:
        return auctions[item_id].place_bid(bidder, amount, at)
    except (KeyError, TypeError, ValueError):
        return False


def top_bidders(item_id, n=3):
    """Return the unique top bidder names in descending bid order."""
    try:
        auction = auctions[item_id]
    except (KeyError, TypeError):
        return []
    if not isinstance(n, int) or n <= 0:
        return []
    ordered = sorted(
        auction.bids,
        key=lambda bid_info: bid_info[1],
        reverse=True,
    )
    names = []
    for bidder, _, _ in ordered:
        if bidder not in names:
            names.append(bidder)
    return names[:n]


def render_listing(item_id):
    """Render the auction listing with Jinja2 HTML escaping enabled."""
    try:
        auction = auctions[item_id]
    except (KeyError, TypeError):
        return ""
    env = Environment(autoescape=True)
    template = env.from_string(
        "<h2>{{ a.title }}</h2><p>Current bid: Rs.{{ a.highest_bid }}</p>"
    )
    return template.render(a=auction)


def bidder_badge(name):
    """Return a safe bidder badge string."""
    safe_name = escape(str(name))
    return f"<span class='bidder'>{safe_name}</span>"


def charge_winner(item_id):
    """Simulate a winner payment demonstration without contacting a gateway."""
    try:
        auction = auctions[item_id]
    except (KeyError, TypeError):
        return False
    winner = auction.winner()
    if winner is None:
        return False
    return {
        "winner": winner,
        "amount": auction.final_price(),
        "status": "simulated",
        "message": "No payment was processed.",
    }


def export_bids(item_id):
    """Export bids as JSON."""
    try:
        auction = auctions[item_id]
    except (KeyError, TypeError):
        return json.dumps([])
    rows = [
        {
            "bidder": bidder,
            "amount": amount,
            "at": bid_time.strftime("%Y-%m-%d %H:%M"),
        }
        for bidder, amount, bid_time in auction.bids
    ]
    return json.dumps(rows)


def seconds_left(item_id):
    """Return the remaining time in seconds for the auction."""
    try:
        auction = auctions[item_id]
    except (KeyError, TypeError):
        return 0
    end = auction.ends_at
    return int(end.timestamp() - time.time())


def main():
    """Run a short demonstration of the auction rules."""
    create_auction(
        "LOT1",
        "Vintage Camera",
        "seller_sam",
        5000,
        "2026-12-01 18:00",
    )
    create_auction(
        "LOT2",
        "<script>alert('pwned')</script>Old Radio",
        "seller_ria",
        2000,
        "2026-12-01 18:00",
    )
    create_auction(
        "LOT3",
        "Brass Lamp",
        "seller_ria",
        800,
        "2026-12-01 18:00",
    )

    print("Asha bids 3000:", bid("LOT1", "asha", 3000, "2026-12-01 08:00"))
    print("Ben bids 3000 (same amount):",
          bid("LOT1", "ben", 3000, "2026-12-01 08:05"))
    print("Asha bids 3050 (+50):",
          bid("LOT1", "asha", 3050, "2026-12-01 08:10"))
    print("Seller bids on own item:",
          bid("LOT1", "seller_sam", 4000, "2026-12-01 09:00"))
    print("Bid at 9:30 AM (before 18:00 close):",
          bid("LOT1", "dev", 4500, "2026-12-01 9:30"))
    print("Late bid (next day):",
          bid("LOT1", "eve", 9000, "2026-12-02 09:00"))
    print("Winner:", auctions["LOT1"].winner())
    print("Final price (reserve 5000):", auctions["LOT1"].final_price())
    print("Top bidders:", top_bidders("LOT1"))
    print("Rs.0 bid on LOT3 (reserve 800):",
          bid("LOT3", "carl", 0, "2026-12-01 11:30"))
    print("LOT3 winner:", auctions["LOT3"].winner())
    print("No-bid winner:", auctions["LOT2"].winner())
    print("Listing HTML:", render_listing("LOT2"))
    print("Badge:", bidder_badge("<img src=x onerror=alert(1)>"))


if __name__ == "__main__":
    main()
