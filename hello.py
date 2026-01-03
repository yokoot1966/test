from datetime import datetime
import urllib.request
import urllib.parse
import json
import sys
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
import readline
# デフォルト登録都市（永続化と編集のベース）
DEFAULT_CITIES = {
    '東京': 'Asia/Tokyo',
    'ニューヨーク': 'America/New_York',
    'ロンドン': 'Europe/London',
    'パリ': 'Europe/Paris',
    'シドニー': 'Australia/Sydney',
    'ドバイ': 'Asia/Dubai',
    'バンコク': 'Asia/Bangkok',
}

# ファイル永続化パス
_CITIES_PATH = 'cities.json'

# timezonefinder インスタンス
tzf = TimezoneFinder()

# 補完候補の管理（登録都市 + セッション履歴）
_city_history = []


def _completer(text, state):
    names = list(cities.keys()) + _city_history if 'cities' in globals() else _city_history
    candidates = []
    seen = set()
    for n in names:
        if n.startswith(text) and n not in seen:
            candidates.append(n)
            seen.add(n)
    try:
        return candidates[state]
    except IndexError:
        return None


# readline の設定
try:
    import readline
    readline.set_completer(_completer)
    readline.set_completer_delims('\n')
    readline.parse_and_bind('tab: complete')
except Exception:
    pass


