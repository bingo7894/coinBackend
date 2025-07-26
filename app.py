# app.py (ไฟล์ที่แก้ไข)

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import uvicorn
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", # สำหรับ local dev
        "https://coin5-hgaq1cb4c-bingo7894s-projects.vercel.app" # <<--- URL จริงของ Vercel App คุณ
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

model = YOLO("best.pt")

COIN_VALUES = {
    "025": 0.25,
    "050": 0.5,
    "1": 1,
    "2": 2,
    "5": 5,
    "10": 10,
}

# สีสำหรับแต่ละ class (RGB)
CLASS_COLORS = {
    "025": (255, 99, 132),   # สีชมพูแดง
    "050": (54, 162, 235),   # สีฟ้า
    "1": (255, 205, 86),     # สีเหลือง
    "2": (75, 192, 192),     # สีเทอร์ควอยซ์
    "5": (153, 102, 255),    # สีม่วง
    "10": (255, 159, 64),    # สีส้ม
}

def get_class_color(class_name):
    """ได้รับสีสำหรับ class หรือสุ่มสีใหม่หากไม่มี"""
    if class_name in CLASS_COLORS:
        return CLASS_COLORS[class_name]
    else:
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def crop_and_encode(image: Image.Image, box: list):
    cropped = image.crop((box[0], box[1], box[2], box[3]))
    buffered = io.BytesIO()
    # ลดคุณภาพของรูปภาพที่ croped แล้วด้วย เพื่อลดขนาดของ Base64 ของแต่ละเหรียญ
    cropped.save(buffered, format="JPEG", quality=75) # ปรับคุณภาพ
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def draw_boxes(image: Image.Image, boxes: list, labels: list, confidences: list = None):
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    for i, (box, label) in enumerate(zip(boxes, labels)):
        # แปลงพิกัดเป็น int
        x1, y1, x2, y2 = map(int, box)
        color = get_class_color(label)
        
        # วาดกรอบสี่เหลี่ยม
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        display_text = f"{label}"
        if confidences and i < len(confidences):
            display_text += f" ({confidences[i]:.2f})"
        
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # กำหนดตำแหน่งพื้นหลังข้อความ
        text_bg_x1 = x1
        text_bg_y1 = y1 - text_height - 8
        text_bg_x2 = x1 + text_width + 8
        text_bg_y2 = y1
        
        if text_bg_y1 < 0:
            text_bg_y1 = y2
            text_bg_y2 = y2 + text_height + 8
        
        # วาดพื้นหลังข้อความ
        draw.rectangle([text_bg_x1, text_bg_y1, text_bg_x2, text_bg_y2], fill=color)
        
        text_x = text_bg_x1 + 4
        text_y = text_bg_y1 + 4
        
        # วาดข้อความสีขาว
        draw.text((text_x, text_y), display_text, fill="white", font=font)
    
    return image

@app.post("/api/process-image")
async def process_image(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    
    results = model(image)
    
    counts = {}
    details = []
    total_count = 0
    total_value = 0.0
    coins_with_images = []
    
    all_boxes = []
    all_labels = []
    all_confidences = []
    
    for result in results:
        for box, cls, conf in zip(result.boxes.xyxy, result.boxes.cls, result.boxes.conf):
            class_id = int(cls.item())
            class_name = model.names[class_id]
            box_list = box.tolist()
            confidence = conf.item()
            
            counts[class_name] = counts.get(class_name, 0) + 1
            
            # ใช้ฟังก์ชัน crop_and_encode ที่ปรับคุณภาพแล้ว
            cropped_img_base64 = crop_and_encode(image, box_list)
            
            coins_with_images.append({
                "type": class_name,
                "bbox": box_list,
                "confidence": confidence,
                "image": cropped_img_base64
            })
            
            all_boxes.append(box_list)
            all_labels.append(class_name)
            all_confidences.append(confidence)
    
    labeled_image = draw_boxes(image.copy(), all_boxes, all_labels, all_confidences)
    
    buffered = io.BytesIO()
    # ลดคุณภาพของรูปภาพรวมที่ label แล้ว
    labeled_image.save(buffered, format="JPEG", quality=75) # ปรับคุณภาพจาก 95 เป็น 75
    labeled_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    for coin_type, count in counts.items():
        value = COIN_VALUES.get(coin_type, 0) * count
        details.append({
            "type": coin_type,
            "count": count,
            "value": value,
            "color": CLASS_COLORS.get(coin_type, (128, 128, 128))
        })
        total_count += count
        total_value += value
    
    return {
        "count": total_count,
        "totalValue": total_value,
        "details": details,
        "coins": coins_with_images,
        "labeledImage": f"data:image/jpeg;base64,{labeled_base64}",
        "classColors": CLASS_COLORS
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
