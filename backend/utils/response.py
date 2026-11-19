from flask import jsonify


def thanh_cong(message=None, data=None, status=200, **extra):
    body = {"status": "success"}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    body.update(extra)
    return jsonify(body), status


def that_bai(message, status=400):
    return jsonify({"status": "error", "message": message}), status
