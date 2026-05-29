"""
tracker.py — ByteTrack-style multi-object tracker with Re-ID.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np


@dataclass
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def cx(self):
        return (self.x1 + self.x2) / 2

    @property
    def cy(self):
        return (self.y1 + self.y2) / 2

    @property
    def area(self):
        return max(0, self.x2 - self.x1) * max(0, self.y2 - self.y1)

    def iou(self, other: 'BBox') -> float:
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0


@dataclass
class Track:
    track_id: int
    visitor_id: str
    bbox: BBox
    confidence: float
    is_staff: bool
    last_seen: int
    appearance: Optional[np.ndarray] = None
    trajectory: list = field(default_factory=list)
    missed: int = 0
    active: bool = True


def make_visitor_id(track_id: int, store_id: str) -> str:
    raw = f"{store_id}_{track_id}"
    return "VIS_" + hashlib.sha1(raw.encode()).hexdigest()[:6]


def extract_appearance(frame: np.ndarray, bbox: BBox) -> np.ndarray:
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(bbox.x1)), max(0, int(bbox.y1))
    x2, y2 = min(w, int(bbox.x2)), min(h, int(bbox.y2))
    ch = y2 - y1
    if ch < 10 or (x2 - x1) < 10:
        return np.zeros(96, dtype=np.float32)
    crop = frame[y1 + ch // 2:y2, x1:x2]
    if crop.size == 0:
        return np.zeros(96, dtype=np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h_ = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
    s_ = cv2.calcHist([hsv], [1], None, [32], [0, 256]).flatten()
    v_ = cv2.calcHist([hsv], [2], None, [32], [0, 256]).flatten()
    feat = np.concatenate([h_, s_, v_])
    n = np.linalg.norm(feat)
    return feat / n if n > 0 else feat


def cosine_sim(a, b) -> float:
    if a is None or b is None:
        return 0.0
    return float(np.clip(np.dot(a, b), 0, 1))


STAFF_HUE_RANGES = [(100, 130), (0, 10), (170, 180)]


def classify_staff(frame: np.ndarray, bbox: BBox) -> tuple[bool, float]:
    h, w = frame.shape[:2]
    x1 = max(0, int(bbox.x1))
    y1 = max(0, int(bbox.y1))
    x2 = min(w, int(bbox.x2))
    y2 = min(h, int(bbox.y2))
    ch = y2 - y1
    if ch < 10 or (x2 - x1) < 10:
        return False, 0.5
    upper = frame[y1:y1 + ch // 3, x1:x2]
    if upper.size == 0:
        return False, 0.5
    hsv = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
    total = hsv.shape[0] * hsv.shape[1] or 1
    uniform = sum(
        int(np.sum(cv2.inRange(hsv, (lo, 80, 80), (hi, 255, 255)) > 0))
        for lo, hi in STAFF_HUE_RANGES
    )
    ratio = uniform / total
    return ratio > 0.55, round(min(0.95, 0.5 + ratio), 3)


class ByteTracker:
    IOU_HIGH = 0.45
    IOU_LOW = 0.20
    MAX_LOST = 30
    RE_ID_THRESH = 0.82
    RE_ENTRY_WIN = 120

    def __init__(self, store_id: str):
        self.store_id = store_id
        self._next = 1
        self.active: dict[int, Track] = {}
        self.lost: dict[int, Track] = {}
        self.gallery: list[tuple[str, np.ndarray, float]] = []
        self.frame = 0

    def update(self, dets: list[dict], frame: np.ndarray, t: float) -> list[Track]:
        self.frame += 1
        bboxes = [BBox(**d["bbox"]) for d in dets]
        confs = [d["confidence"] for d in dets]
        apps = [d.get("appearance") for d in dets]
        staffs = [d.get("is_staff", False) for d in dets]

        hi = [i for i, c in enumerate(confs) if c >= 0.5]
        lo = [i for i, c in enumerate(confs) if c < 0.5]

        mt, md, ut, ud = self._match(list(self.active), hi, bboxes, self.IOU_HIGH)
        for tid, did in zip(mt, md):
            self._upd(tid, bboxes[did], confs[did], staffs[did], apps[did], t)

        lt, ld, _, _ = self._match(ut + list(self.lost), lo, bboxes, self.IOU_LOW)
        for tid, did in zip(lt, ld):
            self._upd(tid, bboxes[did], confs[did], staffs[did], apps[did], t, recover=True)

        for did in ud:
            if confs[did] >= 0.6:
                self._spawn(bboxes[did], confs[did], staffs[did], apps[did], t)

        for tid in list(self.active):
            if tid not in mt:
                self.active[tid].missed += 1
                if self.active[tid].missed > self.MAX_LOST:
                    self._finalise(tid, t)

        return list(self.active.values())

    def check_reentry(self, app: np.ndarray, t: float) -> Optional[str]:
        self.gallery = [(v, a, ts) for v, a, ts in self.gallery if t - ts < self.RE_ENTRY_WIN]
        best, best_v = self.RE_ID_THRESH, None
        for vid, a, _ in self.gallery:
            s = cosine_sim(app, a)
            if s > best:
                best, best_v = s, vid
        return best_v

    def _match(self, tids, dids, bboxes, thr):
        if not tids or not dids:
            return [], [], tids[:], dids[:]
        all_ = {**self.active, **self.lost}
        from scipy.optimize import linear_sum_assignment
        C = np.array([[1 - all_[t].bbox.iou(bboxes[d]) for d in dids] for t in tids])
        ri, ci = linear_sum_assignment(C)
        mt, md, ut_, ud_ = [], [], [], []
        matched_t, matched_d = set(), set()
        for r, c in zip(ri, ci):
            if C[r, c] < 1 - thr:
                mt.append(tids[r])
                md.append(dids[c])
                matched_t.add(r)
                matched_d.add(c)
        for i, t in enumerate(tids):
            if i not in matched_t:
                ut_.append(t)
        for j, d in enumerate(dids):
            if j not in matched_d:
                ud_.append(d)
        return mt, md, ut_, ud_

    def _upd(self, tid, bbox, conf, staff, app, t, recover=False):
        src = self.lost if (recover and tid in self.lost) else self.active
        tr = src[tid]
        tr.bbox = bbox
        tr.confidence = conf
        tr.is_staff = staff
        if app is not None:
            tr.appearance = app
        tr.trajectory.append((bbox.cx, bbox.cy))
        tr.last_seen = self.frame
        tr.missed = 0
        if recover:
            self.active[tid] = tr
            self.lost.pop(tid, None)

    def _spawn(self, bbox, conf, staff, app, t) -> Track:
        tid = self._next
        self._next += 1
        tr = Track(
            track_id=tid,
            visitor_id=make_visitor_id(tid, self.store_id),
            bbox=bbox,
            confidence=conf,
            is_staff=staff,
            last_seen=self.frame,
            appearance=app,
            trajectory=[(bbox.cx, bbox.cy)],
        )
        self.active[tid] = tr
        return tr

    def _finalise(self, tid, t):
        tr = self.active.pop(tid)
        tr.active = False
        if tr.appearance is not None:
            self.gallery.append((tr.visitor_id, tr.appearance, t))
            if len(self.gallery) > 200:
                self.gallery.pop(0)
        self.lost[tid] = tr


class DirectionClassifier:
    def __init__(self, line: float = 0.5, axis: str = "y", min_pts: int = 8):
        self.line = line
        self.axis = axis
        self.min_pts = min_pts

    def classify(self, track: Track, fh: int, fw: int) -> Optional[str]:
        traj = track.trajectory
        if len(traj) < self.min_pts:
            return None
        n = len(traj)
        early = traj[:n // 3]
        late = traj[2 * n // 3:]
        dim = fh if self.axis == "y" else fw
        idx = 1 if self.axis == "y" else 0
        ep = np.mean([p[idx] for p in early]) / dim
        lp = np.mean([p[idx] for p in late]) / dim
        if not ((ep < self.line < lp) or (ep > self.line > lp)):
            return None
        return "ENTRY" if lp > ep else "EXIT"
