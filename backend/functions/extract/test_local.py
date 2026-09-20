import boto3
import base64
import json
import os
import glob

# Initialize AWS clients
textract = boto3.client('textract', region_name='ap-south-1')
bedrock = boto3.client('bedrock-runtime', region_name='ap-south-1')

# Get the absolute path to the root of our dosewise project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

# Now these will safely resolve no matter where you run the script from!
PROMPT_FILE = os.path.join(BASE_DIR, "backend/prompts/extraction_v1.txt")
TEST_DIR = os.path.join(BASE_DIR, "data/test-prescriptions")

MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
def get_textract_text(image_bytes):
    print("Calling Textract...")
    response = textract.detect_document_text(Document={'Bytes': image_bytes})
    
    # Extract only the LINE blocks to build a rough transcript
    lines = [block['Text'] for block in response.get('Blocks', []) if block['BlockType'] == 'LINE']
    return "\n".join(lines)

def call_bedrock(image_bytes, textract_text, system_prompt):
    print("Calling Bedrock...")
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # Format required for Claude 3 Vision on Bedrock
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Here is the raw OCR text from Textract:\n<ocr>\n{textract_text}\n</ocr>\n\nPlease extract the medicines as instructed."
                    }
                ]
            }
        ]
    })
    
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body['content'][0]['text']

def main():
    # Load your extraction prompt
    with open(PROMPT_FILE, 'r') as f:
        system_prompt = f.read()
        
    # Grab all test images
    image_paths = glob.glob(f"{TEST_DIR}/*.jpg") + glob.glob(f"{TEST_DIR}/*.jpeg")
    
    if not image_paths:
        print(f"No test images found in {TEST_DIR}. Add some .jpg files!")
        return
        
    for image_path in image_paths:
        print(f"\n--- Processing {os.path.basename(image_path)} ---")
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()
            
        try:
            textract_text = get_textract_text(image_bytes)
            extracted_json_string = call_bedrock(image_bytes, textract_text, system_prompt)
            
            print("\nExtracted JSON:")
            print(extracted_json_string)
            
            # Save the output to compare against your ground-truth answers.json
            out_path = f"{image_path}_result.json"
            with open(out_path, "w") as f:
                f.write(extracted_json_string)
                
        except Exception as e:
            print(f"Failed to process {image_path}: {e}")

if __name__ == "__main__":
    main()