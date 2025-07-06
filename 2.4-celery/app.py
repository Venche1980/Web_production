from flask import Flask, request, jsonify, send_file
from celery import Celery
import cv2
from cv2 import dnn_superres
import os
import uuid

app = Flask(__name__)


app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

scaler = None

def load_model():
    """Загружаем модель"""
    global scaler
    try:
        scaler = dnn_superres.DnnSuperResImpl_create()
        scaler.readModel('EDSR_x2.pb')
        scaler.setModel("edsr", 2)
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        scaler = None


@celery.task
def upscale_image(input_path, output_path):
    """Задача для апскейлинга изображения"""
    global scaler

    if scaler is None:
        load_model()

    try:
        if scaler is None:
            return {'status': 'error', 'message': 'Model not loaded'}

        image = cv2.imread(input_path)
        if image is None:
            return {'status': 'error', 'message': f'Could not read image from {input_path}'}

        result = scaler.upsample(image)

        cv2.imwrite(output_path, result)

        return {'status': 'success', 'output_file': os.path.basename(output_path)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.route('/upscale', methods=['POST'])
def upscale():
    """Принимает файл с изображением и возвращает id задачи"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(PROCESSED_FOLDER, filename)

    file.save(input_path)

    task = upscale_image.delay(input_path, output_path)

    return jsonify({'task_id': task.id})


@app.route('/tasks/<task_id>')
def get_task_status(task_id):
    """Возвращает статус задачи"""
    task = upscale_image.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is waiting'
        }
    elif task.state == 'SUCCESS':
        result = task.result
        if result['status'] == 'success':
            response = {
                'state': task.state,
                'status': 'completed',
                'file_url': f'/processed/{result["output_file"]}'
            }
        else:
            response = {
                'state': task.state,
                'status': 'error',
                'message': result['message']
            }
    else:
        response = {
            'state': task.state,
            'status': str(task.info)
        }

    return jsonify(response)


@app.route('/processed/<filename>')
def get_processed_file(filename):
    """Возвращает обработанный файл"""
    file_path = os.path.join(PROCESSED_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    load_model()
    app.run(debug=True, host='0.0.0.0')