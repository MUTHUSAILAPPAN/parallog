"""
Reservoir sampling helper used to approximate latency percentiles.

Storing every individual response-time value would defeat the purpose
of map-reduce (partial results would grow without bound as chunks are
merged). Instead, each mapper keeps a fixed-capacity random sample of
the values it has seen; reducers merge two samples into one that is
still (approximately) a fair sample of the combined stream. Percentiles
computed from the merged sample approximate the true percentiles of
the full dataset -- a standard and well-known trade-off in streaming
/ distributed analytics systems.
"""

import random


class ReservoirSample:
    def __init__(self, capacity=1000, values=None, seen=0):
        self.capacity = capacity
        self.values = list(values) if values else []
        self.seen = seen  # total number of values ever offered

    def add(self, value):
        self.seen += 1
        if len(self.values) < self.capacity:
            self.values.append(value)
        else:
            j = random.randint(0, self.seen - 1)
            if j < self.capacity:
                self.values[j] = value

    def merge(self, other):
        combined = self.values + other.values
        total_seen = self.seen + other.seen
        if len(combined) <= self.capacity:
            sample = combined
        else:
            sample = random.sample(combined, self.capacity)
        return ReservoirSample(self.capacity, sample, total_seen)

    def to_dict(self):
        return {"capacity": self.capacity, "values": self.values, "seen": self.seen}

    @classmethod
    def from_dict(cls, d):
        return cls(d["capacity"], d["values"], d["seen"])


def percentile(sorted_values, pct):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1
