import asyncio
import datetime

import aiohttp
from more_itertools import chunked

from models import Session, SwapiPeople, close_orm, init_orm

MAX_REQUESTS = 5


async def get_person(person_id, session):
    url = f"https://swapi.dev/api/people/{person_id}/"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        return None


async def get_name_from_url(url, session):
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            return data.get('name') or data.get('title')
        return None


async def process_person_data(person_data, session):
    if not person_data:
        return None

    # Получаем ID из URL
    person_id = int(person_data['url'].split('/')[-2])

    # Получаем названия фильмов
    films_names = []
    for film_url in person_data.get('films', []):
        name = await get_name_from_url(film_url, session)
        if name:
            films_names.append(name)

    # Получаем название родной планеты
    homeworld_name = ""
    if person_data.get('homeworld'):
        homeworld_name = await get_name_from_url(person_data['homeworld'], session)

    # Получаем названия видов
    species_names = []
    for species_url in person_data.get('species', []):
        name = await get_name_from_url(species_url, session)
        if name:
            species_names.append(name)

    # Получаем названия кораблей
    starships_names = []
    for starship_url in person_data.get('starships', []):
        name = await get_name_from_url(starship_url, session)
        if name:
            starships_names.append(name)

    # Получаем названия транспорта
    vehicles_names = []
    for vehicle_url in person_data.get('vehicles', []):
        name = await get_name_from_url(vehicle_url, session)
        if name:
            vehicles_names.append(name)

    return {
        'id': person_id,
        'birth_year': person_data.get('birth_year'),
        'eye_color': person_data.get('eye_color'),
        'films': ', '.join(films_names),
        'gender': person_data.get('gender'),
        'hair_color': person_data.get('hair_color'),
        'height': person_data.get('height'),
        'homeworld': homeworld_name,
        'mass': person_data.get('mass'),
        'name': person_data.get('name'),
        'skin_color': person_data.get('skin_color'),
        'species': ', '.join(species_names),
        'starships': ', '.join(starships_names),
        'vehicles': ', '.join(vehicles_names)
    }


async def insert_people(people_list):
    async with Session() as session:
        people_objects = []
        for person_data in people_list:
            if person_data:
                people_objects.append(SwapiPeople(**person_data))

        if people_objects:
            session.add_all(people_objects)
            await session.commit()


async def main():
    await init_orm()

    # Отключаем проверку SSL из-за проблем с сертификатом на swapi.dev
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Получаем всех персонажей (примерно до 100)
        for person_id_chunk in chunked(range(1, 101), MAX_REQUESTS):
            # Получаем данные персонажей
            person_tasks = [get_person(person_id, session) for person_id in person_id_chunk]
            persons_data = await asyncio.gather(*person_tasks)

            # Обрабатываем данные каждого персонажа
            processed_data = []
            for person_data in persons_data:
                processed_person = await process_person_data(person_data, session)
                if processed_person:
                    processed_data.append(processed_person)

            # Сохраняем в базу
            if processed_data:
                await insert_people(processed_data)

    await close_orm()


start = datetime.datetime.now()
asyncio.run(main())
print(f"Время выполнения: {datetime.datetime.now() - start}")