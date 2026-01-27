import os
import requests
from datetime import datetime

# ===============================
# API KEY (환경변수에서만 읽음)
# ===============================
API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENWEATHER_API_KEY 환경변수가 설정되지 않았습니다.")

CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

LOG_DIR = "evidence"
LOG_FILE = os.path.join(LOG_DIR, "m3_log.txt")


# ===============================
# 유틸 함수
# ===============================
def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ===============================
# HTTP 에러 로깅 (키/URL 노출 방지)
# ===============================
def log_http_error(context: str, err: requests.HTTPError):
    status = None
    body_preview = None

    if err.response is not None:
        status = err.response.status_code
        try:
            body_preview = err.response.text[:120].replace("\n", " ")
        except Exception:
            body_preview = None

    if status == 401:
        log(f"{context}: 401 Unauthorized - API 키가 유효하지 않거나 아직 활성화되지 않았습니다.")
        log("조치: OpenWeather에서 키 확인/재발급 후, PowerShell 환경변수를 새 키로 다시 설정하세요.")
    elif status == 404:
        log(f"{context}: 404 Not Found - 도시명이 잘못되었을 수 있습니다. (예: Busan, Seoul)")
    elif status is not None:
        log(f"{context}: HTTP {status} 에러 발생")
        if body_preview:
            log(f"{context}: 응답 일부: {body_preview}")
    else:
        log(f"{context}: HTTP 에러 발생 (상태코드 확인 불가)")


# ===============================
# API 호출 함수
# ===============================
def get_current_weather(city: str):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "kr",
    }
    r = requests.get(CURRENT_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    return {
        "temp": float(data["main"]["temp"]),
        "feels_like": float(data["main"]["feels_like"]),
        "desc": data["weather"][0].get("description", ""),
    }


def get_rain_probability(city: str):
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "kr",
    }
    r = requests.get(FORECAST_URL, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    # 가장 가까운 예보(3시간 이내)
    item = data["list"][0]
    pop = float(item.get("pop", 0.0))  # 0.0 ~ 1.0
    pop_percent = int(round(pop * 100))
    pop_time = item.get("dt_txt", "")

    return pop_percent, pop_time


# ===============================
# 출력 함수
# ===============================
def print_weather(city: str, current: dict, pop: int, pop_time: str):
    print("\n==============================")
    print(f"📍 도시: {city}")
    if current.get("desc"):
        print(f"🌥 현재 상태: {current['desc']}")
    print(f"🌡 현재 온도: {current['temp']:.1f}°C")
    print(f"🤒 체감온도: {current['feels_like']:.1f}°C")
    if pop_time:
        print(f"☔ 강수확률: {pop}% (기준: {pop_time})")
    else:
        print(f"☔ 강수확률: {pop}%")
    print("==============================\n")


# ===============================
# 메인
# ===============================
def main():
    ensure_log_dir()

    city = "Seoul"
    log("M3 Weather 프로그램 시작")
    log(f"초기 도시 설정: {city}")

    while True:
        try:
            # 온도/체감온도: Current API
            current = get_current_weather(city)

            # 강수확률: Forecast API
            pop, pop_time = get_rain_probability(city)

            print_weather(city, current, pop, pop_time)
            # ✅ 따옴표/줄바꿈 문제 방지: f-string 한 줄로만 기록
            log(f"날씨 갱신 | {city} | temp={current['temp']:.1f}C, feels={current['feels_like']:.1f}C, pop={pop}%")

        except requests.HTTPError as e:
            log_http_error("API 호출", e)

        except requests.Timeout:
            log("API 호출: Timeout - 네트워크 상태를 확인하고 다시 시도하세요.")

        except requests.RequestException as e:
            # URL/키가 포함될 수 있는 메시지는 최소화
            log(f"API 호출: RequestException - {type(e).__name__}")

        except Exception as e:
            log(f"예상치 못한 에러: {type(e).__name__}")

        cmd = input("입력: [c]도시변경 / [r]새로고침 / [q]종료 > ").strip().lower()

        if cmd == "c":
            new_city = input("도시 이름 입력 (예: Busan, Tokyo) > ").strip()
            if new_city:
                log(f"도시 변경: {city} → {new_city}")
                city = new_city
            else:
                log("도시 변경 취소(빈 입력)")

        elif cmd == "r":
            log("사용자 요청: 새로고침")

        elif cmd == "q":
            log("프로그램 종료")
            break

        else:
            log(f"알 수 없는 입력: {cmd} (c/r/q 중 하나)")


if __name__ == "__main__":
    main()
