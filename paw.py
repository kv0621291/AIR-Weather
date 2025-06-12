import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from tabulate import tabulate

def paw(airport_name, airport_cd):
    """
    Print real-time weather info for the given airport code (e.g., "Incheon Airport", "RKSI").
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
                tm = item.findtext('tm', default='N/A')
                weather = item.findtext('weather', default='N/A')
                temp_minmax = item.findtext('sel_val1', default='N/A')
                rain_snow = item.findtext('sel_val2', default='N/A')
                summary = item.findtext('summary', default='N/A')
                outlook = item.findtext('outlook', default='N/A')
                try:
                    obs_dt = datetime.strptime(tm, '%Y%m%d%H%M')
                    obs_str = obs_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    obs_str = tm
                table_title = f"[{airport_name}] Weather Info as of {obs_str}"
                headers = ["Obs Time", "Weather", "Min/Max Temp", "Precip/Snow", "Summary"]
                table = [[obs_str, weather, temp_minmax, rain_snow, summary]]
                print(f"\n{table_title}\n")
                print(tabulate(
                    table,
                    headers=headers,
                    tablefmt="grid",
                    stralign="center",
                    numalign="center"
                ))
                print("■ Weather Overview")
                print(outlook)
                print()
            else:
                print("No real-time airport data available.")
        else:
            print(f"Airport weather API error: {response.status_code}")
    except Exception as e:
        print("Error retrieving airport weather info:", e)
