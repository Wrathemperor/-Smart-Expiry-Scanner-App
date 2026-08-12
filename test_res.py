import cv2
import pytesseract
from PIL import Image
import statistics

img_path = 'app/images/783d0947-7d46-43b3-8777-e745d99e4f46.jpg'
orig = cv2.imread(img_path)

gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)

# Also try upscaling by 2x just in case
upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

variants = {
    'orig_gray': gray,
    'orig_upscaled': upscaled
}

for name, var_img in variants.items():
    pil_img = Image.fromarray(cv2.cvtColor(var_img, cv2.COLOR_GRAY2RGB))
    
    data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config='--psm 11')
    text = pytesseract.image_to_string(pil_img, config='--psm 11')
    confs = [float(c) for c in data['conf'] if str(c) != '-1']
    avg_conf = statistics.mean(confs) if confs else 0.0
    print(f"--- Variant {name} ---")
    print(f"Avg Conf: {avg_conf}")
    lines = [l for l in text.split('\n') if len(l.strip()) > 3]
    for l in lines:
        if '2026' in l or 'EXP' in l.upper() or 'BEFORE' in l.upper() or '26' in l or 'BB' in l.upper() or 'MFD' in l.upper():
            print(f"Line: {l}")
