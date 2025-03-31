import dotenv
import requests
import json
from tqdm import tqdm
import os

dotenv.load_dotenv()

VK_TOKEN = os.environ.get("VK_TOKEN")



VK_API_URL = "https://api.vk.com/method/photos.get"
YANDEX_API_URL = "https://cloud-api.yandex.net/v1/disk/resources/upload"


class VKPhotoBackup:
    def __init__(self, vk_token, yandex_token, vk_user_id, num_photos=5):
        self.vk_token = vk_token
        self.yandex_token = yandex_token
        self.vk_user_id = vk_user_id
        self.num_photos = num_photos
        self.photo_data = []

    def get_vk_photos(self):
        response = requests.get(VK_API_URL, params={
            'access_token': self.vk_token,
            'v': '5.199',
            'owner_id': self.vk_user_id,
            'album_id': 'profile',
            'extended': '1',
            'photo_sizes': '1'
        })

        data = response.json()
        if "response" not in data:
            raise ValueError(f"Ошибка VK API: {data}")

        photos = []
        for obj in data["response"].get("items", []):
            max_size = max(obj["sizes"], key=lambda s: s["height"] * s["width"])  # Наибольший размер
            photos.append({
                "likes": obj["likes"]["count"],
                "date": obj["date"],
                "url": max_size["url"],
                "size": max_size["type"]
            })
        # Сортировка по лайкам, потом по дате
        photos.sort(key=lambda p: (p["likes"], p["date"]), reverse=True)
        return photos[:self.num_photos]

    def upload_to_yandex(self, photo_url, filename):
        folder = "VK_Backup"
        headers = {"Authorization": f"OAuth {self.yandex_token}"}

        # Создание папки (если её нет)
        requests.put(f"https://cloud-api.yandex.net/v1/disk/resources?path={folder}", headers=headers)

        # Получение ссылки для загрузки
        upload_url = requests.get(YANDEX_API_URL, headers=headers, params={"path": f"{folder}/{filename}", "overwrite": "true"}).json()
        if "href" not in upload_url:
            raise ValueError(f"Ошибка получения ссылки для загрузки: {upload_url}")

        # Загрузка файла
        file_data = requests.get(photo_url).content
        response = requests.put(upload_url["href"], files={"file": file_data})
        if response.status_code != 201:
            raise ValueError(f"Ошибка загрузки: {response.text}")

    def backup_photos(self):
        print("Получаю фото из ВКонтакте...")
        photos = self.get_vk_photos()

        print(f"Нашел {len(photos)} фото. Начинаю загрузку на Я.Диск...")
        for photo in tqdm(photos, desc="Загрузка"):
            filename = f"{photo['likes']}.jpg"
            if any(p["file_name"] == filename for p in self.photo_data):  # Проверка на дубликаты
                filename = f"{photo['likes']}_{photo['date']}.jpg"

            self.upload_to_yandex(photo["url"], filename)
            self.photo_data.append({"file_name": filename, "size": photo["size"]})

        # Сохранение информации в JSON
        with open("photos_backup.json", "w") as json_file:
            json.dump(self.photo_data, json_file, indent=4)
        print("Резервное копирование завершено! Данные сохранены в папку VK_Backup")


# Запрос ID юзера в ВК
VK_USER_ID = input("Введите ID пользователя ВК: ")
YANDEX_TOKEN = input('Введите токен яндекс диска')

backup = VKPhotoBackup(VK_TOKEN, YANDEX_TOKEN, VK_USER_ID)
backup.backup_photos()