#!/usr/bin/env python3
"""
Azure OpenAI / Microsoft Foundry: Image Generation with gpt-image-1.5

✅ FIXED: quality parameter
   • gpt-image-1.5 only accepts: 'low', 'medium', 'high', 'auto'
   • Changed default from 'standard' to 'high'

(Uses AZURE_OPENAI_IMAGE_MODEL so it doesn't conflict with your text model.)

Usage:
    # Export env vars first if available; .env is only used as fallback.
    python3 generate_image_gpt_image_1_5.py
"""

import base64
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime


REQUEST_TIMEOUT_SECONDS = 600
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 120


def load_dotenv(dotenv_path: str = ".env") -> dict[str, str]:
    """Load key=value pairs from a .env file (same as your original script)."""
    values: dict[str, str] = {}
    if not os.path.exists(dotenv_path):
        return values

    with open(dotenv_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
                value = value[1:-1]

            values[key] = value

    return values


def config_value(name: str, dotenv_values: dict[str, str], default: str | None = None) -> str | None:
    """Return env var first, then .env value, then default."""
    return os.getenv(name) or dotenv_values.get(name) or default


def post_json_with_retries(request: urllib.request.Request, timeout: int, max_attempts: int) -> str:
    """Retry transient network failures that can happen on long-running image requests."""
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            details = err.read().decode("utf-8", errors="replace")
            retryable = err.code in {408, 429, 500, 502, 503, 504}
            if retryable and attempt < max_attempts:
                print(
                    f"HTTP {err.code} from Azure OpenAI. Retrying in {RETRY_DELAY_SECONDS}s "
                    f"({attempt}/{max_attempts})...",
                    file=sys.stderr,
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            raise RuntimeError(f"HTTP {err.code}: {details}") from err
        except (http.client.RemoteDisconnected, TimeoutError, urllib.error.URLError) as err:
            if attempt < max_attempts:
                print(
                    f"Transient request failure: {err}. Retrying in {RETRY_DELAY_SECONDS}s "
                    f"({attempt}/{max_attempts})...",
                    file=sys.stderr,
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            raise RuntimeError(f"Request failed after {max_attempts} attempts: {err}") from err

    raise RuntimeError("Request failed without producing a response.")


def main() -> int:
    config_names = {
        "AZURE_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_IMAGE_MODEL",
    }
    dotenv_values = load_dotenv() if any(not os.getenv(name) for name in config_names) else {}

    api_key = config_value("AZURE_API_KEY", dotenv_values)
    if not api_key:
        print("Error: AZURE_API_KEY is not set (env or .env).", file=sys.stderr)
        return 1

    endpoint = config_value("AZURE_OPENAI_ENDPOINT", dotenv_values, "https://jls.openai.azure.com")
    api_version = config_value("AZURE_OPENAI_API_VERSION", dotenv_values, "2025-04-01-preview")
    model = config_value("AZURE_OPENAI_IMAGE_MODEL", dotenv_values, "gpt-image-1.5")

    if not endpoint or not api_version or not model:
        print("Error: Missing required Azure OpenAI configuration.", file=sys.stderr)
        return 1

    endpoint = endpoint.rstrip("/")

    # Correct deployment-scoped endpoint for gpt-image-1.5
    url = f"{endpoint}/openai/deployments/{model}/images/generations?api-version={api_version}"

    # Customize your prompt here
    prompt = """A highly detailed mythological fantasy illustration in a soft, ethereal, storybook style.

Full length portrait, full body view, head-to-toe composition of Lord Rama, Vishnu’s divine avatar and the embodiment of Dharma (righteousness) and ideal manhood (Maryada Purushottama). He is the pinnacle of celestial masculine beauty, noble grace, and divine heroism — whose righteous form and unyielding character inspired the universe. He is portrayed with idealized yet powerful anatomy, harmonious proportions, broad shoulders, long elegant arms reaching towards his knees, slender waist, strong yet graceful limbs, and a dignified standing posture with one leg slightly bent in a heroic and graceful stance while holding his divine bow.

His face is extraordinarily handsome and noble, with symmetrical refined features, deep blue luminous skin with warm golden undertones that glow with divine radiance, softly defined jawline, a refined high nose, full naturally tinted lips with a gentle serene expression, and large expressive lotus-like eyes filled with compassion, wisdom, courage, and tranquil strength. His gaze should feel intensely calming yet powerfully magnetic — gentle, righteous, and heroic — paired with a soft, benevolent smile that radiates divine confidence, moral strength, and inner peace.

His hair is long, dark, and luxuriously flowing, neatly styled beneath an ornate golden crown adorned with jewels and a subtle halo of divine light. Fragrant tulsi and flower garlands adorn his neck and shoulders, enhancing his regal and sacred presence.

His deep blue, radiant skin appears smooth, softly glowing, and infused with divine golden luminosity, flawless and transcendent, emphasizing noble masculine beauty, strength, and celestial elegance in every detail of his full form.

He is adorned in traditional flowing celestial silks in vibrant saffron orange and soft gold hues (pitambara style), with a gracefully draped upper cloth over one shoulder and a dhoti tied elegantly. These lightweight fabrics move beautifully with soft folds, accentuating his athletic yet graceful physique while maintaining royal dignity.

Include a luminous ornamental halo with intricate radial patterns that softly blends into the glowing atmosphere, reinforcing his divine Vishnu-avatar nature. He holds his iconic mighty bow (Kodanda) gracefully in one hand with elegant fingers, exuding readiness and power. A quiver of arrows rests on his back. The surrounding nature is a sacred forest river landscape at golden hour, with ancient trees, gentle mist, and blooming flowers framing him beautifully.

The overall composition is a centered full length portrait with Lord Rama as the dominant and emotional focal point, occupying most of the vertical frame from head to toe, making his noble beauty, heroic posture, exquisite ornamentation, and divine righteousness the clear visual and emotional center while the sacred natural elements serve as a beautifully framed backdrop.

Lighting must be diffused and painterly with warm gold tones, soft highlights, no harsh shadows, and a gentle atmospheric haze. The overall color palette should emphasize warm gold, vibrant saffron orange, deep blues, soft greens, ivory, and subtle floral tones.

Rendering style: ultra-detailed digital painting, classical mythological illustration, soft-focus glow, painterly textures, smooth skin gradients, high detail in jewelry and fabrics, cinematic composition, harmonious balance, fantasy realism, sacred and divine mood, with strong emphasis on noble masculine beauty, heroic grace, righteousness, and celestial elegance.

"""

    payload = {
        "prompt": prompt,
        "n": 1,                    # number of images to generate
        "size": "1024x1536",       # supported: 1024x1024, 1024x1536, 1536x1024
        "quality": "high",         # ← FIXED: only 'low', 'medium', 'high', 'auto' allowed
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    print(f"Generating image with model: {model} ...")
    try:
        response_data = post_json_with_retries(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_attempts=MAX_RETRIES + 1,
        )
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1

    response_json = json.loads(response_data)

    # Extract base64 image data (gpt-image-1.5 always returns b64_json)
    try:
        b64_data = response_json["data"][0]["b64_json"]
        image_bytes = base64.b64decode(b64_data)
    except (KeyError, IndexError, TypeError):
        print("Unexpected response format:", json.dumps(response_json, indent=2), file=sys.stderr)
        return 1

    # Save image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"generated_image_{timestamp}.png"
    output_dir = "image_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"\n✅ Image successfully generated and saved as:")
    print(f"   {output_path}")
    print(f"\nPrompt used : {prompt}")
    print(f"Model        : {model}")
    print(f"Size         : {payload['size']}")
    print(f"Quality      : {payload['quality']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
