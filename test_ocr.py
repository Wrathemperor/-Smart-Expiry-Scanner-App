import cv2
import pytesseract
from PIL import Image
import statistics
import os

img_path = 'app/images/783d0947-7d46-43b3-8777-e745d99e4f46.jpg'
orig = cv2.imread(img_path)
h, w = orig.shape[:2]
max_w = 1600
if w > max_w:
    scale = max_w / float(w)
    img = cv2.resize(orig, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
else:
    img = orig.copy()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
denoised = cv2.bilateralFilter(gray, 9, 75, 75)
adaptive = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
_, otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

variants = {
    'original': img,
    'gray': gray,
    'denoised': denoised,
    'adaptive': adaptive,
    'otsu': otsu,
    'upscaled': upscaled
}

psms = [6, 11, 12]

os.makedirs('debug_ocr', exist_ok=True)

for name, var_img in variants.items():
    if len(var_img.shape) == 2:
        pil_img = Image.fromarray(cv2.cvtColor(var_img, cv2.COLOR_GRAY2RGB))
    else:
        pil_img = Image.fromarray(cv2.cvtColor(var_img, cv2.COLOR_BGR2RGB))
    
    pil_img.save(f'debug_ocr/{name}.png')

    for psm in psms:
        custom_config = f'--psm {psm}'
        try:
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config=custom_config)
            text = pytesseract.image_to_string(pil_img, config=custom_config)
            confs = [float(c) for c in data['conf'] if str(c) != '-1']
            avg_conf = statistics.mean(confs) if confs else 0.0
            print(f"--- Variant: {name}, PSM: {psm} ---")
            print(f"Avg Conf: {avg_conf}")
            # print(f"Text: {text[:200]}...") # truncated to avoid spam
            lines = [l for l in text.split('\n') if l.strip()]
            for l in lines:
                if '2026' in l or 'EXP' in l.upper() or 'BB' in l.upper() or 'BEFORE' in l.upper():
                    print(f"Found candidate line: {l}")
        except Exception as e:
            print(f"Error {name} {psm}: {e}")
