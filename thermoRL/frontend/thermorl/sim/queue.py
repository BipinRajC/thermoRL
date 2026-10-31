from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueuedJob:
    job_id: str
    defer_count: int
    next_eligible_s: float


@dataclass
class JobQueue:
    max_deferrals: int = 3
    retry_delay_s: float = 40.0
    capacity: int = 256
    items: list[QueuedJob] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.items)

    def defer(self, item: QueuedJob, now_s: float) -> bool:
        if item.defer_count >= self.max_deferrals:
            return True
        item.defer_count += 1
        item.next_eligible_s = now_s + self.retry_delay_s
        if item not in self.items:
            if len(self.items) >= self.capacity:
                return True
            self.items.append(item)
        return False
