# paw.py

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from tabulate import tabulate

def paw(airport_name, airport_cd):
    """
    공항코드(예: "인천공항", "RKSI")를 받아 해당 공항의 어제 17시 기준 기상 정보를 표로 출력하고,
    일기 개황과 위험기상예보는 표 아래에 별도 출력
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    base_time = "1700"
    url = (
        "https://apihub.kma.go.kr/api/typ02/openApi/AirPortService/getAirPort"
        f"?pageNo=1&numOfRows=10&dataType=XML&base_date={yesterday}&base_time={base_time}"
        f"&airPortCd={airport_cd}&authKey=JqqAloFPS0yqgJaBT-tM4Q"
    )

    try:
        response = requests.get(url)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            item = root.find('.//item')
            if item is not None:
                # 표에 들어갈 데이터
                tm = item.findtext('tm', default='정보 없음')               # 관측시각
                weather = item.findtext('weather', default='정보 없음')     # 날씨
                temp_minmax = item.findtext('sel_val1', default='정보 없음') # 최저/최고기온
                rain_snow = item.findtext('sel_val2', default='정보 없음')   # 예상 강수량/강설량
                summary = item.findtext('summary', default='정보 없음')      # 요약

                # 표 아래 별도 출력 데이터
                outlook = item.findtext('outlook', default='정보 없음')      # 일기 개황

                # 관측시각 포맷 변환 (YYYY-MM-DD HH:MM)
                try:
                    obs_dt = datetime.strptime(tm, '%Y%m%d%H%M')
                    obs_str = obs_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    obs_str = tm

                table_title = f"[{airport_name}] {obs_str} 기준 기상 정보"

                # 표 데이터 구성
                headers = ["관측시각", "날씨", "최저/최고기온", "예상 강수량/강설량", "요약"]
                table = [[obs_str, weather, temp_minmax, rain_snow, summary]]

                print(f"\n{table_title}")
                print()
                print(tabulate(
                    table,
                    headers=headers,
                    tablefmt="grid",
                    stralign="center",
                    numalign="center"
                ))

                # 표 아래 별도 출력
                print("■ 일기 개황")
                print(outlook)
                print()

            else:
                print("공항 실황 데이터가 없습니다.")
        else:
            print(f"공항 날씨 API 오류: {response.status_code}")
    except Exception as e:
        print("공항 날씨 정보 조회 중 오류:", e)

# 사용 예시 (main.py에서)
# from paw import paw
# paw("인천공항", "RKSI")
# paw("김포공항", "RKSS")