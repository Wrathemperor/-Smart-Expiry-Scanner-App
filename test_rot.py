import cv2
import pytesseract
from PIL import Image
import statistics

img_path = 'app/images/783d0947-7d46-43b3-8777-e745d99e4f46.jpg'
orig = cv2.imread(img_path)

# try rotation
for i, rot in enumerate([None, cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE]):
    if rot is not None:
        img = cv2.rotate(orig, rot)
    else:
        img = orig.copy()
        
    h, w = img.shape[:2]
    max_w = 1600
    if w > max_w:
        scale = max_w / float(w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pil_img = Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB))
    
    data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT, config='--psm 11')
    text = pytesseract.image_to_string(pil_img, config='--psm 11')
    confs = [float(c) for c in data['conf'] if str(c) != '-1']
    avg_conf = statistics.mean(confs) if confs else 0.0
    print(f"--- Rotation {i} ---")
    print(f"Avg Conf: {avg_conf}")
    lines = [l for l in text.split('\n') if len(l.strip()) > 3]
    for l in lines:
        if '2026' in l or 'EXP' in l.upper() or 'BEFORE' in l.upper() or '26' in l:
            print(f"Line: {l}")
