import os
from flask import Flask, render_template, jsonify
import config

import io
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import config
import jobs
import convert
import split
from pdf_checks import validate_pdf
from figures import count_document_figures

def create_app():
    app = Flask(__name__)
    # Note: Flask MAX_CONTENT_LENGTH is not globally set so Split PDF can accept arbitrary sizes.
    # Individual routes enforce limits if required.

    # Ensure required runtime folders exist
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/inspect", methods=["POST"])
    def api_inspect():
        if "file" not in request.files:
            return jsonify({"error": "File tidak ditemukan dalam unggahan."}), 400
        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "Tidak ada file yang dipilih."}), 400

        file_bytes = f.read()
        import fitz
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            total = len(doc)
            doc.close()
            return jsonify({
                "filename": f.filename,
                "pages": total,
                "size_mb": round(len(file_bytes) / (1024 * 1024), 2)
            })
        except Exception:
            return jsonify({"error": "File tidak dapat dibaca sebagai dokumen PDF."}), 400

    @app.route("/api/convert", methods=["POST"])
    def api_convert():
        if "file" not in request.files:
            return jsonify({"error": "File tidak ditemukan dalam unggahan."}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "Tidak ada file yang dipilih."}), 400

        file_bytes = f.read()
        doc, err = validate_pdf(file_bytes, check_limits=True, require_text=True)
        if err:
            return jsonify({"error": err}), 400

        original_stem = Path(f.filename).stem
        total_slides = len(doc)
        doc.close()

        job_id = jobs.create_job(total_slides=total_slides, total_figures=0)
        upload_path = config.UPLOAD_DIR / f"{job_id}.pdf"
        with open(upload_path, "wb") as out_f:
            out_f.write(file_bytes)

        convert.start_conversion_thread(job_id, upload_path, original_stem)
        return jsonify({"job_id": job_id})

    @app.route("/api/jobs/<job_id>", methods=["GET"])
    def api_get_job(job_id):
        job = jobs.get_job(job_id)
        if not job:
            return jsonify({"error": "Pekerjaan tidak ditemukan."}), 404
        return jsonify({
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "error": job.get("error")
        })

    @app.route("/api/jobs/<job_id>/result", methods=["GET"])
    def api_get_job_result(job_id):
        job = jobs.get_job(job_id)
        if not job:
            return jsonify({"error": "Pekerjaan tidak ditemukan."}), 404
        if job["status"] != "done":
            return jsonify({"error": "Pekerjaan belum selesai."}), 400
        return jsonify({
            "markdown": job["markdown"],
            "stats": job["stats"]
        })

    @app.route("/api/jobs/<job_id>/download", methods=["GET"])
    def api_download_job(job_id):
        job = jobs.get_job(job_id)
        if not job:
            return jsonify({"error": "Pekerjaan tidak ditemukan."}), 404
        out_file = config.OUTPUT_DIR / f"{job_id}.md"
        if not out_file.exists():
            return jsonify({"error": "File output tidak ditemukan."}), 404
        return send_file(
            out_file,
            as_attachment=True,
            download_name=f"slides_{job_id[:8]}.md",
            mimetype="text/markdown"
        )

    @app.route("/api/split", methods=["POST"])
    def api_split():
        if "file" not in request.files:
            return jsonify({"error": "File tidak ditemukan dalam unggahan."}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "Tidak ada file yang dipilih."}), 400

        range_str = request.form.get("ranges", "").strip()
        if not range_str:
            return jsonify({"error": "Rentang halaman tidak boleh kosong."}), 400

        file_bytes = f.read()
        doc, err = validate_pdf(file_bytes, check_limits=False, require_text=False)
        if err:
            return jsonify({"error": err}), 400

        sorted_pages, range_err = split.parse_page_ranges(range_str, len(doc))
        if range_err:
            doc.close()
            return jsonify({"error": range_err}), 400

        split_bytes = split.split_pdf_doc(doc, sorted_pages)
        doc.close()

        original_stem = Path(f.filename).stem
        return send_file(
            io.BytesIO(split_bytes),
            as_attachment=True,
            download_name=f"{original_stem}_split.pdf",
            mimetype="application/pdf"
        )

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({"error": f"Ukuran file melebihi batas {config.MAX_UPLOAD_MB} MB."}), 413

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Permintaan tidak valid."}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Halaman atau sumber daya tidak ditemukan."}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Terjadi kesalahan internal pada server."}), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=True)
