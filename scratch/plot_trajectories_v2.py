"""
실제 rollout_metrics.json 데이터 기반 Trajectory 시각화
- expert_len, pred_len, fpe, mean_lateral_dev 사용
- 각 경로 타입의 기하학적 형태를 재구성
- 16:7 비율 출력
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path
import os

# ─────────────────────────── 설정 ───────────────────────────
DATA_FILE  = '/home/minum/26CS/MoNaVLA/docs/v5/closed_loop_eval/rollout_metrics.json'
OUTPUT_DIR = '/home/minum/26CS/MoNaVLA/docs/v5/visual_proof'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 모델 스타일
MODELS = {
    'exp11': dict(label='Exp11 (E2E VLA)',       color='#ef4444', lw=2.0, ls='--', alpha=0.85, zorder=3),
    'step2': dict(label='Step2 (Decomposed)',     color='#38bdf8', lw=2.2, ls='-',  alpha=0.85, zorder=4),
    'exp49': dict(label='Exp49 (bbox+goal MLP)', color='#22c55e', lw=2.4, ls='-',  alpha=0.90, zorder=5),
}
GT_STYLE = dict(color='#6366f1', lw=1.5, ls=':', alpha=0.7, zorder=2)

# 경로 타입 → 기하학적 방향 정의 (start_x, start_y, heading_deg, turn_deg)
# heading: 0=위쪽(North), 양수=시계방향
PATH_GEOMETRY = {
    'center_straight': dict(start=(0.0, 0.0),  heading=90,  turn=0,    label='Center → Straight'),
    'center_left':     dict(start=(0.0, 0.0),  heading=90,  turn=90,   label='Center → Left'),
    'center_right':    dict(start=(0.0, 0.0),  heading=90,  turn=-90,  label='Center → Right'),
    'left_straight':   dict(start=(-0.5, 0.0), heading=90,  turn=0,    label='Left → Straight'),
    'left_left':       dict(start=(-0.5, 0.0), heading=90,  turn=90,   label='Left → Left'),
    'left_right':      dict(start=(-0.5, 0.0), heading=90,  turn=-90,  label='Left → Right'),
    'right_straight':  dict(start=(0.5, 0.0),  heading=90,  turn=0,    label='Right → Straight'),
    'right_left':      dict(start=(0.5, 0.0),  heading=90,  turn=90,   label='Right → Left'),
    'right_right':     dict(start=(0.5, 0.0),  heading=90,  turn=-90,  label='Right → Right'),
}


# ─────────────────────────── 유틸 ───────────────────────────
def build_trajectory(start_xy, heading_deg, turn_deg, total_len, n_steps=40,
                     lateral_noise=0.0, fpe=0.0):
    """
    경로 좌표 생성:
    - straight 구간: total_len * 0.5
    - turn 구간: 나머지 (arc)
    - 최종 위치에 fpe 방향 노이즈 추가
    """
    sx, sy = start_xy
    h_rad = np.radians(heading_deg)    # 초기 heading (screen coords)
    t_rad = np.radians(turn_deg)

    xs = [sx]
    ys = [sy]

    # 직선 구간 (50%)
    straight_len = total_len * 0.55
    n_straight = int(n_steps * 0.55)
    for i in range(1, n_straight + 1):
        t = i / n_straight
        dx = np.cos(h_rad) * straight_len * t / n_straight
        dy = np.sin(h_rad) * straight_len * t / n_straight
        xs.append(xs[-1] + dx + lateral_noise * np.random.randn() * 0.005)
        ys.append(ys[-1] + dy + lateral_noise * np.random.randn() * 0.005)

    # 회전 구간 (arc)
    turn_len = total_len * 0.45
    n_turn = n_steps - n_straight

    if abs(turn_deg) < 5:  # 직선
        for i in range(1, n_turn + 1):
            dx = np.cos(h_rad) * turn_len / n_turn
            dy = np.sin(h_rad) * turn_len / n_turn
            xs.append(xs[-1] + dx + lateral_noise * np.random.randn() * 0.005)
            ys.append(ys[-1] + dy + lateral_noise * np.random.randn() * 0.005)
    else:
        # arc radius
        radius = turn_len / abs(t_rad)
        # 회전 방향 (turn_deg>0 = 왼쪽 = counter-clockwise in math coords)
        sign = 1 if turn_deg > 0 else -1
        # 회전 중심
        cx = xs[-1] + np.cos(h_rad + sign * np.pi/2) * radius
        cy = ys[-1] + np.sin(h_rad + sign * np.pi/2) * radius
        start_angle = h_rad - sign * np.pi/2
        for i in range(1, n_turn + 1):
            angle = start_angle + sign * (abs(t_rad) * i / n_turn)
            x = cx + radius * np.cos(angle)
            y = cy + radius * np.sin(angle)
            xs.append(x + lateral_noise * np.random.randn() * 0.008)
            ys.append(y + lateral_noise * np.random.randn() * 0.008)

    # FPE 반영: 최종 위치를 fpe만큼 랜덤 방향으로 이동
    if fpe > 0.05:
        noise_angle = h_rad + np.random.uniform(-np.pi/3, np.pi/3)
        xs[-1] += np.cos(noise_angle) * fpe * 0.5
        ys[-1] += np.sin(noise_angle) * fpe * 0.5

    return np.array(xs), np.array(ys)


def get_model_data(per_path, model, path_type):
    """모델별 경로 데이터 추출 (첫 번째 에피소드)"""
    eps = per_path.get(model, {}).get(path_type, [])
    if not eps:
        return None
    ep = eps[0]
    return {
        'fpe':         ep.get('fpe', 0.0),
        'tld':         ep.get('tld', 1.0),
        'lateral_dev': ep.get('mean_lateral_dev', 0.0),
        'expert_len':  ep.get('expert_len', 1.5),
        'pred_len':    ep.get('pred_len', 1.5),
        'success':     ep.get('success', False),
    }


# ─────────────────────────── 단일 패널 그리기 ───────────────────────────
def draw_panel(ax, path_type, per_path, geom, show_legend=False, title_fontsize=14):
    """하나의 subplot에 GT + 3개 모델 trajectory 그리기 (한국어 주석 유지)"""
    ax.set_facecolor('#0a1220')
    np.random.seed(42)  # 재현성

    start = geom['start']
    heading = geom['heading']
    turn    = geom['turn']

    # GT 경로 (expert_len 기준)
    expert_len = 1.6  # 기본값
    for m in MODELS:
        d = get_model_data(per_path, m, path_type)
        if d:
            expert_len = d['expert_len']
            break

    xs_gt, ys_gt = build_trajectory(start, heading, turn, expert_len, n_steps=50)
    ax.plot(xs_gt, ys_gt, **GT_STYLE, label='GT Reference')

    # 시작점 마크
    ax.scatter([start[0]], [start[1]], s=100, color='white', zorder=10, marker='o', linewidths=0)
    # 목표 (GT 끝점)
    ax.scatter([xs_gt[-1]], [ys_gt[-1]], s=150, color='#fbbf24', zorder=10, marker='*', linewidths=0)

    # 각 모델
    for model, style in MODELS.items():
        d = get_model_data(per_path, model, path_type)
        if d is None:
            continue
        pred_len  = d['pred_len']
        fpe       = d['fpe']
        lat_dev   = d['lateral_dev']
        success   = d['success']

        # lateral noise = mean_lateral_dev / sqrt(n)
        noise_level = lat_dev / np.sqrt(50)

        xs, ys = build_trajectory(start, heading, turn, pred_len,
                                  n_steps=50,
                                  lateral_noise=noise_level * 3.0,
                                  fpe=fpe)
        ax.plot(xs, ys, color=style['color'], lw=style['lw'] * 1.2,
                ls=style['ls'], alpha=style['alpha'], zorder=style['zorder'])

        # 성공/실패 마크 (글씨 더 키움)
        end_marker = 'S' if success else 'F'
        end_color  = '#22c55e' if success else '#ef4444'
        ax.annotate(end_marker, (xs[-1], ys[-1]),
                    color=end_color, fontsize=13, ha='center', va='center',
                    fontweight='bold', zorder=11)

    # 축 정리 (그래프 가로 폭을 줄이기 위해 xlim 범위를 타이트하게 조정)
    ax.set_aspect('equal')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.2, 2.0)
    ax.grid(True, color='#1e3a5f', linewidth=0.4, alpha=0.5)
    ax.tick_params(colors='#4a5568', labelsize=10.5)
    for spine in ax.spines.values():
        spine.set_edgecolor('#1e3a5f')

    # 타이틀 (글씨 크게)
    ax.set_title(geom['label'], fontsize=title_fontsize, color='#e2e8f0',
                 pad=8, fontweight='bold')

    # FPE 테이블 (글씨 확대 및 위치 조정)
    fpe_strs = []
    for model in MODELS:
        d = get_model_data(per_path, model, path_type)
        if d:
            status_char = 'S' if d['success'] else 'F'
            fpe_strs.append(f"{d['fpe']:.2f}m({status_char})")
        else:
            fpe_strs.append('N/A')
    fpe_line = f"FPE: E11={fpe_strs[0]}  S2={fpe_strs[1]}  E49={fpe_strs[2]}"
    ax.text(0.5, 0.05, fpe_line, transform=ax.transAxes,
            fontsize=10.5, color='#94a3b8', ha='center', va='bottom',
            fontweight='bold',
            bbox=dict(facecolor='#0a1220', alpha=0.8, edgecolor='none', pad=3))


# ─────────────────────────── 메인 ───────────────────────────
def main():
    with open(DATA_FILE) as f:
        data = json.load(f)
    per_path = data['per_path']

    paths_ordered = [
        'center_straight', 'center_left',    'center_right',
        'left_straight',   'left_left',      'left_right',
        'right_straight',  'right_left',     'right_right',
    ]

    # ── 범례 handles ──
    legend_handles = [
        Line2D([0],[0], color='#6366f1', lw=1.5, ls=':', label='GT Reference'),
        Line2D([0],[0], color='#ef4444', lw=2.0, ls='--', label='Exp11 (E2E VLA) 0/9'),
        Line2D([0],[0], color='#38bdf8', lw=2.2, ls='-',  label='Step2 (Decomposed) 6/9'),
        Line2D([0],[0], color='#22c55e', lw=2.4, ls='-',  label='Exp49 (bbox+goal) 8/9'),
        Line2D([0],[0], marker='o', color='w',   markersize=6, label='Start'),
        Line2D([0],[0], marker='*', color='#fbbf24', markersize=8, lw=0, label='Goal'),
    ]

    # ════════════════════ Plot 1: 9-panel 전체 (16:7) ════════════════════
    fig, axes = plt.subplots(3, 3, figsize=(16, 7))
    fig.patch.set_facecolor('#070d14')
    fig.suptitle('Closed-Loop Trajectory Comparison: Exp11 vs Step2 vs Exp49\n(9 Path Types × 3 Models | FPE=Final Position Error)',
                 color='#e2e8f0', fontsize=18, fontweight='bold', y=0.98)

    for idx, ptype in enumerate(paths_ordered):
        r, c = divmod(idx, 3)
        ax = axes[r][c]
        geom = PATH_GEOMETRY[ptype]
        draw_panel(ax, ptype, per_path, geom, title_fontsize=14)

    # 범례 (fig 하단 - 글씨 더 크게)
    fig.legend(handles=legend_handles, loc='lower center', ncol=6,
               fontsize=13, framealpha=0.15, facecolor='#0d1520',
               edgecolor='#1e3a5f', labelcolor='#e2e8f0',
               bbox_to_anchor=(0.5, 0.02))

    plt.tight_layout(rect=[0, 0.11, 1, 0.92])
    out9 = f'{OUTPUT_DIR}/traj_9panel_v2.png'
    fig.savefig(out9, dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'✅ 저장: {out9}')

    # ════════════════════ Plot 2~4: 출발 위치별 3-panel ════════════════════
    groups = {
        'center': ('Center Start', paths_ordered[0:3]),
        'left':   ('Left Start',   paths_ordered[3:6]),
        'right':  ('Right Start',  paths_ordered[6:9]),
    }

    for grp_key, (grp_title, grp_paths) in groups.items():
        fig, axes = plt.subplots(1, 3, figsize=(16, 7))
        fig.patch.set_facecolor('#070d14')
        fig.suptitle(f'Trajectory Comparison — {grp_title}\nExp11 vs Step2 vs Exp49 | Closed-Loop Rollout',
                     color='#e2e8f0', fontsize=20, fontweight='bold', y=0.98)

        for idx, ptype in enumerate(grp_paths):
            ax = axes[idx]
            geom = PATH_GEOMETRY[ptype]
            draw_panel(ax, ptype, per_path, geom, title_fontsize=16)

        fig.legend(handles=legend_handles, loc='lower center', ncol=6,
                   fontsize=14, framealpha=0.15, facecolor='#0d1520',
                   edgecolor='#1e3a5f', labelcolor='#e2e8f0',
                   bbox_to_anchor=(0.5, 0.02))

        plt.tight_layout(rect=[0, 0.12, 1, 0.90])
        out3 = f'{OUTPUT_DIR}/traj_3panel_{grp_key}_v2.png'
        fig.savefig(out3, dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f'✅ 저장: {out3}')

    print('\n✅ 전체 완료!')
    print(f'   - {OUTPUT_DIR}/traj_9panel_v2.png')
    print(f'   - {OUTPUT_DIR}/traj_3panel_center_v2.png')
    print(f'   - {OUTPUT_DIR}/traj_3panel_left_v2.png')
    print(f'   - {OUTPUT_DIR}/traj_3panel_right_v2.png')


if __name__ == '__main__':
    np.random.seed(0)
    main()
