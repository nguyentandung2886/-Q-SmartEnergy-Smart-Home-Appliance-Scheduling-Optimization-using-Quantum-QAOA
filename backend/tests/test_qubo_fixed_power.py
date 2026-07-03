"""Bug #5 fix: H_power của QUBO phải cộng dồn tải NỀN CỐ ĐỊNH (fixed appliances đang bật
theo usage_windows) khi xét ngưỡng quá tải — không chỉ xét cặp hai thiết bị LINH HOẠT.

Một thiết bị linh hoạt xếp vào giờ mà tải cố định đã bật sẵn, nếu (công suất linh hoạt +
tải cố định tại giờ đó) > power_threshold_w thì QUBO phải phạt (H_power > 0) — và optimizer
phải né giờ đó khi còn lựa chọn hợp lệ khác.
"""
import numpy as np

from api.optimize_router import _fixed_load_w_by_hour
from core.data_prep import build_daily_profile
from core.qubo_builder import Appliance, build_qubo
from core.quantum_runner import QuantumScheduler


def test_hpower_penalizes_flexible_when_fixed_background_pushes_over_threshold():
    """Thiết bị linh hoạt 3000W, giờ ứng viên 10 & 14, ngưỡng 5000W. Tải nền cố định 3000W
    chỉ bật tại giờ 10 -> 3000+3000=6000 > 5000 -> biến (X,10) bị phạt trên ĐƯỜNG CHÉO;
    giờ 14 (3000+0) không bị phạt."""
    profile = build_daily_profile()
    app = Appliance(name="X", power_w=3000, duration_hours=1, candidate_hours=(10, 14))
    fixed_load_w = {h: 0.0 for h in range(24)}
    fixed_load_w[10] = 3000.0

    # lambda_onehot=0 để đường chéo không bị dịch -1e6, cô lập số hạng H_power.
    Q, var_map = build_qubo([app], profile, fixed_load_w=fixed_load_w, lambda_onehot=0.0)
    inv = {v: k for k, v in var_map.items()}
    j10 = inv[("X", 10)]
    j14 = inv[("X", 14)]

    assert Q[j10, j10] >= 1_000_000.0
    assert Q[j14, j14] < 1_000_000.0


def test_hpower_without_fixed_load_leaves_single_var_unpenalized():
    """Không truyền fixed_load_w (mặc định): một thiết bị dưới ngưỡng KHÔNG bị phạt đường chéo
    — giữ nguyên hành vi cũ của H_power (chỉ phạt cặp thiết bị linh hoạt)."""
    profile = build_daily_profile()
    app = Appliance(name="X", power_w=3000, duration_hours=1, candidate_hours=(10, 14))
    Q, var_map = build_qubo([app], profile, lambda_onehot=0.0)
    inv = {v: k for k, v in var_map.items()}
    assert Q[inv[("X", 10)], inv[("X", 10)]] < 1_000_000.0
    assert Q[inv[("X", 14)], inv[("X", 14)]] < 1_000_000.0


def test_hpower_pair_check_includes_fixed_background():
    """Hai thiết bị linh hoạt 2000W cùng chạy giờ 10, riêng chúng 4000W < 5000W (không bị
    phạt nếu bỏ qua tải nền). Thêm tải nền 2000W tại giờ 10 -> 6000W > 5000W -> cặp phải bị
    phạt trên off-diagonal."""
    profile = build_daily_profile()
    apps = [
        Appliance(name="A", power_w=2000, duration_hours=1, candidate_hours=(10, 14)),
        Appliance(name="B", power_w=2000, duration_hours=1, candidate_hours=(10, 16)),
    ]
    fixed_load_w = {h: 0.0 for h in range(24)}
    fixed_load_w[10] = 2000.0
    Q, var_map = build_qubo(apps, profile, fixed_load_w=fixed_load_w)
    inv = {v: k for k, v in var_map.items()}
    lo, hi = sorted((inv[("A", 10)], inv[("B", 10)]))
    assert Q[lo, hi] >= 1_000_000.0

    # Không tải nền -> 4000W < 5000W -> cặp KHÔNG bị phạt (hành vi cũ giữ nguyên).
    Q2, _ = build_qubo(apps, profile)
    assert Q2[lo, hi] == 0.0


def test_scheduler_avoids_hour_overloaded_by_fixed_background():
    """QuantumScheduler chọn giờ an toàn khi tải nền cố định làm một giờ ứng viên quá tải."""
    profile = build_daily_profile()
    app = Appliance(name="X", power_w=3000, duration_hours=1, candidate_hours=(10, 14))
    fixed_load_w = {h: 0.0 for h in range(24)}
    fixed_load_w[10] = 3000.0
    scheduler = QuantumScheduler([app], profile, fixed_load_w=fixed_load_w)
    result = scheduler.solve(use_quantum=False)
    assert result.schedule["X"] == 14


def test_fixed_load_w_by_hour_sums_on_hours_from_usage_windows():
    """Helper của router: tổng công suất (W) các tải cố định đang bật tại mỗi giờ, lấy giờ bật
    từ usage_windows (khớp cách _default_fixed_hours xác định giờ tải cố định)."""
    fridge = Appliance(name="Tủ lạnh", power_w=100, duration_hours=24,
                       candidate_hours=(), is_flexible=False)
    load = _fixed_load_w_by_hour([fridge])
    # Tủ lạnh chạy 24/7 (DEFAULT_USAGE_WINDOWS: [(0, 24)]).
    assert all(load[h] == 100.0 for h in range(24))


def test_fixed_load_w_by_hour_ignores_flexible_appliances():
    flex = Appliance(name="Máy giặt", power_w=500, duration_hours=1,
                     candidate_hours=(9, 14), is_flexible=True)
    load = _fixed_load_w_by_hour([flex])
    assert all(load[h] == 0.0 for h in range(24))
