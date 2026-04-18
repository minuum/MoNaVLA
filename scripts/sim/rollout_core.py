"""
Closed-loop kinematic simulation core.
No model loading — pure trajectory math + metrics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

# discrete class → [lx, ly, az]   (lx/ly m/s, az rad/s)
# from dataset: lx=1.15, ly=±1.15, az=±0.25
ACTION_VEL = {
    0: (0.0,    0.0,   0.0),    # STOP
    1: (1.15,   0.0,   0.0),    # FORWARD
    2: (0.0,    1.15,  0.0),    # LEFT  (strafe)
    3: (0.0,   -1.15,  0.0),    # RIGHT (strafe)
    4: (1.15,   1.15,  0.0),    # FWD+L
    5: (1.15,  -1.15,  0.0),    # FWD+R
    6: (0.0,    0.0,   0.25),   # ROT_L
    7: (0.0,    0.0,  -0.25),   # ROT_R
}
CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
DT_DEFAULT = 0.1  # seconds per frame


@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0


@dataclass
class Trajectory:
    poses: List[Pose] = field(default_factory=list)
    actions: List[int] = field(default_factory=list)

    def append(self, pose: Pose, action: int):
        self.poses.append(pose)
        self.actions.append(action)

    def total_length(self) -> float:
        total = 0.0
        for i in range(1, len(self.poses)):
            dx = self.poses[i].x - self.poses[i-1].x
            dy = self.poses[i].y - self.poses[i-1].y
            total += math.sqrt(dx*dx + dy*dy)
        return total

    def final_pos(self) -> Tuple[float, float]:
        if not self.poses:
            return (0.0, 0.0)
        return (self.poses[-1].x, self.poses[-1].y)


def pose_step(pose: Pose, lx: float, ly: float, az: float, dt: float = DT_DEFAULT) -> Pose:
    """Body-frame velocity → world-frame pose update."""
    ct, st = math.cos(pose.theta), math.sin(pose.theta)
    return Pose(
        x=pose.x + (lx * ct - ly * st) * dt,
        y=pose.y + (lx * st + ly * ct) * dt,
        theta=pose.theta + az * dt,
    )


def build_trajectory(action_seq: List[int], dt: float = DT_DEFAULT) -> Trajectory:
    traj = Trajectory()
    pose = Pose()
    for cls in action_seq:
        lx, ly, az = ACTION_VEL.get(cls, (0.0, 0.0, 0.0))
        traj.append(pose, cls)
        pose = pose_step(pose, lx, ly, az, dt)
    traj.append(pose, -1)  # final pose (after last action)
    return traj


def continuous_to_class(lx: float, ly: float, az: float) -> int:
    """Map continuous expert action [lx, ly, az] to nearest discrete class."""
    is_fwd = lx > 0.5
    is_left = ly > 0.5
    is_right = ly < -0.5
    is_rot_l = az > 0.1
    is_rot_r = az < -0.1
    if not is_fwd and not is_left and not is_right:
        if is_rot_l: return 6
        if is_rot_r: return 7
        return 0
    if is_fwd and is_left: return 4
    if is_fwd and is_right: return 5
    if is_fwd: return 1
    if is_left: return 2
    if is_right: return 3
    return 0


def compute_metrics(expert: Trajectory, pred: Trajectory, success_fpe: float = 0.5) -> dict:
    expert_final = np.array(expert.final_pos())
    pred_final = np.array(pred.final_pos())
    fpe = float(np.linalg.norm(pred_final - expert_final))

    expert_len = expert.total_length()
    pred_len = pred.total_length()
    tld = pred_len / max(expert_len, 1e-6)

    # Mean lateral deviation: perpendicular distance to expert heading at each step
    deviations = []
    for i, pose in enumerate(pred.poses):
        if i < len(expert.poses):
            ep = expert.poses[i]
            dx, dy = pose.x - ep.x, pose.y - ep.y
            deviations.append(math.sqrt(dx*dx + dy*dy))
    mean_dev = float(np.mean(deviations)) if deviations else 0.0

    success = (fpe < success_fpe) and (0.7 <= tld <= 1.5)

    return {
        "fpe": fpe,
        "tld": float(tld),
        "mean_lateral_dev": mean_dev,
        "expert_len": float(expert_len),
        "pred_len": float(pred_len),
        "success": bool(success),
        "expert_n_frames": len(expert.poses),
        "pred_n_frames": len(pred.poses),
    }
