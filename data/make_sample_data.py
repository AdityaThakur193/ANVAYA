import os
import pymupdf
import wave
import math
import struct

def generate_sample_data():
    sample_dir = os.path.join("data", "sample_case")
    os.makedirs(sample_dir, exist_ok=True)
    print(f"[DATA] Creating sample data in: {sample_dir}")

    # 1. Generate sample_intel_report.pdf using PyMuPDF
    pdf_path = os.path.join(sample_dir, "sample_intel_report.pdf")
    doc = pymupdf.open()

    page1 = doc.new_page()
    page1.insert_text((50, 50), "CLASSIFIED INTEL REPORT — OPERATION ALPHA", fontsize=16)
    page1.insert_text((50, 100), "The logistics convoy is scheduled to depart Sector 7 at 04:30 AM via Northern Pass.", fontsize=12)
    page1.insert_text((50, 130), "Primary convoy vehicle registration number is RAKE-07.", fontsize=12)
    page1.insert_text((50, 160), "All escort personnel must maintain radio silence until crossing Checkpoint 4.", fontsize=12)

    page2 = doc.new_page()
    page2.insert_text((50, 50), "CLASSIFIED INTEL REPORT — PAGE 2", fontsize=16)
    page2.insert_text((50, 100), "Substation Alpha security clearance is granted under Authorization Code Bravo-9.", fontsize=12)
    page2.insert_text((50, 130), "Secondary emergency contact frequency is 142.85 MHz.", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    print(f"[OK] Generated PDF: {pdf_path}")

    # 2. Generate sample_handwritten_note.png (Image with text using PyMuPDF pixmap)
    img_doc = pymupdf.open()
    img_page = img_doc.new_page(width=600, height=300)
    img_page.insert_text((40, 50), "SEIZED EVIDENCE NOTE - CASE #402", fontsize=14)
    img_page.insert_text((40, 100), "Suspect meeting at North Highway Checkpoint at 22:00 hrs.", fontsize=12)
    img_page.insert_text((40, 130), "Cash transfer of INR 5,00,000 confirmed for equipment delivery.", fontsize=12)
    img_page.insert_text((40, 160), "Contact Alias: SHADOW-1", fontsize=12)

    pix = img_page.get_pixmap(dpi=150)
    img_path = os.path.join(sample_dir, "sample_handwritten_note.png")
    pix.save(img_path)
    img_doc.close()
    print(f"[OK] Generated Image: {img_path}")

    # 3. Generate sample_wiretap.wav (Valid 3-second audio wave file)
    wav_path = os.path.join(sample_dir, "sample_wiretap.wav")
    sample_rate = 16000
    duration_sec = 3
    num_samples = sample_rate * duration_sec
    frequency = 440.0  # 440 Hz A note tone

    with wave.open(wav_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            value = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)

    print(f"[OK] Generated Audio: {wav_path}")
    print("\n[SUCCESS] Sample Evidence Bundle Ready!")

if __name__ == "__main__":
    generate_sample_data()
