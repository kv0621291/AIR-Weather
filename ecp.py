def ecp(result, features, month, day, df_10years, CANCELLATION_THRESHOLDS, print_result=True):
    """
    예측값과 10년치 데이터를 바탕으로 결항 확률(%)을 산출합니다.
    - 임계값 초과 항목이 하나라도 있으면 결항으로 간주합니다.
    """
    filtered = df_10years[(df_10years['month'] == month) & (df_10years['day'] == day)]
    if filtered.empty:
        if print_result:
            print("해당 날짜의 10년치 데이터가 없습니다.")
        return 0.0
    over_threshold = [
        filtered[feature] > CANCELLATION_THRESHOLDS[feature]
        for feature in features
    ]
    cancel_days = (sum(over_threshold) >= 1).sum()
    total_days = len(filtered)
    cancel_prob_past = (cancel_days / total_days) * 100 if total_days > 0 else 0
    predict_flag = any(result[i] > CANCELLATION_THRESHOLDS[feature] for i, feature in enumerate(features))
    if print_result:
        print(f"\n{month}월 {day}일 결항 확률: {cancel_prob_past:.1f}%")
        if predict_flag:
            print("※ 예측값 중 임계값을 초과한 항목이 있습니다. 결항 위험이 높습니다.")
        else:
            print("모든 예측값이 임계값 이하입니다. 결항 위험이 낮습니다.")
    return cancel_prob_past
