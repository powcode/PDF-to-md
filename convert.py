import threading
from pathlib import Path
import fitz
import config
import jobs
from pdf_checks import validate_pdf
from figures import count_document_figures
from extract import detect_footers, extract_slide_markdown
from describe import describe_figure

def run_conversion_task(job_id: str, pdf_path: Path, original_stem: str):
    try:
        jobs.update_job(job_id, status="running", message="Membaca file PDF...")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        doc, err = validate_pdf(pdf_bytes)
        if err:
            jobs.update_job(job_id, status="error", error=err, message=err)
            return

        total_slides = len(doc)
        total_figures, doc_figures = count_document_figures(doc)

        if total_figures > config.MAX_FIGURES:
            err = f"Jumlah gambar ({total_figures}) melebihi batas {config.MAX_FIGURES} gambar."
            jobs.update_job(job_id, status="error", error=err, message=err)
            doc.close()
            return

        jobs.update_job(
            job_id,
            status="running",
            progress={"slide": 0, "total_slides": total_slides, "figure": 0, "total_figures": total_figures},
            message=f"Memproses {total_slides} slide dan {total_figures} gambar..."
        )

        # Detect footers
        footer_patterns = detect_footers(doc)

        all_slides_md = []
        global_fig_count = 0
        global_important_fig_count = 0
        stats = {
            "slides": total_slides,
            "figures": total_figures,
            "figures_ok": 0,
            "figures_needs_review": 0,
            "figures_failed": 0,
            "figures_cached": 0,
            "figures_skipped": 0
        }

        # Process each slide
        for slide_idx in range(total_slides):
            page = doc[slide_idx]
            slide_num = slide_idx + 1
            page_figs = doc_figures[slide_idx]

            jobs.update_job_progress(
                job_id,
                slide=slide_num,
                figure=global_fig_count,
                message=f"Memproses slide {slide_num} dari {total_slides}..."
            )

            # Describe figures on this slide
            valid_figs = []
            fig_descriptions = []
            slide_raw_text = page.get_text()

            for fig in page_figs:
                global_fig_count += 1
                jobs.update_job_progress(
                    job_id,
                    slide=slide_num,
                    figure=global_fig_count,
                    message=f"Slide {slide_num} dari {total_slides}, gambar {global_fig_count} dari {total_figures}..."
                )

                if not config.AI_MODEL:
                    desc = "Deskripsi gambar belum diaktifkan (Model AI belum diatur di config.py)."
                    status = "needs_review"
                else:
                    try:
                        desc, status = describe_figure(
                            fig["png_bytes"],
                            fig["caption"],
                            fig["context"],
                            slide_raw_text
                        )
                    except Exception as ex:
                        desc = "Deskripsi gambar gagal dibuat, perlu ditinjau."
                        status = "failed"

                stats[f"figures_{status}"] = stats.get(f"figures_{status}", 0) + 1
                
                # If vision model flagged as decorative/unimportant, omit from markdown
                if status != "skipped" and desc != "DEKORASI_SLIDE":
                    valid_figs.append(fig)
                    fig_descriptions.append(desc)

            slide_md, next_fig_idx = extract_slide_markdown(
                page=page,
                slide_num=slide_num,
                page_figures=valid_figs,
                figure_descriptions=fig_descriptions,
                global_figure_start_index=global_important_fig_count,
                footer_patterns=footer_patterns
            )
            global_important_fig_count = next_fig_idx
            all_slides_md.append(slide_md)

        full_md = "\n\n---\n\n".join(all_slides_md)
        doc.close()

        # Save output file
        out_file = config.OUTPUT_DIR / f"{job_id}.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(full_md)

        jobs.update_job(
            job_id,
            status="done",
            markdown=full_md,
            stats=stats,
            message="Selesai."
        )

    except Exception as e:
        err_msg = f"Terjadi kesalahan saat pemrosesan: {str(e)}"
        jobs.update_job(job_id, status="error", error=err_msg, message=err_msg)

def start_conversion_thread(job_id: str, pdf_path: Path, original_stem: str):
    t = threading.Thread(
        target=run_conversion_task,
        args=(job_id, pdf_path, original_stem),
        daemon=True
    )
    t.start()
    return t
