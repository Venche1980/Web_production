from typing import List, Dict, Optional
from datetime import datetime
from app.models import Advertisement


# Временное хранилище в памяти (позже можно заменить на БД)
class Database:
    def __init__(self):
        self.advertisements: Dict[int, Advertisement] = {}
        self.current_id = 1

    def create_advertisement(self, ad: Advertisement) -> Advertisement:
        ad.id = self.current_id
        ad.created_at = datetime.now()
        self.advertisements[self.current_id] = ad
        self.current_id += 1
        return ad

    def get_advertisement(self, ad_id: int) -> Optional[Advertisement]:
        return self.advertisements.get(ad_id)

    def update_advertisement(self, ad_id: int, update_data: dict) -> Optional[Advertisement]:
        if ad_id in self.advertisements:
            ad = self.advertisements[ad_id]
            for key, value in update_data.items():
                if value is not None and hasattr(ad, key):
                    setattr(ad, key, value)
            return ad
        return None

    def delete_advertisement(self, ad_id: int) -> bool:
        if ad_id in self.advertisements:
            del self.advertisements[ad_id]
            return True
        return False

    def search_advertisements(self, filters: dict) -> List[Advertisement]:
        result = []
        for ad in self.advertisements.values():
            match = True
            for key, value in filters.items():
                if value is not None:
                    if key == "title" and ad.title and value.lower() not in ad.title.lower():
                        match = False
                        break
                    elif key == "description" and ad.description and value.lower() not in ad.description.lower():
                        match = False
                        break
                    elif key == "author" and ad.author and value.lower() not in ad.author.lower():
                        match = False
                        break
                    elif key == "min_price" and ad.price < float(value):
                        match = False
                        break
                    elif key == "max_price" and ad.price > float(value):
                        match = False
                        break
            if match:
                result.append(ad)
        return result


# Создаем единственный экземпляр базы данных
db = Database()