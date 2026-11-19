# Calculated expected results

```json
{
  "inputs": {
    "sellers": 3095,
    "items": 3379,
    "orders": 3000
  },
  "outputs": {
    "seller_activity": 3095,
    "seller_geography": 23
  },
  "totals": {
    "distinct_orders": 3007,
    "item_rows": 3379,
    "delivered_orders": 2947,
    "canceled_orders": 11,
    "other_orders": 49,
    "on_time_items": 3022,
    "late_items": 321,
    "missing_handoff_items": 36,
    "merchandise_value": "390764.28"
  },
  "sample": [
    {
      "seller_id": "0015a82c2db000af6aaaf3ae2ecb0532",
      "seller_state": "SP",
      "distinct_orders": 1,
      "item_rows": 1,
      "merchandise_value": "895.00",
      "delivered_orders": 1,
      "canceled_orders": 0,
      "other_orders": 0,
      "on_time_items": 1,
      "late_items": 0,
      "missing_handoff_items": 0
    },
    {
      "seller_id": "001cca7ae9ae17fb1caed9dfb1094831",
      "seller_state": "ES",
      "distinct_orders": 6,
      "item_rows": 7,
      "merchandise_value": "839.00",
      "delivered_orders": 5,
      "canceled_orders": 0,
      "other_orders": 1,
      "on_time_items": 7,
      "late_items": 0,
      "missing_handoff_items": 0
    },
    {
      "seller_id": "001e6ad469a905060d959994f1b41e4f",
      "seller_state": "RJ",
      "distinct_orders": 0,
      "item_rows": 0,
      "merchandise_value": "0.00",
      "delivered_orders": 0,
      "canceled_orders": 0,
      "other_orders": 0,
      "on_time_items": 0,
      "late_items": 0,
      "missing_handoff_items": 0
    }
  ]
}
```

Full rows and schemas: expected-results.json. Distinct orders summed across sellers count seller-order pairs.

## Output columns

| Table | Column | Trino type |
|---|---|---|
| seller_activity | seller_id | varchar |
| seller_activity | seller_state | varchar |
| seller_activity | distinct_orders | bigint |
| seller_activity | item_rows | bigint |
| seller_activity | merchandise_value | decimal(28,2) |
| seller_activity | delivered_orders | bigint |
| seller_activity | canceled_orders | bigint |
| seller_activity | other_orders | bigint |
| seller_activity | on_time_items | bigint |
| seller_activity | late_items | bigint |
| seller_activity | missing_handoff_items | bigint |
| seller_geography | seller_state | varchar |
| seller_geography | seller_count | bigint |
| seller_geography | item_rows | bigint |