def load_cities() -> dict:
    try:
        with open(_CITIES_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return dict(DEFAULT_CITIES)


def save_cities(d: dict) -> None:
    try:
        with open(_CITIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def manage_cities_menu(curr: dict) -> dict:
    """簡易メニュー: 一覧 / 追加 / 変更 / 削除 / 保存して戻る"""
    while True:
        print('\n--- 登録都市メンテナンス ---')
        print('1) 一覧  2) 追加  3) 変更  4) 削除  5) 保存して戻る  6) 中止(保存せず)')
        choice = input('選択: ').strip()
        if choice == '1':
            print('\n登録都市一覧:')
            for i, (name, tz) in enumerate(curr.items(), start=1):
                print(f"{i}. {name} -> {tz}")
        elif choice == '2':
            name = input('追加する都市名: ').strip()
            if not name:
                print('空の名前は追加できません')
                continue
            if name in curr:
                print('既に登録されています')
                continue
            tz = input('タイムゾーンを手入力 (例 Asia/Tokyo)、自動判定は空で Enter: ').strip()
            if not tz:
                coords = geocode_city(name)
                tz = latlon_to_timezone(coords[0], coords[1]) if coords else None
                if not tz:
                    tz = input('自動判定失敗。タイムゾーンを入力してください: ').strip()
            curr[name] = tz if tz else ''
            print(f'追加しました: {name} -> {curr[name]}')
        elif choice == '3':
            print('\n変更したい都市を番号で選択')
            items = list(curr.items())
            for i, (name, tz) in enumerate(items, start=1):
                print(f"{i}. {name} -> {tz}")
            sel = input('番号: ').strip()
            if not sel.isdigit() or not (1 <= int(sel) <= len(items)):
                print('無効な番号')
                continue
            idx = int(sel) - 1
            old_name, old_tz = items[idx]
            new_name = input(f'新しい都市名 (空で {old_name} のまま): ').strip() or old_name
            new_tz = input(f'新しいタイムゾーン (空で {old_tz} のまま): ').strip() or old_tz
            # 適用
            if new_name != old_name:
                curr.pop(old_name, None)
            curr[new_name] = new_tz
            print('更新しました')
        elif choice == '4':
            print('\n削除したい都市を番号で選択')
            items = list(curr.items())
            for i, (name, tz) in enumerate(items, start=1):
                print(f"{i}. {name} -> {tz}")
            sel = input('番号: ').strip()
            if not sel.isdigit() or not (1 <= int(sel) <= len(items)):
                print('無効な番号')
                continue
            idx = int(sel) - 1
            name = items[idx][0]
            ok = input(f'{name} を削除しますか? (y/n): ').strip().lower()
            if ok == 'y':
                curr.pop(name, None)
                print('削除しました')
        elif choice == '5':
            save_cities(curr)
            print('保存しました。')
            return curr
        elif choice == '6':
            print('キャンセル。保存せず戻ります。')
            return curr
        else:
            print('無効な選択')
def latlon_to_timezone(lat: float, lon: float) -> str | None:
    try:
        tz = tzf.timezone_at(lng=lon, lat=lat)
        return tz
    except Exception:
        return None


def get_weather(city: str) -> dict | None:
    """wttr.in から指定都市の天気を取得して JSON を返す。
    ネットワークエラーやパースエラー時は None を返す。
    """
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded}?format=j1"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (WeatherScript)'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        data = json.loads(raw)
        return data
    except Exception:
        return None


def geocode_city(city: str) -> tuple[float, float] | None:
    """Nominatimで都市名をジオコーディングし、(lat, lon) を返す。"""
    try:
        q = urllib.parse.quote(city)
        url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (GeoCoder)'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        items = json.loads(raw)
        if not items:
            return None
        lat = float(items[0]['lat'])
        lon = float(items[0]['lon'])
        return (lat, lon)
    except Exception:
        return None


def get_wikipedia_summary(title: str, max_chars: int = 300) -> str | None:
    """Try Japanese then English Wikipedia for a short plain-text summary.
    Returns truncated summary (max_chars) or None if not found.
    """
    for lang in ('ja', 'en'):
        try:
            q = urllib.parse.quote(title)
            url = (
                f"https://{lang}.wikipedia.org/w/api.php?"
                f"action=query&prop=extracts&exintro&explaintext&redirects=1&format=json&titles={q}"
            )
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (CitySummary)'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode('utf-8')
            data = json.loads(raw)
            pages = data.get('query', {}).get('pages', {})
            for page_id, page in pages.items():
                if page_id == '-1':
                    continue
                extract = page.get('extract', '')
                if extract:
                    s = extract.replace('\n', ' ').strip()
                    if len(s) > max_chars:
                        s = s[:max_chars].rstrip() + '…'
                    return s
        except Exception:
            continue
    return None


def print_weather(city: str, data: dict) -> None:
    if not data:
        print(f"{city} の天気情報を取得できませんでした。ネットワークや都市名を確認してください。")
        return

    # current_condition 配列の先頭に現在情報がある
    try:
        cur = data['current_condition'][0]
        desc = cur.get('weatherDesc', [{'value': '不明'}])[0].get('value')
        temp_c = cur.get('temp_C')
        feels_like = cur.get('FeelsLikeC')
        humidity = cur.get('humidity')
        obs_time = cur.get('observation_time')

        print('\n' + '=' * 40)
        print(f"都市: {city}")
        if obs_time:
            print(f"観測時刻(UTC): {obs_time}")
        print(f"現在の天気: {desc}")
        if temp_c is not None:
            print(f"気温: {temp_c}°C (体感: {feels_like}°C)")
        if humidity is not None:
            print(f"湿度: {humidity}%")
        print('=' * 40 + '\n')
    except Exception:
        print(f"{city} の天気データの解析に失敗しました。")


def main():
    # print("Hello New World")

    # 登録都市をロード（ファイルがあれば上書き）
    global cities
    cities = load_cities()

    # コマンドラインで管理モードを起動できる
    if '--manage' in sys.argv:
        cities = manage_cities_menu(dict(cities))
        print('管理モードを終了します。')
        return

    # 現在時刻を日本時間で表示
    now_jst = datetime.now(ZoneInfo('Asia/Tokyo'))
    print(f"今日の日付: {now_jst.strftime('%Y年%m月%d日')}")
    print(f"時刻: {now_jst.strftime('%H:%M:%S')}")

    def process_city(city: str) -> None:
        # タイムゾーン表示: 登録都市なら直接、そうでなければジオコーディングで判定
        tz_name = None
        if city in cities:
            tz_name = cities[city]
        else:
            coords = geocode_city(city)
            if coords:
                tz_name = latlon_to_timezone(coords[0], coords[1])

        if tz_name:
            try:
                now_city = datetime.now(ZoneInfo(tz_name))
                print(f"{city}の時刻: {now_city.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")
            except Exception:
                print(f"{city} の現地時刻を取得できませんでした。タイムゾーン: {tz_name}")
        else:
            print(f"'{city}'のタイムゾーンが特定できませんでした。現地時刻は表示できません。")
            print(f"利用可能な登録都市: {', '.join(cities.keys())}")

        # 天気情報の取得と表示
        data = get_weather(city)
        print_weather(city, data)

        # 都市説明（Wikipedia から取得）
        desc = get_wikipedia_summary(city, max_chars=300)
        if desc:
            print('---')
            print(f"{city} の説明:")
            print(desc)
        else:
            print(f"{city} の説明は見つかりませんでした。")

    # 初回: 引数があればそれを処理、なければループで入力を待つ
    next_city = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else None

    while True:
        if next_city:
            city = next_city
            next_city = None
        else:
            try:
                city = input("\n都市名を入力してください（Enterで終了、Tabで補完）: ").strip()
            except EOFError:
                print('\n入力が閉じられました。終了します。')
                break

        if not city:
            print('終了します。')
            break
        process_city(city)
        # セッション履歴に追加（先頭に新しいものを追加し重複を避ける）
        try:
            if city in _city_history:
                _city_history.remove(city)
            _city_history.insert(0, city)
            # 履歴は最大30件に抑える
            _city_history[:] = _city_history[:30]
        except Exception:
            pass


if __name__ == '__main__':
    main()

