import os
import base64
import uuid
import cv2
import numpy as np
import requests
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from keras.models import load_model

# Konfigurasi API You.com
YOU_API_KEY = "a0a7ea3c-70af-45b2-a1a3-13defad18b27<__>1RfxPyETU8N2v5f4r1d4elnD"
YOU_API_URL = "https://chat-api.you.com/smart"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load model dan label
model = load_model("model/keras_Model.h5", compile=False)
class_names = open("model/labels.txt", "r").readlines()

# 🔹 Fungsi You AI Chat: Jelaskan penyakit berdasarkan nama
def get_you_diagnosis(disease_name):
    prompt = (
        f"Tolong jelaskan informasi tentang penyakit berikut ini:\n\n"
        f"Nama penyakit: {disease_name}\n\n"
        f"Saya ingin tahu:\n"
        f"- Apa itu penyakit ini?\n"
        f"- Bagaimana gejala dan penyebabnya?\n"
        f"- Bagaimana cara penyembuhannya?\n"
        f"- Obat untuk penyakit ini?\n"
        f"Jelaskan dengan bahasa awam."
    )

    try:
        headers = {
            "X-API-Key": YOU_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "query": prompt
        }

        response = requests.post(YOU_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("text", "❌ You AI tidak memberikan respons teks.")
    except Exception as e:
        return f"❌ You AI gagal menjawab: {str(e)}"

# 🔹 Prediksi gambar dengan Keras
def predict_keras(image_np):
    image = cv2.resize(image_np, (224, 224), interpolation=cv2.INTER_AREA)
    image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
    image = (image / 127.5) - 1
    prediction = model.predict(image)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()
    confidence_score = float(prediction[0][index])
    return class_name, confidence_score

# 🔹 Deteksi lewat kamera
def detect_disease_with_camera():
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return "❌ Kamera tidak tersedia", None
    ret, frame = cam.read()
    cam.release()
    if not ret:
        return "❌ Gagal mengambil gambar", None

    filename = f"{uuid.uuid4().hex}.jpg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    cv2.imwrite(image_path, frame)

    predicted_label, confidence = predict_keras(frame)
    you_info = get_you_diagnosis(predicted_label)

    result = (
        f"📸 Deteksi Kamera: <b>{predicted_label}</b><br>"
        f"🧪 Kepercayaan Model: {confidence:.2%}<br><br>"
        f"🧠 You AI Menjawab:<br>{you_info}"
    )
    return result, image_path

# 🔹 Deteksi lewat upload gambar
def detect_disease_with_upload(image_path):
    with open(image_path, "rb") as img_file:
        b64_image = base64.b64encode(img_file.read()).decode("utf-8")

    prompt = (
        "Saya mengunggah gambar penyakit kulit. Tolong bantu identifikasi dan jawab secara detail:\n"
        "- Nama penyakit\n"
        "- Deskripsi penyakit\n"
        "- Cara penyembuhan\n"
        "- Nama obat\n\n"
        "Jawab dengan bahasa mudah dimengerti.\n"
        f"Gambar base64:\n{b64_image}"
    )

    try:
        headers = {
            "X-API-Key": YOU_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "query": prompt
        }

        response = requests.post(YOU_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("text", "❌ You AI tidak memberikan respons teks.")
    except Exception as e:
        return f"❌ You AI gagal menjawab: {str(e)}"

# 🔹 Route utama
@app.route("/", methods=["GET", "POST"])
def home():
    diagnosis = ""
    image_path = ""

    if request.method == "POST":
        method = request.form.get("method")
        if method == "upload":
            file = request.files.get("image")
            if not file or file.filename == "":
                diagnosis = "❌ Gambar tidak ditemukan."
            else:
                filename = secure_filename(file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
                gpt_result = detect_disease_with_upload(image_path)
                diagnosis = f"🧠 You AI Analisa Upload Gambar:<br>{gpt_result}"
        elif method == "camera":
            diagnosis, image_path = detect_disease_with_camera()

    return render_template("index.html", diagnosis=diagnosis, image_path=image_path)

if __name__ == "__main__":
    app.run(debug=True)
