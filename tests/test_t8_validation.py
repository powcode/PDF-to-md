import pytest
from describe import count_sentences, get_cache_key, build_instruction

def test_count_sentences():
    # 1 sentence
    assert count_sentences("Ini adalah satu kalimat tunggal.") == 1
    # 2 sentences
    assert count_sentences("Diagram ini menunjukkan alur data. Nilai presisi mencapai 95%.") == 2
    # 3 sentences
    assert count_sentences("Ini kalimat pertama. Ini kalimat kedua! Ini kalimat ketiga?") == 3
    # 4 sentences
    assert count_sentences("Satu. Dua. Tiga. Empat.") == 4
    # Number with decimals should not split (e.g. 1.500 or 3.14)
    assert count_sentences("Model mencapai akurasi 98.5% pada data uji. Nilai F1-score adalah 0.94.") == 2

def test_cache_key():
    k1 = get_cache_key(b"image_bytes", "gemini-3.5-flash", "prompt 1")
    k2 = get_cache_key(b"image_bytes", "gemini-3.5-flash", "prompt 1")
    k3 = get_cache_key(b"other_bytes", "gemini-3.5-flash", "prompt 1")
    assert k1 == k2
    assert k1 != k3
