import pytest
import io
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_upscale_no_file(client):
    """Тест загрузки без файла"""
    response = client.post('/upscale')
    assert response.status_code == 400
    assert b'No file uploaded' in response.data

def test_upscale_with_file(client):
    """Тест загрузки с файлом"""
    # Создаем тестовый файл
    data = {
        'file': (io.BytesIO(b'fake image data'), 'test.png')
    }
    response = client.post('/upscale', data=data)
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'task_id' in json_data

def test_task_status(client):
    """Тест получения статуса задачи"""
    response = client.get('/tasks/fake-task-id')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'state' in json_data
    assert 'status' in json_data

def test_processed_file_not_found(client):
    """Тест получения несуществующего файла"""
    response = client.get('/processed/nonexistent.png')
    assert response.status_code == 404
    assert b'File not found' in response.data