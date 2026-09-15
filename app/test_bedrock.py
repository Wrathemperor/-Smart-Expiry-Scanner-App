import boto3
from botocore.exceptions import ClientError

IMAGE_PATH = r"D:\Projects\gateway-server\app\images\IMG_20260817_010249.jpg"
REGION = "us-east-1"
  # Note: Ensure your region is ap-south-1 or us-east-1 based on your Bedrock setup
MODEL_ID = "amazon.nova-lite-v1:0"

def main():
    print("Creating Bedrock Runtime client....")
    client = boto3.client(
        "bedrock-runtime",
        region_name=REGION
    )
    print(f"Reading image: {IMAGE_PATH}")
    # Read the image using OpenCV
    import cv2
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise OSError("Could not read image")

    # Downscale if the image's largest side is greater than 1024px
    h, w = img.shape[:2]
    max_side = 1500
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    # Encode with 80% JPEG quality to compress the payload size
    success, encoded_img = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    image_bytes = encoded_img.tobytes()
    
    print(f"Compressed image size: {len(image_bytes):,} bytes")


    # with open(IMAGE_PATH, "rb") as image_file:
    #     image_bytes = image_file.read()
    print(f"Image size: {len(image_bytes):,} bytes")
    print("Sending request to Amazon Nova Lite...")

    # boto3 expects lowercase d: modelId
    response = client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "jpeg",
                            "source": {
                                "bytes": image_bytes
                            }
                        }
                    },
                        # In the messages argument:
    {
        "text": (
            "Analyse this grocery product image. "
            "Identify the product name. "
            "Locate and extract BOTH the manufacturing date (MFD/MFG) and the expiration date/use-by date (EXP). "
            "Respond in JSON format with keys: product_name, manufacturing_date, expiration_date, description"
        )
    }

                ]
            }
        ],
        inferenceConfig={
            "temperature": 0,
            "maxTokens": 300
        }
    )

    print("\n==== NOVA RESPONSE =====")
    message = response["output"]["message"]
    for content_block in message["content"]:
        if "text" in content_block:
            print(content_block["text"])

    print("\n==== USAGE ====")
    usage = response.get("usage", {})
    print(f"Input tokens: {usage.get('inputTokens', 0)}")
    print(f"Output tokens: {usage.get('outputTokens', 0)}")
    print(f"Total tokens: {usage.get('totalTokens', 0)}")


if __name__ == "__main__":
    try:
        main()
    except ClientError as e:
        print("\n==== AWS ERROR ====")
        print(e)
    except FileNotFoundError:
        print("\nERROR: Image file was not found.")
        print(IMAGE_PATH)
    except Exception as e:
        print("\n===== Error =====")
        print(type(e).__name__)
        print(e)
