#!/usr/bin/python

# ------------------------------
# HTTP server for face alignment
# pi-null-mezon@yandex.ru
# ------------------------------

import flask
from waitress import serve

import os
import dlib
import cv2
import numpy

app = flask.Flask(__name__)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(
    os.getenv("SHAPE_PREDICTOR_MODEL", "/models/shape_predictor_5_face_landmarks.dat")
)


@app.route("/status", methods=["GET"])
def status():
    return (
        flask.jsonify(
            {"status": "Success", "name": "alignface-service", "version": "1.0.0.0"}
        ),
        200,
    )


@app.route("/align", methods=["POST"])
def align():
    if "file" not in flask.request.files:
        return (
            flask.jsonify(
                {"status": "Error", "info": "'file' part is missing in request"}
            ),
            400,
        )
    file = flask.request.files["file"]
    target_eyes_dst = 120
    if "distance" in flask.request.form:
        target_eyes_dst = float(flask.request.form["distance"])
    target_width = 480
    if "width" in flask.request.form:
        target_width = int(flask.request.form["width"])
    target_height = 640
    if "height" in flask.request.form:
        target_height = int(flask.request.form["height"])
    shift = 0.1
    if "shift" in flask.request.form:
        shift = float(flask.request.form["shift"])
    img = cv2.imdecode(numpy.frombuffer(file.read(), numpy.uint8), cv2.IMREAD_COLOR)
    if img.shape[0] == 0 or img.shape[1] == 0:
        return (
            flask.jsonify({"Status": "Error", "info": "image can not be decoded"}),
            400,
        )
    dets = detector(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if len(dets) == 0:
        return (
            flask.jsonify({"status": "Error", "info": "no faces on the input image"}),
            400,
        )

    d = None
    widest = 0
    for det in dets:
        width = det.right() - det.left()
        if width > widest:
            widest = width
            d = det

    shape = predictor(img, d)
    rpt = (shape.part(0) + shape.part(1)) / 2
    lpt = (shape.part(2) + shape.part(3)) / 2
    eyes_dst = dlib.length(rpt - lpt)
    # print(f"dst: {eyes_dst}")
    angle = 180.0 * numpy.arctan((lpt.y - rpt.y) / (lpt.x - rpt.x)) / numpy.pi
    # print(f"angle: {angle}")
    cpt = (rpt + lpt) / 2
    cpt.y += d.height() * shift
    scale = target_eyes_dst / eyes_dst
    rmatrix = cv2.getRotationMatrix2D((cpt.x, cpt.y), angle, scale)
    rmatrix[0, 2] += target_width / 2.0 - cpt.x
    rmatrix[1, 2] += target_height / 2.0 - cpt.y
    alignedimg = cv2.warpAffine(
        img, rmatrix, (target_width, target_height), borderValue=cv2.mean(img)
    )
    return flask.Response(
        cv2.imencode("*.jpg", alignedimg)[1].tobytes(),
        mimetype="image/jpeg",
        status=200,
    )


if __name__ == "__main__":
    serve(
        app,
        host=os.getenv("APP_ADDR", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 5000)),
    )
