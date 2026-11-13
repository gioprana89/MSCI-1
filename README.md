# Paper ke-4 · MSCI Indonesia

**Versi 0.3 · Data sampai 13 November 2026**

- `Protokol_Analisis_v0_3.md` memuat keputusan pascapilot.
- `Methods_and_Results_EN.md` memuat draf naskah bahasa Inggris.
- `results/` memuat audit 31 pembanding dan sembilan saham terdampak, pasangan, diagnostik pra-peristiwa, estimasi, distribusi placebo, dan leave-one-out.
- `figures/` memuat tiga gambar naskah dalam PNG 300 dpi dan PDF vektor.
- `app.py` membuka dashboard empat tab dari hasil yang sudah dihitung.

## Jalankan dashboard

Ekstrak ZIP dan buka terminal pada folder hasil ekstraksi. Gunakan Python 3.11 atau 3.12. Buat lingkungan virtual dengan `python -m venv .venv`, lalu aktifkan. Di PowerShell gunakan `.\.venv\Scripts\Activate.ps1`. Di macOS/Linux gunakan `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Dashboard menggunakan tabel dan gambar yang sudah ada dalam paket. Workbook mentah hanya diperlukan untuk replikasi.

## Replikasi analisis

Simpan workbook asli `Ringkasan_Saham_Gabungan.xlsx` di folder paket atau berikan path absolut.

```bash
python analisis.py --stocks Ringkasan_Saham_Gabungan.xlsx
python visualisasi.py
```

`results/metadata.json` mencatat hash input dan cakupan analisis. Sumber IHSG dicatat per tanggal. Dokumen pengumuman yang menjadi dasar flag ada di `inputs/audit_sources.json`. Status perubahan bobot MSCI dan pemeriksaan seluruh keterbukaan emiten masih terbuka. Baca bagian keterbatasan dalam draf sebelum mengutip angka sebagai hasil artikel.
