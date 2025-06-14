import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tensorflow.keras.models import load_model
from tabulate import tabulate
import matplotlib.pyplot as plt
import time

try:
    from paw import paw
except Exception as e:
    print(f"[warning] paw 모듈 import 중 오류 발생: {e}")
    paw = None

try:
    from ecp import ecp
except Exception as e:
    print(f"[warning] ecp 모듈 import 중 오류 발생: {e}")
    ecp = None
    
"""
# paw, ecp 모듈 import 실패 시 즉시 종료
try:
    from paw import paw
except Exception as e:
    sys.exit(f"[fatal] paw 모듈 import 중 오류 발생: {e}\n프로그램을 종료합니다.")

try:
    from ecp import ecp
except Exception as e:
    sys.exit(f"[fatal] ecp 모듈 import 중 오류 발생: {e}\n프로그램을 종료합니다.")
"""

np.set_printoptions(threshold=np.inf, linewidth=200)

AIRPORTS = {
    "1": {
        "name": "Incheon Airport",
        "code": "RKSI",
        "model": "icn/icn_lstm_model.keras",
        "scaler_min": "icn/icn_scaler_min.npy",
        "scaler_max": "icn/icn_scaler_max.npy",
        "data": "icn/icn_scaled_data.csv",
        "raw": "icn/icn_2000-2025.csv"
    },
    "2": {
        "name": "Gimpo Airport",
        "code": "RKSS",
        "model": "gmp/gmp_lstm_model.keras",
        "scaler_min": "gmp/gmp_scaler_min.npy",
        "scaler_max": "gmp/gmp_scaler_max.npy",
        "data": "gmp/gmp_scaled_data.csv",
        "raw": "gmp/gmp_1970-2025.csv"
    }
}

# 한글 컬럼명 사용
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
        print("선택한 날짜에 대한 과거 데이터가 부족합니다.")
        return None
    last_seq = target.tail(SEQ_LENGTH)[FEATURES].values.astype(np.float32)
    last_seq = last_seq.reshape((1, SEQ_LENGTH, len(FEATURES)))
    pred = model.predict(last_seq)
    pred_original = pred * (scaler_max - scaler_min) + scaler_min
    return pred_original[0]

def print_prediction_report(result, features, month, day, df_10years):
    print(f"\n=== 예측 및 결항 임계값 ({month}월 {day}일) ===")
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
        '예측값': [f"{v:.2f}" for v in predicted_values],
        '임계값': cancellation_thresholds,
        '임계값 대비 (%)': [f"{p:.1f}" for p in percentages],
        '10년간 초과일수': exceed_counts
    }
    df_report = pd.DataFrame(report_data)
    table = tabulate(
        df_report,
        headers="keys",
        tablefmt="grid",
        showindex=False,
        stralign="center",
        numalign="center"
    )
    print(table)

def predict_week(model, scaler_min, scaler_max, df_scaled, start_month, start_day, df_10years):
    start_date = datetime(datetime.now().year, start_month, start_day)
    dates = [(start_date + timedelta(days=i)) for i in range(7)]
    date_labels = [f"{d.month}/{d.day}" for d in dates]
    week_preds = []
    week_probs = []
    for d in dates:
        result = predict_weather(model, scaler_min, scaler_max, df_scaled, d.month, d.day)
        if result is None:
            week_preds.append([None]*len(FEATURES))
            week_probs.append(None)
            continue
        week_preds.append([float(f"{v:.2f}") for v in result])
        prob = ecp(result, FEATURES, d.month, d.day, df_10years, CANCELLATION_THRESHOLDS, print_result=False)
        week_probs.append(float(f"{prob:.1f}"))
    feature_rows = []
    for i in range(len(FEATURES)):
        feature_rows.append([day_preds[i] for day_preds in week_preds])
    feature_rows.append(week_probs)
    row_labels = FEATURES + ['결항확률(%)']
    df_week = pd.DataFrame(feature_rows, index=row_labels, columns=date_labels)
    print(f"\n=== 주간 예측 테이블 ({date_labels[0]} ~ {date_labels[-1]}) ===")
    print(tabulate(
        df_week,
        headers="keys",
        tablefmt="grid",
        stralign="center",
        numalign="center"
    ))
    max_prob = max([p for p in week_probs if p is not None] or [0])
    ymax = ((int(max_prob) // 20) + 1) * 20 if max_prob % 20 != 0 else int(max_prob)
    if ymax < 20:
        ymax = 20
    plt.figure(figsize=(10, 4))
    plt.plot(date_labels, week_probs, marker='o', color='red', label='Cancelation Probability(%)')
    for i, v in enumerate(week_probs):
        if v is not None:
            plt.annotate(f"{v}%", (date_labels[i], v), textcoords="offset points", xytext=(0,8), ha='center', fontsize=10)
    plt.ylim(0, ymax)
    plt.yticks(np.arange(0, ymax+1, 10))
    plt.grid(axis='y', which='major', linestyle='--', alpha=0.6)
    plt.title(f"Period: {date_labels[0]} ~ {date_labels[-1]}", fontsize=15)
    plt.xlabel("Date")
    plt.ylabel("Cancelation Probability(%)")
    plt.legend()
    plt.tight_layout()
    plt.show()
    time.sleep(0.5)

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
        print("\n1. 하루 예측")
        print("2. 1주일 예측(입력일 포함 7일)")
        print("0. 첫 화면으로 돌아가기")
        sel = input("메뉴를 선택하세요: ")
        if sel == "1":
            result = predict_weather(model, scaler_min, scaler_max, df_scaled, month, day)
            if result is not None:
                print_prediction_report(result, FEATURES, month, day, df_raw)
                ecp(result, FEATURES, month, day, df_raw, CANCELLATION_THRESHOLDS)
            print("\n0. 첫 화면으로 돌아가기")
            back = input("Enter를 입력하면 날짜 선택 화면, 0을 입력하면 첫 화면으로 돌아갑니다: ")
            if back == "0":
                return True
        elif sel == "2":
            predict_week(model, scaler_min, scaler_max, df_scaled, month, day, df_raw)
            print("\n0. 첫 화면으로 돌아가기")
            back = input("Enter를 입력하면 날짜 선택 화면, 0을 입력하면 첫 화면으로 돌아갑니다: ")
            if back == "0":
                return True
        elif sel == "0":
            return True
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

def main_menu():
    while True:
        print("\n=== 공항 기상 예측 프로그램 ===")
        print("1. 인천공항")
        print("2. 김포공항")
        print("0. 종료")
        sel = input("공항을 선택하세요: ")
        if sel in AIRPORTS:
            airport_menu(sel)
        elif sel == "0":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 선택하세요.")

if __name__ == "__main__":
    main_menu()
