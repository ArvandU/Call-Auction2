def double_auction_uniform_price(bids, asks):
    """
    Implements a call auction clearing mechanism:
    
    1. Sort bids in descending order by price; if prices are equal, sort by ascending quantity.
    2. Sort asks in ascending order by price; if prices are equal, sort by ascending quantity.
    3. If the highest bid is lower than the lowest ask, no trade occurs (return 0, 0).
    4. Otherwise, match bids and asks sequentially:
         - For each pair (bid, ask) meeting bid_price >= ask_price, clear trade for the minimum quantity.
         - Reduce quantities accordingly and move to the next bid/ask when one is exhausted.
         - Continue until the condition fails.
    5. The uniform price is defined as the average of the last cleared bid and ask prices.
    
    Returns:
       uniform_price (float) and total traded quantity (int).
    """
    if not bids or not asks:
        return 0, 0

    sorted_bids = [list(b) for b in bids]
    sorted_asks = [list(a) for a in asks]
    
    sorted_bids.sort(key=lambda x: (-x[0], x[1]))
    sorted_asks.sort(key=lambda x: (x[0], x[1]))
    
    if sorted_bids[0][0] < sorted_asks[0][0]:
        return 0, 0

    traded_quantity = 0
    i = 0
    j = 0
    last_bid_price = 0
    last_ask_price = 0

    while i < len(sorted_bids) and j < len(sorted_asks):
        bid_price, bid_qty = sorted_bids[i]
        ask_price, ask_qty = sorted_asks[j]
        if bid_price < ask_price:
            break
        trade_qty = min(bid_qty, ask_qty)
        traded_quantity += trade_qty
        last_bid_price = bid_price
        last_ask_price = ask_price
        sorted_bids[i][1] -= trade_qty
        sorted_asks[j][1] -= trade_qty
        if sorted_bids[i][1] == 0:
            i += 1
        if sorted_asks[j][1] == 0:
            j += 1

    if traded_quantity == 0:
        return 0, 0
    uniform_price = (last_bid_price + last_ask_price) / 2
    return uniform_price, traded_quantity
