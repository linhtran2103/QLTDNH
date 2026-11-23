
import pyodbc

from flask import Blueprint, Flask, current_app, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import (
    DUNG_LUONG_ANH_TOI_DA,
    PROJECT_ROOT,
    PUBLIC_BASE_URL,
    SECRET_KEY,
)

from backend.utils.response import that_bai


web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def trang_chu():
    return render_template("dashboard.html")


@web_bp.route("/login")
def trang_dang_nhap():
    return render_template("login.html")


@web_bp.route("/foods")
def trang_mon_an():
    return render_template("foods.html")


@web_bp.route("/foods/add")
def trang_them_mon_an():
    return render_template("add_food.html")


@web_bp.route("/foods/edit/<int:food_id>")
def trang_sua_mon_an(food_id):
    return render_template("edit_food.html", food_id=food_id)


@web_bp.route("/categories")
def trang_danh_muc():
    return render_template("categories.html")


@web_bp.route("/users")
def trang_quan_ly_tai_khoan():
    return render_template("users.html")


# TRANG THỐNG KÊ DOANH THU
@web_bp.route("/revenue")
def trang_thong_ke_doanh_thu():
    return render_template("revenue.html")


def create_app():

    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "frontend" / "templates"),
        static_folder=str(PROJECT_ROOT / "frontend" / "static"),
    )

    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = DUNG_LUONG_ANH_TOI_DA + 1024 * 1024
    app.config["PUBLIC_BASE_URL"] = PUBLIC_BASE_URL

    app.json.ensure_ascii = False

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        allow_headers=["Content-Type", "Authorization"]
    )

    from backend.auth import auth_bp
    from backend.ban import ban_bp
    from backend.danh_muc import danh_muc_bp
    from backend.mon_an import mon_an_bp
    from backend.nguoi_dung import nguoi_dung_bp
    from backend.nhat_ky import nhat_ky_bp
    from backend.thong_ke import thong_ke_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ban_bp)
    app.register_blueprint(danh_muc_bp)
    app.register_blueprint(mon_an_bp)
    app.register_blueprint(nguoi_dung_bp)
    app.register_blueprint(nhat_ky_bp)
    app.register_blueprint(thong_ke_bp)

    @app.errorhandler(Exception)
    def xu_ly_loi(error):

        la_api = request.path.startswith("/api/")

        if isinstance(error, HTTPException):

            if not la_api:
                return error

            if error.code == 413:
                return that_bai("Ảnh không được vượt quá 5MB", 413)

            return that_bai(error.description, error.code)

        current_app.logger.exception(
            "Lỗi không xử lý được: %s %s",
            request.method,
            request.path
        )

        if la_api:

            if isinstance(error, pyodbc.IntegrityError):
                return that_bai(
                    "Dữ liệu bị trùng hoặc đang được dùng ở nơi khác",
                    400
                )

            return that_bai("Đã xảy ra lỗi phía máy chủ", 500)

        return "Đã xảy ra lỗi phía máy chủ", 500

    return app
