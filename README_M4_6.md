# M4.6.1 Interval Aggregator Test Patch

Strengthens the concurrency regression test for the approved `IntervalAggregator`.

The test now forces a genuine asynchronous interleaving during a 30-minute interval transition by blocking the summary handler while a second observation for the same beacon arrives. It verifies that no observation is lost.

`tools/review_milestones.json` is the single canonical milestone configuration and includes M4.5 and M4.6 directly.
