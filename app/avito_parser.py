import os
import requests
from bs4 import BeautifulSoup
import hashlib
import json
from enum import Enum

class EstateParam(Enum):
    ROOMS = ("Количество комнат", "🚪 Комнат: {}")
    TOTAL_AREA = ("Общая площадь", "📐 Общая площадь: {}")
    FLOOR = ("Этаж", "🪜  Этаж: {}")
    PLOT_AREA = ("Площадь участка", "🌳 Площадь участка: {}")
    HOUSE_TYPE = ("Тип дома", "🏡 Тип дома: {}")
    WALL_MATERIAL = ("Материал стен", "🧱 Материал стен: {}")
    BUILD_YEAR = ("Год постройки", "📅 Год постройки: {}")
    DISTANCE_TO_CENTER = ("Расстояние до центра города", "📍 Расстояние до центра: {}")
    LAND_CATEGORY = ("Категория земель", "🏞️  Категория земель: {}")
    GARAGE_TYPE = ("Тип гаража", "🚗 Тип гаража: {}")
    PARKING_TYPE = ("Тип машиноместа", "🅿️ Тип машиноместа: {}")
    ROOM_AREA = ("Площадь комнаты", "🛏️  Площадь комнаты: {}")
    ROOMS_IN_APARTMENT = ("Комнат в квартире", "🏠 Комнат в квартире: {}")
    HOUSE_AREA = ("Площадь дома", "🏠 Площадь дома: {}")
    FLOORS_IN_HOUSE = ("Этажей в доме", "🏠 Этажей в доме: {}")
    AREA = ("Площадь:", "📐 Площадь: {}")

    def __init__(self, param_name, display_format):
        self.param_name = param_name
        self.display_format = display_format

class AvitoParser:
    def __init__(self, cache_dir="cache"):
        self.price_value = None
        self.full_address = None
        self.type_estate = None
        self.cache_dir = cache_dir
        # Создаем директорию для кэша, если её нет
        os.makedirs(self.cache_dir, exist_ok=True)

        # Инициализируем все параметры как None
        for param in EstateParam:
            setattr(self, param.name.lower(), None)

    def _get_cache_filename(self, url):
        # Хэшируем URL для создания уникального имени файла
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def _download_html(self, url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Ошибка при загрузке страницы: {response.status_code}")
        return response.text

    def _process_address(self, address):
        parts = address.split(',')
        if 'ул.' or 'пр-т' in parts[-2]:
            processed_parts = [part + '\n 📍' for part in parts[:-2]]
            processed_parts.append(f"{parts[-2]},{parts[-1]}")
        else:
            processed_parts = [part + '\n 📍' for part in parts[:-1]]
            processed_parts.append(parts[-1])
        address = ''.join(processed_parts)
        return address

    def _extract_type_estate(self, title):
        estate_types_mapping = {
            'квартира': 'Квартира',
            'Квартира-студия': 'Студия',
            'Своб. планировка': 'Свободная планировка',
            'Комната': 'Комната',
            'Дом': 'Дом',
            'Дача': 'Дача',
            'Коттедж': 'Коттедж',
            'Таунхаус': 'Таунхаус',
            'ИЖС': 'ИЖС',
            'СНТ, ДНП': 'СНТ',
            'Гараж,': 'Гараж',
            'Машиноместо': 'Машиноместо'
        }
        
        for search_string, estate_type in estate_types_mapping.items():
            if search_string in title:
                return estate_type
        
        return "Не указано"

    def _extract_param(self, params_soup, param_name):
        for li in params_soup.find_all('li', class_='params-paramsList__item-_2Y2O'):
            span = li.find('span', class_='styles-module-noAccent-l9CMS')
            if span and param_name in span.text:
                return span.next_sibling.strip()
        return None

    def _format_price(self, price):
        try:
            price_num = int(price.replace(" ", "").replace("₽", ""))
            return f"{price_num:,}".replace(",", " ")
        except (ValueError, AttributeError):
            return price

    def parse(self, url):
        cache_file = self._get_cache_filename(url)

        # Если файл с кэшем существует, читаем из него
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)

        # Скачиваем HTML
        html = self._download_html(url)

        # Парсим HTML
        soup = BeautifulSoup(html, 'html.parser')

        # Извлекаем заголовок страницы
        title = soup.find('title').text if soup.find('title') else "Не указано"
        self.type_estate = self._extract_type_estate(title)

        # Извлекаем цену
        price_span = soup.find('span', {'itemprop': 'price'})
        self.price_value = price_span.get('content', 'Не указано') if price_span else 'Не указано'
        self.price_value = self._format_price(self.price_value)

        # Извлекаем параметры, если блок параметров существует
        if params_block := soup.find('div', {'data-marker': 'item-view/item-params'}):
            params_soup = BeautifulSoup(params_block.decode_contents(), 'html.parser')

            # Извлекаем все параметры
            for param in EstateParam:
                value = self._extract_param(params_soup, param.param_name)
                setattr(self, param.name.lower(), value)

        # Извлекаем адрес
        address_element = soup.find('span', class_='style-item-address__string-wt61A')
        self.full_address = address_element.text.strip() if address_element else "Не указано"
        self.full_address = self._process_address(self.full_address)

        # Формируем итоговую строку
        result = []
        result.append(f"🌟 <b>{self.type_estate}</b>")
        result.append(f"💵 {self.price_value}₽\n")
        result.append(f"⛳️ {self.full_address}\n")

        # Динамически добавляем параметры, если они не None
        for param in EstateParam:
            value = getattr(self, param.name.lower())
            if value is not None:
                result.append(param.display_format.format(value))

        # Объединяем строки с переносами
        result.append('\n\n')
        result_str = "\n".join(result)

        # Сохраняем результат в кэш
        with open(cache_file, "w", encoding="utf-8") as file:
            json.dump(result_str, file, ensure_ascii=False)

        return result_str


if __name__ == "__main__":
    url0 = 'https://www.avito.ru/ekaterinburg/kvartiry/1-k._kvartira_406_m_69_et._4574477371?context=H4sIAAAAAAAA_wEmANn_YToxOntzOjE6IngiO3M6MTY6Ik9Ra1c5RzE3TUY5c0R2NW8iO32sRl6AJgAAAA'
    parser = AvitoParser()
    print(parser.parse(url0))