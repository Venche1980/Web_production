from aiohttp import web
import asyncpg
import asyncio
import nest_asyncio
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Конфигурация базы данных PostgreSQL
DATABASE_CONFIG = {
    'database': os.getenv('DATABASE_NAME', 'flask_01'),
    'user': os.getenv('DATABASE_USER', 'postgres'),
    'password': os.getenv('DATABASE_PASSWORD', '123'),
    'host': os.getenv('DATABASE_HOST', 'localhost'),
    'port': int(os.getenv('DATABASE_PORT', 5432))
}

# Пул соединений с базой данных
db_pool = None


async def init_db():
    """Инициализация пула подключения к БД и создание таблиц"""
    global db_pool

    # Ждем пока база данных станет доступной
    for attempt in range(30):
        try:
            db_pool = await asyncpg.create_pool(**DATABASE_CONFIG)
            print(f"Подключение к БД успешно (попытка {attempt + 1})")
            break
        except Exception as e:
            print(f"Попытка {attempt + 1}: Ошибка подключения к БД: {e}")
            if attempt < 29:
                await asyncio.sleep(2)
            else:
                raise

    async with db_pool.acquire() as conn:
        # Создание таблицы пользователей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        """)

        # Создание таблицы объявлений
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS advertisements (
                id SERIAL PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER REFERENCES users(id) NOT NULL
            )
        """)

    print("Таблицы созданы успешно")


async def check_auth(email, password):
    """Проверка авторизации пользователя"""
    if not email or not password:
        return None

    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash FROM users WHERE email = $1", email
        )
        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
    return None


# CORS middleware
@web.middleware
async def cors_handler(request, handler):
    if request.method == 'OPTIONS':
        response = web.Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, User-Email, User-Password'
        return response

    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, User-Email, User-Password'
    return response


# Регистрация пользователя
async def register(request):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return web.json_response({'error': 'Email и password обязательны'}, status=400)

        async with db_pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1", email
            )
            if existing_user:
                return web.json_response({'error': 'Пользователь уже существует'}, status=400)

            password_hash = generate_password_hash(password)
            await conn.execute(
                "INSERT INTO users (email, password_hash) VALUES ($1, $2)",
                email, password_hash
            )

        return web.json_response({'message': 'Пользователь создан'}, status=201)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)


# Создание объявления
async def create_ad(request):
    try:
        data = await request.json()

        # Авторизация через заголовки
        email = request.headers.get('User-Email')
        password = request.headers.get('User-Password')

        user = await check_auth(email, password)
        if not user:
            return web.json_response({'error': 'Неверная авторизация'}, status=401)

        title = data.get('title')
        description = data.get('description')

        if not title or not description:
            return web.json_response({'error': 'Title и description обязательны'}, status=400)

        async with db_pool.acquire() as conn:
            ad_id = await conn.fetchval("""
                INSERT INTO advertisements (title, description, owner_id)
                VALUES ($1, $2, $3) RETURNING id""",
                                        title, description, user['id']
                                        )

            ad = await conn.fetchrow("""
                SELECT id, title, description, created_at, owner_id 
                FROM advertisements WHERE id = $1""",
                                     ad_id
                                     )

        return web.json_response({
            'id': ad['id'],
            'title': ad['title'],
            'description': ad['description'],
            'created_at': ad['created_at'].isoformat(),
            'owner_id': ad['owner_id']
        }, status=201)

    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)


# Получение объявления
async def get_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])

        async with db_pool.acquire() as conn:
            ad = await conn.fetchrow("""
                SELECT id, title, description, created_at, owner_id 
                FROM advertisements WHERE id = $1""",
                                     ad_id
                                     )

        if not ad:
            return web.json_response({'error': 'Объявление не найдено'}, status=404)

        return web.json_response({
            'id': ad['id'],
            'title': ad['title'],
            'description': ad['description'],
            'created_at': ad['created_at'].isoformat(),
            'owner_id': ad['owner_id']
        })

    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)


# Редактирование объявления
async def update_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])
        data = await request.json()

        # Проверка авторизации
        email = request.headers.get('User-Email')
        password = request.headers.get('User-Password')

        user = await check_auth(email, password)
        if not user:
            return web.json_response({'error': 'Неверная авторизация'}, status=401)

        title = data.get('title')
        description = data.get('description')

        if not title or not description:
            return web.json_response({'error': 'Title и description обязательны'}, status=400)

        async with db_pool.acquire() as conn:
            ad = await conn.fetchrow(
                "SELECT id, owner_id FROM advertisements WHERE id = $1", ad_id
            )
            if not ad:
                return web.json_response({'error': 'Объявление не найдено'}, status=404)

            if ad['owner_id'] != user['id']:
                return web.json_response({'error': 'Нет прав для редактирования'}, status=403)

            await conn.execute("""
                UPDATE advertisements SET title = $1, description = $2 
                WHERE id = $3""",
                               title, description, ad_id
                               )

            updated_ad = await conn.fetchrow("""
                SELECT id, title, description, created_at, owner_id 
                FROM advertisements WHERE id = $1""",
                                             ad_id
                                             )

        return web.json_response({
            'id': updated_ad['id'],
            'title': updated_ad['title'],
            'description': updated_ad['description'],
            'created_at': updated_ad['created_at'].isoformat(),
            'owner_id': updated_ad['owner_id']
        })

    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)


# Удаление объявления
async def delete_ad(request):
    try:
        ad_id = int(request.match_info['ad_id'])

        # Проверка авторизации
        email = request.headers.get('User-Email')
        password = request.headers.get('User-Password')

        user = await check_auth(email, password)
        if not user:
            return web.json_response({'error': 'Неверная авторизация'}, status=401)

        async with db_pool.acquire() as conn:
            ad = await conn.fetchrow(
                "SELECT id, owner_id FROM advertisements WHERE id = $1", ad_id
            )
            if not ad:
                return web.json_response({'error': 'Объявление не найдено'}, status=404)

            if ad['owner_id'] != user['id']:
                return web.json_response({'error': 'Нет прав для удаления'}, status=403)

            await conn.execute("DELETE FROM advertisements WHERE id = $1", ad_id)

        return web.json_response({'message': 'Объявление удалено'})

    except Exception as e:
        return web.json_response({'error': str(e)}, status=400)


# Создание приложения
async def create_app():
    await init_db()

    app = web.Application(middlewares=[cors_handler])

    # Добавляем маршруты
    app.router.add_post('/register', register)
    app.router.add_post('/advertisements', create_ad)
    app.router.add_get('/advertisements/{ad_id}', get_ad)
    app.router.add_put('/advertisements/{ad_id}', update_ad)
    app.router.add_delete('/advertisements/{ad_id}', delete_ad)

    return app


if __name__ == '__main__':
    # Применяем патч для Windows
    nest_asyncio.apply()

    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


    async def main():
        app = await create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        print("Сервер запущен на http://0.0.0.0:8080")

        try:
            await asyncio.Future()  # Ждем бесконечно
        except KeyboardInterrupt:
            print("Остановка сервера...")
        finally:
            await runner.cleanup()
            if db_pool:
                await db_pool.close()


    # Запускаем сервер
    asyncio.run(main())