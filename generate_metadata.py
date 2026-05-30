import anthropic
import base64
import json
import os
import sys
from pathlib import Path
 
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
 
SYSTEM_PROMPT = """You are an expert stock photo metadata specialist. 
Analyze the provided image and return ONLY a JSON object with the following fields:
- title: A clear, descriptive title (max 200 characters)
- description: A detailed description suitable for stock licensing (max 200 characters)
- keywords: A list of 20-50 highly relevant keywords, ordered by relevance (most relevant first)
- category: The primary Shutterstock category. Must be one of: "Abstract", "Animals/Wildlife", "Arts", "Backgrounds/Textures", "Beauty/Fashion", "Buildings/Landmarks", "Business/Finance", "Celebrities", "Editorial", "Education", "Food and drink", "Healthcare/Medical", "Holidays", "Industrial", "Interiors", "Miscellaneous", "Nature", "Objects", "Parks/Outdoor", "People", "Religion", "Science", "Signs/Symbols", "Sports/Recreation", "Technology", "Transportation", "Vintage"
- license_type: Either "commercial" or "editorial" with a brief reason
 
Return ONLY valid JSON, no markdown, no explanation."""
 
 
def encode_image(image_path: Path) -> tuple[str, str]:
    ext = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    mime_type = mime_map.get(ext, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, mime_type
 
 
def analyze_image(client: anthropic.Anthropic, image_path: Path) -> dict:
    print(f"  Analyzing {image_path.name}...")
    image_data, mime_type = encode_image(image_path)
 
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analyze this stock photo and return the metadata JSON.",
                    },
                ],
            }
        ],
    )
 
    raw = message.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)
 
 
def process_folder(folder_path: str, api_key: str) -> list[dict]:
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist.")
        sys.exit(1)
 
    images = [
        f for f in folder.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
 
    if not images:
        print(f"No supported images found in '{folder_path}'.")
        sys.exit(1)
 
    print(f"Found {len(images)} image(s). Generating metadata with Claude...\n")
 
    client = anthropic.Anthropic(api_key=api_key)
    results = []
 
    for image_path in sorted(images):
        try:
            metadata = analyze_image(client, image_path)
            results.append(
                {
                    "filename": image_path.name,
                    "filepath": str(image_path.resolve()),
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "keywords": metadata.get("keywords", []),
                    "category": metadata.get("category", ""),
                    "license_type": metadata.get("license_type", "commercial"),
                    "approved": False,
                }
            )
            print(f"  ✓ Done: {image_path.name}")
        except Exception as e:
            print(f"  ✗ Error processing {image_path.name}: {e}")
 
    # Save results to JSON for the review app
    output_file = folder / "_metadata_draft.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
 
    print(f"\nMetadata saved to: {output_file}")
    return results
 
 
if __name__ == "__main__":
    import argparse
 
    parser = argparse.ArgumentParser(description="Generate Shutterstock metadata using Claude AI")
    parser.add_argument("folder", help="Path to folder containing photos")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    args = parser.parse_args()
 
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Anthropic API key required. Use --api-key or set ANTHROPIC_API_KEY env var.")
        sys.exit(1)
 
    results = process_folder(args.folder, api_key)
    print(f"\n✅ Metadata generated for {len(results)} photos.")
    print("Now run: python review_app.py <folder_path>")
 