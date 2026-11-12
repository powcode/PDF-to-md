# Slidekit

Aplikasi web lokal serbaguna untuk memproses dokumen presentasi dan dokumen PDF:
1. **PDF ke Markdown**: Mengekstrak slide PDF menjadi format Markdown terstruktur, membersihkan logo institusi/elemen template dekoratif berulang, dan memberikan deskripsi teks 2–3 kalimat otomatis untuk setiap gambar penting menggunakan AI Visual (Google Gemini 3.5 Flash).
2. **Split PDF**: Alat pemotong halaman PDF tanpa batasan ukuran file maupun jumlah halaman, dilengkapi deteksi otomatis total halaman, tombol pintas instan, dan pratinjau halaman langsung (*live preview*).

---

## Fitur Utama

### 1. PDF ke Markdown
- **Dukungan Dokumen Luas**: Mendukung semua jenis file PDF tanpa batasan metadata PowerPoint.
- **Penyaringan Gambar Cerdas (2 Lapisan)**:
  - Otomatis mendeteksi dan membuang elemen berulang (logo universitas/perusahaan di pojok slide, ikon judul, pita dekorasi, sampul latar belakang).
  - Hanya mengekstrak dan mendeskripsikan gambar substansial (diagram alur, tabel data, grafik statistik, arsitektur sistem, rumus).
- **Deskripsi Visual AI**: Menggunakan model `gemini-3.5-flash` dengan format deskripsi tepat 2–3 kalimat, dilengkapi mekanisme fallback kuota otomatis.
- **Tabel & Footer**: Deteksi tabel bawaan (*table parser*) menjadi Markdown table, serta pembersihan otomatis teks footer berulang dan penomoran slide.
- **Live Progress Bar**: Indikator status persentase dan teks proses secara *real-time* per slide dan per gambar.

### 2. Split PDF
- **Bebas Batasan**: Tidak dibatasi ukuran file (bisa puluhan hingga ratusan MB) dan tidak dibatasi jumlah halaman. Mendukung segala jenis PDF (termasuk hasil scan / gambar murni).
- **Deteksi Otomatis Info Dokumen**: Langsung menampilkan jumlah total halaman dan ukuran file begitu dokumen dipilih.
- **Dua Metode Pemilihan Halaman**:
  - **📘 Mode Rentang (Dari – Sampai)**: Masukkan halaman awal dan akhir, didukung tombol pintas instan (*Semua Halaman*, *Paruh Awal*, *Paruh Akhir*).
  - **✏️ Mode Kustom / Acak**: Input teks bebas menggunakan format rentang dan koma (contoh: `1-5, 8, 12-14`).
- **Pratinjau Langsung (Live Preview)**: Menampilkan konfirmasi daftar halaman yang akan diekstrak sebelum tombol unduh ditekan, serta validasi otomatis jika halaman melebihi kapasitas dokumen.

---

## Prasyarat

- Python 3.10+
- Kunci API Google Gemini (AI Studio)

---

## Instalasi

### Cara 1: Menggunakan `uv` (Direkomendasikan)

1. Buat virtual environment:
   ```bash
   uv venv .venv
   ```

2. Pasang dependensi:
   - **Windows (Command Prompt / PowerShell)**:
     ```bash
     uv pip install --python .venv\Scripts\python.exe -r requirements.txt
     ```
   - **Bash / macOS / Linux**:
     ```bash
     uv pip install --python .venv/Scripts/python.exe -r requirements.txt
     ```

### Cara 2: Menggunakan Python `venv` & `pip` Standar

1. Buat virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Aktifkan virtual environment:
   - **Windows Command Prompt**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **Windows PowerShell**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Git Bash / Linux / macOS**:
     ```bash
     source .venv/Scripts/activate
     ```

3. Pasang dependensi:
   ```bash
   pip install -r requirements.txt
   ```

---

## Konfigurasi API Key

Slidekit otomatis membaca konfigurasi kunci API dari file `.env` di direktori utama proyek.

1. Buka file `.env` di folder proyek:
   ```env
   GEMINI_API_KEY=kunci_api_gemini_anda
   ```
   *(File `.env` sudah masuk dalam `.gitignore` sehingga aman dan tidak akan terunggah ke repositori git).*

2. Model AI default diatur ke `gemini-3.5-flash` di `config.py` (dengan fallback otomatis jika kuota harian model habis).

---

## Menjalankan Aplikasi

Jalankan server Flask:

```bash
# Melalui venv aktif:
python app.py

# Atau langsung menggunakan interpreter venv:
.venv\Scripts\python.exe app.py
```

Buka peramban di:
```
http://127.0.0.1:5000
```

---

## Menjalankan Pengujian (Testing)

Jalankan seluruh test otomatis dengan pytest:

```bash
# Melalui venv aktif:
pytest

# Atau langsung via venv:
.venv\Scripts\python.exe -m pytest
```

---

## Struktur Folder

```
PDF2md/
├── app.py              # Server Flask & routing API (/api/convert, /api/split, /api/inspect)
├── config.py           # Konfigurasi parameter, direktori, & auto-load .env
├── pdf_checks.py       # Validasi format & struktur PDF
├── figures.py          # Deteksi & pemfilteran gambar penting (menyingkirkan logo/dekorasi)
├── describe.py         # Klien Gemini Vision API, pemvalidasi kalimat, & fallback kuota
├── extract.py          # Ekstraksi teks slide, tabel, dan pembersihan footer
├── convert.py          # Orkestrasi antrean konversi PDF ke Markdown
├── split.py            # Logika pemotongan halaman dokumen PDF
├── jobs.py             # Manajemen status background thread & cache
├── static/
│   ├── tokens.css      # Desain token warna neo-brutalist & tipografi
│   ├── style.css       # Gaya tampilan UI, kartu stiker, dan responsivitas
│   └── app.js          # Logika frontend, polling progress, dan live split preview
├── templates/
│   └── index.html      # Tampilan utama tabbed UI Slidekit
├── tests/              # Test suite pytest
├── .env                # Variabel lingkungan lokal (kunci API)
└── requirements.txt    # Dependensi pustaka Python
```
