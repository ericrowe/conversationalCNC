import os
from flask import Blueprint, render_template

web_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.abspath(os.path.join(web_dir, "..", "templates"))
static_dir = os.path.abspath(os.path.join(web_dir, "..", "static"))

web_bp = Blueprint(
    "web",
    __name__,
    template_folder=templates_dir,
    static_folder=static_dir
)


@web_bp.route("/")
def index():
    return render_template("operations/drilling.html")

@web_bp.route("/drilling")
def drilling_page():
    return render_template("operations/drilling.html")

@web_bp.route("/peck-drilling")
def peck_drilling_page():
    return render_template("operations/peck_drilling.html")

@web_bp.route("/thread-milling")
def thread_milling_page():
    return render_template("operations/thread_milling.html")

@web_bp.route("/circular-pocket")
def circular_pocket_page():
    return render_template("operations/circular_pocket.html")

@web_bp.route("/surfacing")
def surfacing_page():
    return render_template("operations/surfacing.html")

@web_bp.route("/engraving")
def engraving_page():
    return render_template("operations/engraving.html")

@web_bp.route("/machines")
def machines_page():
    return render_template("machines.html")


@web_bp.route("/tools")
def tools_page():
    return render_template("tools.html")

