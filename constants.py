BASE = "https://www.invitro.ru/analizes/for-doctors/"
BASE_HOST = "https://www.invitro.ru"
CITY_SLUGS_CACHE_FILE = "city_slugs_cache.json"

# Initial set of city slugs before caching
CITY_SLUGS = {
    "москва": "",
    "moskva": "",
    "moscow": "",
    "санкт-петербург": "piter",
    "санкт петербург": "piter",
    "спб": "piter",
    "piter": "piter",
    "saint-petersburg": "piter",
    "аша": "asha",
    "asha": "asha",
    "зеленчукская": "zelenchukskaya",
    "zelenchukskaya": "zelenchukskaya",
    "кимовск": "kimovsk",
    "kimovsk": "kimovsk",
}

# Column names for final Excel export
COLS = [
    "Категория",
    "Подкатегория",
    "Название анализа",
    "Код анализа во внутренней системе Invitro",
    "Код анализа по номенклатуре МЗ РФ (если есть)",
    "Срок выполнения анализа",
    "Стоимость анализа",
]
