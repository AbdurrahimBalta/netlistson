FROM python:3.9.16


# Çalışma dizinini ayarla
WORKDIR /app

RUN apt update
RUN apt install libngspice0-dev -y

# Gerekli bağımlılıkları kopyala ve kur
COPY requirements.txt .

RUN pip install -r requirements.txt

RUN pip install opencv-python-headless==4.5.5.64
# Uygulama dosyalarını kopyala
COPY . .

EXPOSE 8000

# Uygulamayı çalıştır
CMD ["uvicorn" ,"main:app" ,"--host","0.0.0.0", "--port","10000"]
