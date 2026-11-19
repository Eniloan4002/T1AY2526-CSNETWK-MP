from game.draft import (
    create_resource_query,
    create_resource_offer,
    create_resource_buy
)

print("\n========== RESOURCE TRADING MESSAGE TESTS ==========")

query = create_resource_query("WOOD", 1)

offer = create_resource_offer("WOOD", 2, 2)

buy = create_resource_buy("WOOD", 1, 2)

print("RESOURCE_QUERY:", query)
print("RESOURCE_OFFER:", offer)
print("RESOURCE_BUY:", buy)

if query == {"resource": "WOOD", "qty": 1}:
    print("SUCCESS! RESOURCE_QUERY is correct.")

if offer == {
    "resource": "WOOD",
    "qty_available": 2,
    "price_per_unit": 2
}:
    print("SUCCESS! RESOURCE_OFFER is correct.")

if buy == {
    "resource": "WOOD",
    "qty": 1,
    "coins": 2
}:
    print("SUCCESS! RESOURCE_BUY is correct.")