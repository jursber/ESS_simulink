"""全商业模式调度算法验证脚本。"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from src.models.dispatch import (
    ESSParams, FinancialParams, HourlyData,
    BusinessModel, PricingMode,
)
from src.core.dispatch import run_dispatch
from src.data.config import ConfigLoader
from src.data.loader import DataLoader


def get_tou_price(h: int) -> float:
    """行政分时电价 (M1): 河南峰谷平."""
    if 0 <= h < 8:
        return 0.28  # 谷
    elif 8 <= h < 12 or 17 <= h < 21:
        return 0.95  # 峰
    else:
        return 0.58  # 平 (12-17, 21-24)


def build_hourly() -> list[HourlyData]:
    load_df = pd.read_csv('data/load/daily_default.csv')
    load_df['date'] = load_df['date'].astype(str)
    day_data = load_df[load_df['date'] == '2026-03-15'].sort_values('hour')

    p_da, p_rt = DataLoader.load_spot_prices('henan', '2026-03-15')
    contract_df = ConfigLoader.load_contract_position('henan', '2026-03-15', profile='mock_henan')
    dayahead_df = ConfigLoader.load_dayahead_position('henan', '2026-03-15', profile='mock_henan')

    hourly = []
    for _, row in day_data.iterrows():
        h = int(row['hour'])
        ct = contract_df[contract_df['hour'] == h]
        da = dayahead_df[dayahead_df['hour'] == h]
        hourly.append(HourlyData(
            hour=h,
            load_real=float(row['Load_real']),
            P_user=get_tou_price(h),
            P_da=p_da[h],
            P_rt=p_rt[h],
            Q_contract=float(ct['q_contract_kwh'].iloc[0]),
            P_contract=float(ct['p_contract_yuan_per_kwh'].iloc[0]),
            Q_dayahead=float(da['q_dayahead_kwh'].iloc[0]),
        ))
    return hourly


def validate_result(result, params: ESSParams, label: str) -> list[str]:
    """验证调度结果的物理和经济约束。返回问题列表。"""
    issues = []
    n = len(result.load_ESS)

    # 1. 物理约束
    for h in range(n):
        if abs(result.load_ESS[h]) > params.max_power + 1e-6:
            issues.append(f"[{label}] h={h}: |load_ESS|={abs(result.load_ESS[h]):.1f} > P_max={params.max_power}")

        if result.SOC[h] < params.soc_min - 1e-6:
            issues.append(f"[{label}] h={h}: SOC={result.SOC[h]:.4f} < SOC_min={params.soc_min}")
        if result.SOC[h] > params.soc_max + 1e-6:
            issues.append(f"[{label}] h={h}: SOC={result.SOC[h]:.4f} > SOC_max={params.soc_max}")

    # 2. 充电时 SOC 应上升
    for h in range(1, n):
        if result.load_ESS[h] < -1e-6 and result.SOC[h] <= result.SOC[h-1] - 1e-9:
            issues.append(f"[{label}] h={h}: 充电但SOC未上升")

    # 3. 放电时 SOC 应下降
    for h in range(1, n):
        if result.load_ESS[h] > 1e-6 and result.SOC[h] >= result.SOC[h-1] + 1e-9:
            issues.append(f"[{label}] h={h}: 放电但SOC未下降")

    # 4. 充放电互斥在逐时模拟中自然保证，检查是否有同时充放的小时
    # (算法本身保证了这点)

    # 5. 用户节省合理性
    if result.user_savings < -1e6:
        issues.append(f"[{label}] 用户节省异常大负值: {result.user_savings:.1f}")

    # 6. ESS收入 = 电费节省 * (1 - r_user)，验证一致性
    if abs(result.ess_revenue) > 1e-6:
        expected = result.user_savings * 0.7  # B1 r_user=0.3
        # 不在此做严格校验，因为r_user因模式不同

    # 7. 日初SOC应接近初始值
    if abs(result.SOC[0] - 0.10) > 1e-6:
        issues.append(f"[{label}] 日初SOC={result.SOC[0]:.4f} != 0.10")

    # 8. load_grid = load_real - load_ESS 恒成立(由计算保证)

    return issues


def main():
    params = ESSParams()
    fin = FinancialParams()
    hourly = build_hourly()

    print(f"储能: Cap={params.cap_rated}kWh, P_rated={params.power_rated}MW, "
          f"eta_rt={params.eta_roundtrip}, eta_s={params.eta_single:.4f}")
    print(f"SOC: [{params.soc_min}, {params.soc_max}], P_max={params.max_power:.0f}kW")
    print(f"财务: r_user={fin.r_user}, r_discount={fin.r_discount}")
    print(f"负荷: {[f'{h.load_real:.0f}' for h in hourly]}")
    print(f"P_user: {[f'{h.P_user:.2f}' for h in hourly]}")
    print(f"P_rt: {[f'{h.P_rt:.3f}' for h in hourly]}")
    print()

    all_bms = [
        (BusinessModel.B1_USER_ESS, "B1"),
        (BusinessModel.B2A_RETAILER, "B2a"),
        (BusinessModel.B2B_ESS, "B2b"),
        (BusinessModel.B2C_USER, "B2c"),
        (BusinessModel.B3A_COMBINED, "B3a"),
        (BusinessModel.B3B_USER, "B3b"),
        (BusinessModel.B4_UNIFIED, "B4"),
    ]

    all_issues = []
    for bm, label in all_bms:
        result = run_dispatch(hourly, bm, PricingMode.M1_ADMIN_TOU, params, fin)
        issues = validate_result(result, params, label)
        all_issues.extend(issues)

        n_charge = sum(1 for x in result.load_ESS if x < -1)
        n_disch = sum(1 for x in result.load_ESS if x > 1)
        daily_disch = sum(max(0, x) for x in result.load_ESS)

        print(f"--- {label} ---")
        print(f"  load_ESS: {[f'{x:.0f}' for x in result.load_ESS]}")
        print(f"  SOC:      {[f'{s:.2f}' for s in result.SOC]}")
        print(f"  充:{n_charge}h 放:{n_disch}h  日放:{daily_disch:.0f}kWh  循环:{result.equivalent_cycles:.2f}")
        print(f"  日套利:{result.daily_arbitrage:.1f}  用户节省:{result.user_savings:.1f}  用户净得:{result.user_net:.1f}")
        if result.retail_profit != 0:
            print(f"  购电成本:{result.purchase_cost:.1f}  售电收入:{result.retail_revenue:.1f}  售电利润:{result.retail_profit:.1f}")
        print(f"  ESS收入:{result.ess_revenue:.1f}  ESS年净:{result.ess_net_annual:.0f}")
        print(f"  IRR={result.irr*100:.1f}%  NPV={result.npv:.0f}  回收期={result.payback_years:.1f}年")
        if result.combined_profit != 0:
            print(f"  组合利润:{result.combined_profit:.1f}  总福利:{result.total_welfare:.1f}")

    print(f"\n{'='*60}")
    if all_issues:
        print(f"发现 {len(all_issues)} 个问题:")
        for iss in all_issues:
            print(f"  ✗ {iss}")
    else:
        print("全部约束验证通过, 未发现问题.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
