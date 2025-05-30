import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from tabulate import tabulate

from paw import paw
from ecp import ecp  # ← 추가

np.set_printoptions(threshold=np.inf, linewidth=200)

AIRPORTS = {
    "1": {
        "name": "인천공항",
        "code": "RKSI",
        "model": "icn/icn_lstm_model.keras",
        "scaler_min": "icn/icn_scaler_min.npy",
        "scaler_max": "icn/icn_scaler_max.npy",
        "data": "icn/icn_scaled_data.csv",
        "raw": "icn/icn_2000-2025.csv"
    },
    "2": {
        "name": "김포공항",
        "code": "RKSS",
        "model": "gmp/gmp_lstm_model.keras",
        "scaler_min": "gmp/gmp_scaler_min.npy",
        "scaler_max": "gmp/gmp_scaler_max.npy",
        "data": "gmp/gmp_scaled_data.csv",
        "raw": "gmp/gmp_1970-2025.csv"
    }
}

FEATURES = ['평균풍속(KT)', '최대순간풍속(KT)', '강수량합(mm)', '1시간최다강수(mm)', '최심신적설(cm)']
SEQ_LENGTH = 7

CANCELLATION_THRESHOLDS = {
    '평균풍속(KT)': 25.0,
    '최대순간풍속(KT)': 35.0,
    '강수량합(mm)': 110.0,
    '1시간최다강수(mm)': 20.0,
    '최심신적설(cm)': 5.0
}

def load_airport_files(airport_code):
    info = AIRPORTS[airport_code]
    model = load_model(info["model"])
    scaler_min = np.load(info["scaler_min"])
    scaler_max = np.load(info["scaler_max"])
    df_scaled = pd.read_csv(info["data"])
    df_scaled['일시'] = pd.to_datetime(df_scaled['일시'])
    try:
        df_raw = pd.read_csv(info["raw"], encoding='euc-kr')
    except UnicodeDecodeError:
        df_raw = pd.read_csv(info["raw"], encoding='cp949')
    if '일시' in df_raw.columns:
        df_raw['일시'] = pd.to_datetime(df_raw['일시'])
        df_raw['month'] = df_raw['일시'].dt.month
        df_raw['day'] = df_raw['일시'].dt.day
    return model, scaler_min, scaler_max, df_scaled, df_raw

def predict_weather(model, scaler_min, scaler_max, df_scaled, month, day):
    target = df_scaled[(df_scaled['일시'].dt.month == month) & (df_scaled['일시'].dt.day == day)]
    if len(target) < SEQ_LENGTH:
        print("해당 날짜의 과거 데이터가 부족합니다.")
        return None
    last_seq = target.tail(SEQ_LENGTH)[FEATURES].values.astype(np.float32)
    last_seq = last_seq.reshape((1, SEQ_LENGTH, len(FEATURES)))
    pred = model.predict(last_seq)
    pred_original = pred * (scaler_max - scaler_min) + scaler_min
    return pred_original[0]

def print_prediction_report(result, features, month, day, df_10years):
    print(f"\n=== 예측 결과 및 결항 기준 비교({month}/{day}) ===")
    predicted_values = [result[i] for i in range(len(features))]
    cancellation_thresholds = [CANCELLATION_THRESHOLDS[f] for f in features]
    percentages = [
        (predicted_values[i] / cancellation_thresholds[i]) * 100 if cancellation_thresholds[i] != 0 else 0
        for i in range(len(features))
    ]
    filtered = df_10years[(df_10years['month'] == month) & (df_10years['day'] == day)]
    exceed_counts = [(filtered[feature] > CANCELLATION_THRESHOLDS[feature]).sum() for feature in features]

    report_data = {
        '항목': features,
        '예측 값': [f"{v:.2f}" for v in predicted_values],
        '결항 기준': cancellation_thresholds,
        '결항 기준 대비 백분율(%)': [f"{p:.1f}" for p in percentages],
        '지난 10년간 초과 횟수': exceed_counts
    }
    df_report = pd.DataFrame(report_data)

    # 중앙 정렬 옵션
    table = tabulate(
        df_report,
        headers="keys",
        tablefmt="grid",  # 경계선 포함 보기 좋은 표
        showindex=False,
        stralign="center",
        numalign="center"
    )
    print(table)

def main_menu():
    while True:
        print("\n=== 공항 날씨 예측 프로그램 ===")
        print("1. 인천공항")
        print("2. 김포공항")
        print("0. 프로그램 종료")
        sel = input("공항을 선택하세요: ")
        if sel in AIRPORTS:
            airport_menu(sel)
        elif sel == "0":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 선택하세요.")

def airport_menu(airport_code):
    model, scaler_min, scaler_max, df_scaled, df_raw = load_airport_files(airport_code)
    while True:
        paw(AIRPORTS[airport_code]['name'], AIRPORTS[airport_code]['code'])
        print("\n1. 날짜 선택하여 예측")
        print("0. 뒤로가기")
        sel = input("메뉴를 선택하세요: ")
        if sel == "1":
            go_to_main = date_menu(model, scaler_min, scaler_max, df_scaled, df_raw, AIRPORTS[airport_code]['name'])
            if go_to_main:
                break
        elif sel == "0":
            break
        else:
            print("잘못된 입력입니다. 다시 선택하세요.")

def date_menu(model, scaler_min, scaler_max, df_scaled, df_raw, airport_name):
    while True:
        print(f"\n[{airport_name}] 날짜 선택")
        print("0. 첫 화면으로 돌아가기")
        user_input = input("예측할 월(1~12, 0 입력 시 첫 화면): ")
        if user_input == "0":
            return True
        try:
            month = int(user_input)
            day = int(input("예측할 일(1~31): "))
            if not (1 <= month <= 12 and 1 <= day <= 31):
                print("잘못된 날짜입니다.")
                continue
        except ValueError:
            print("숫자를 입력하세요.")
            continue
        result = predict_weather(model, scaler_min, scaler_max, df_scaled, month, day)
        if result is not None:
            print_prediction_report(result, FEATURES, month, day, df_raw)
            # 결항 확률 계산 (별도 파일 함수)
            ecp(result, FEATURES, month, day, df_raw, CANCELLATION_THRESHOLDS)
        print("\n0. 첫 화면으로 돌아가기")
        back = input("계속하려면 Enter, 첫 화면으로 돌아가려면 0을 입력하세요: ")
        if back == "0":
            return True

if __name__ == "__main__":
    main_menu()