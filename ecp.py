# ecp.py

def ecp(result, features, month, day, df_10years, CANCELLATION_THRESHOLDS):
    """
    예측 결과와 10년간 데이터를 기반으로 결항 확률(%)을 추정
    - 기준: 한 feature라도 결항 기준 초과 시 결항으로 간주
    """
    filtered = df_10years[(df_10years['month'] == month) & (df_10years['day'] == day)]
    if filtered.empty:
        print("10년간 해당 날짜의 데이터가 없습니다.")
        return 0.0

    # 각 feature별 결항 기준 초과 여부
    over_threshold = [
        filtered[feature] > CANCELLATION_THRESHOLDS[feature]
        for feature in features
    ]
    # 한 feature라도 초과한 날이 있으면 결항으로 간주
    cancel_days = (sum(over_threshold) >= 1).sum()
    total_days = len(filtered)
    cancel_prob_past = (cancel_days / total_days) * 100 if total_days > 0 else 0

    # 예측값이 결항 기준을 넘으면 경고
    predict_flag = any(result[i] > CANCELLATION_THRESHOLDS[feature] for i, feature in enumerate(features))

    print(f"\n예측일({month}/{day})의 결항 확률: {cancel_prob_past:.1f}%")
    if predict_flag:
        print("※ 예측값 중 결항 기준을 초과한 항목이 있습니다. 결항 위험이 높습니다.")
    else:
        print("예측값이 결항 기준 미만입니다. 결항 위험이 낮습니다.")

    return cancel_prob_past