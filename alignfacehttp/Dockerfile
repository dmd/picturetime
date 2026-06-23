FROM python:3.13-slim

WORKDIR /usr/src/app

COPY shape_predictor_5_face_landmarks.dat.bz2 .
COPY requirements.txt .

# build-essential + cmake are needed only to compile dlib; bzip2 decompresses the model.
RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential cmake bzip2 && \
    bzip2 -d shape_predictor_5_face_landmarks.dat.bz2 && \
    mkdir /models && \
    mv *.dat /models && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

COPY httpsrv.py /usr/src/app/httpsrv.py
CMD ["python", "/usr/src/app/httpsrv.py"]
