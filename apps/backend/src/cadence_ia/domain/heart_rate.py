"""Heart-rate metrics: work/rest segments and recovery."""

from dataclasses import dataclass, field

from cadence_ia.domain.activity import Activity, Trackpoint

SMOOTH_WINDOW_S = 15
# A set/rest must move HR by this fraction of the session's average HR,
# so detection adapts to each person and day instead of a fixed bpm value.
THRESHOLD_RATIO = 0.05
MIN_THRESHOLD_BPM = 4


@dataclass
class Segment:
    kind: str  # "work" (HR rising) or "rest" (HR falling)
    start_s: int
    end_s: int
    hr_start: int
    hr_end: int
    hr_avg: int
    drop_30s: int | None = None  # rest only: HR drop after 30 s
    drop_60s: int | None = None  # rest only: HR drop after 60 s

    @property
    def duration_s(self) -> int:
        return self.end_s - self.start_s


@dataclass
class WorkoutMetrics:
    duration_s: int
    hr_min: int
    hr_avg: int
    hr_max: int
    threshold_bpm: float
    segments: list[Segment] = field(default_factory=list)

    @property
    def sets(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "work"]

    @property
    def rests(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "rest"]


def curve(trackpoints: list[Trackpoint]) -> list[tuple[float, int]]:
    """The raw HR samples as (seconds since the first one, bpm), for charts."""
    points = [tp for tp in trackpoints if tp.heart_rate is not None]
    if not points:
        return []
    t0 = points[0].time
    return [((tp.time - t0).total_seconds(), tp.heart_rate) for tp in points]


def resample(trackpoints: list[Trackpoint]) -> list[float]:
    """HR once per second from the first trackpoint, linearly interpolated."""
    points = [tp for tp in trackpoints if tp.heart_rate is not None]
    if not points:
        raise ValueError("No heart-rate data")

    t0 = points[0].time
    xs = [(tp.time - t0).total_seconds() for tp in points]
    ys = [tp.heart_rate for tp in points]

    hr = []
    j = 0
    for t in range(int(xs[-1]) + 1):
        while j < len(xs) - 2 and xs[j + 1] < t:
            j += 1
        if j + 1 >= len(xs) or xs[j + 1] == xs[j]:
            hr.append(float(ys[j]))
        else:
            ratio = (t - xs[j]) / (xs[j + 1] - xs[j])
            hr.append(ys[j] + (ys[j + 1] - ys[j]) * ratio)
    return hr


def smooth(values: list[float], window: int) -> list[float]:
    """Centered moving average."""
    half = window // 2
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - half) : i + half + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def turning_points(values: list[float], threshold: float) -> list[tuple[int, str]]:
    """Alternating (index, "valley" | "peak") pairs at least `threshold` apart.
    A point is only confirmed once the signal moves back by `threshold`, so wiggles are ignored."""
    points: list[tuple[int, str]] = []
    direction = 0  # 1 rising, -1 falling, 0 not decided yet
    lo = hi = ext = 0

    for i, v in enumerate(values):
        if direction == 0:
            if v < values[lo]:
                lo = i
            if v > values[hi]:
                hi = i
            if values[hi] - values[lo] >= threshold:
                if lo < hi:
                    points.append((lo, "valley"))
                    direction, ext = 1, hi
                else:
                    points.append((hi, "peak"))
                    direction, ext = -1, lo
        elif direction == 1:
            if v > values[ext]:
                ext = i
            elif values[ext] - v >= threshold:
                points.append((ext, "peak"))
                direction, ext = -1, i
        else:
            if v < values[ext]:
                ext = i
            elif v - values[ext] >= threshold:
                points.append((ext, "valley"))
                direction, ext = 1, i
    return points


def auto_threshold(hr_avg: float) -> float:
    return max(MIN_THRESHOLD_BPM, hr_avg * THRESHOLD_RATIO)


def _drop_after(smoothed: list[float], start: int, end: int, seconds: int) -> int | None:
    if end - start < seconds:
        return None
    return round(smoothed[start] - smoothed[start + seconds])


def analyze(
    activity: Activity,
    smooth_window: int = SMOOTH_WINDOW_S,
    threshold: float | None = None,
) -> WorkoutMetrics:
    """Analyze an activity. `threshold` defaults to a share of the average HR."""
    hr = resample(activity.trackpoints)
    hr_avg = sum(hr) / len(hr)
    if threshold is None:
        threshold = auto_threshold(hr_avg)
    smoothed = smooth(hr, smooth_window)
    turns = turning_points(smoothed, threshold)

    segments = []
    for (start, kind), (end, _) in zip(turns, turns[1:]):
        chunk = hr[start : end + 1]
        segment = Segment(
            kind="work" if kind == "valley" else "rest",
            start_s=start,
            end_s=end,
            hr_start=round(smoothed[start]),
            hr_end=round(smoothed[end]),
            hr_avg=round(sum(chunk) / len(chunk)),
        )
        if segment.kind == "rest":
            segment.drop_30s = _drop_after(smoothed, start, end, 30)
            segment.drop_60s = _drop_after(smoothed, start, end, 60)
        segments.append(segment)

    raw = [tp.heart_rate for tp in activity.trackpoints if tp.heart_rate is not None]
    return WorkoutMetrics(
        duration_s=len(hr) - 1,
        hr_min=min(raw),
        hr_avg=round(hr_avg),
        hr_max=max(raw),
        threshold_bpm=round(threshold, 1),
        segments=segments,
    )
