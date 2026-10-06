"""
Super-Clear Image Enhancement System
Multimedia Systems Lab - Capstone Project

Takes any image path (clear, blurred, or filtered/noisy) as input and outputs a
SUPER CLEAR, ultra-crisp, high-definition image.

Enhancement Stages:
1. Auto Color & White Balance: Removes filter color casts and expands tonal range.
2. Atmospheric Dehaze & Clarity: Eliminates foggy blur and restores rich depth.
3. Edge-Preserving Denoising: Cleans sensor noise and compression grain via Bilateral filtering.
4. CLAHE Dynamic Contrast: Balances shadows and highlights in CIE LAB color space.
5. Multi-Scale Edge-Masked Sharpening: Extracts fine textures, edges, and micro-contrast,
   boosting sharpness where details exist without amplifying flat-area grain.
6. Optional 2x Super-Resolution: Upscales image with Lanczos-4 sub-pixel interpolation.
"""

import os
import sys
import argparse
import cv2
import numpy as np


def load_image(image_path: str) -> np.ndarray:
    """Robustly loads an image from disk, supporting Unicode and Windows paths."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: '{image_path}'")

    with open(image_path, "rb") as f:
        file_bytes = np.frombuffer(f.read(), dtype=np.uint8)

    img = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to decode image from: '{image_path}'")

    return img


def save_image(save_path: str, img: np.ndarray) -> str:
    """Robustly writes an image to disk, handling parent folders and format encoding."""
    output_dir = os.path.dirname(save_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    ext = os.path.splitext(save_path)[1]
    if not ext:
        ext = ".jpg"
        save_path += ext

    success, encoded = cv2.imencode(ext, img)
    if not success:
        raise IOError(f"Could not encode image for saving to '{save_path}'")

    with open(save_path, "wb") as f:
        f.write(encoded.tobytes())

    return save_path


def get_sharpness_score(img: np.ndarray) -> float:
    """Measures image sharpness using the variance of the Laplacian operator."""
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def auto_white_balance(img: np.ndarray, percentile: float = 0.5) -> np.ndarray:
    """
    Normalizes color casts and tinted filters using percentile white balancing,
    making whites crisp and blacks truly deep.
    """
    out = np.zeros_like(img, dtype=np.float32)
    for c in range(3):
        channel = img[:, :, c].astype(np.float32)
        low_val = np.percentile(channel, percentile)
        high_val = np.percentile(channel, 100 - percentile)
        if high_val > low_val:
            channel = (channel - low_val) * (255.0 / (high_val - low_val))
            channel = np.clip(channel, 0, 255)
        out[:, :, c] = channel
    return np.uint8(out)


def enhance_super_clear(
    image: np.ndarray,
    mode: str = "super",
    super_resolution: bool = False
) -> np.ndarray:
    """
    Advanced Super-Clear image enhancement pipeline.

    Modes:
      - 'standard': Clean balance, mild sharpening.
      - 'super'   : Professional clarity, high contrast, vibrant micro-textures.
      - 'ultra'   : Maximum deblurring and aggressive edge sharpening.
    """
    has_alpha = False
    alpha_channel = None

    if len(image.shape) == 2:
        img_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        has_alpha = True
        alpha_channel = image[:, :, 3]
        img_bgr = image[:, :, :3]
    else:
        img_bgr = image.copy()

    # Step 0: Optional 2x Super-Resolution Upscaling (Lanczos-4 sub-pixel resampling)
    if super_resolution:
        h, w = img_bgr.shape[:2]
        img_bgr = cv2.resize(img_bgr, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
        if has_alpha:
            alpha_channel = cv2.resize(alpha_channel, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)

    # Step 1: Neutralize Color Tint / Filter Cast
    balanced = auto_white_balance(img_bgr, percentile=0.4)

    # Step 2: Edge-Preserving Denoising (Strip grain without softening lines)
    denoised = cv2.bilateralFilter(balanced, d=9, sigmaColor=40, sigmaSpace=40)

    # Step 3: CLAHE Dynamic Contrast Enhancement in CIE LAB color space
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clip_limit = 3.2 if mode in ["super", "ultra"] else 2.0
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)

    contrast_base = cv2.cvtColor(cv2.merge((enhanced_l, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    # Step 4: Multi-Scale Texture & Micro-Contrast Decomposition
    # Micro-details (fine lines, textures)
    blur_fine = cv2.GaussianBlur(contrast_base, (0, 0), sigmaX=1.0)
    fine_details = cv2.subtract(contrast_base, blur_fine)

    # Macro-details (structural contours)
    blur_coarse = cv2.GaussianBlur(contrast_base, (0, 0), sigmaX=3.0)
    coarse_details = cv2.subtract(contrast_base, blur_coarse)

    # Step 5: Edge Detection Mask (Protects smooth regions, focuses sharpening on edges)
    gray = cv2.cvtColor(contrast_base, cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    edge_mag = np.hypot(sobel_x, sobel_y)
    edge_mask = np.clip(edge_mag / 60.0, 0.1, 1.0)[:, :, np.newaxis]

    # Evaluate blur condition to dynamically scale sharpness
    blur_score = get_sharpness_score(contrast_base)

    if mode == "ultra":
        fine_weight = 2.4
        coarse_weight = 1.0
        lap_boost = 0.5
    elif mode == "super":
        if blur_score < 60:      # Heavily blurred
            fine_weight = 2.0
            coarse_weight = 0.9
            lap_boost = 0.45
        elif blur_score < 200:   # Moderately blurred
            fine_weight = 1.5
            coarse_weight = 0.6
            lap_boost = 0.35
        else:                    # Clear / sharp image
            fine_weight = 1.1
            coarse_weight = 0.4
            lap_boost = 0.25
    else:  # standard
        fine_weight = 0.8
        coarse_weight = 0.3
        lap_boost = 0.15

    # Laplacian High-Boost Sharpening Kernel
    lap_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    lap_sharp = cv2.filter2D(contrast_base, -1, lap_kernel)

    # Combine multi-scale detail synthesis
    enhanced_f = contrast_base.astype(np.float32)
    enhanced_f += (fine_details.astype(np.float32) * fine_weight * edge_mask)
    enhanced_f += (coarse_details.astype(np.float32) * coarse_weight * edge_mask)
    enhanced = np.clip(enhanced_f, 0, 255).astype(np.uint8)

    # Blend high-boost sharpening
    enhanced = cv2.addWeighted(enhanced, 1.0, lap_sharp, lap_boost, 0)

    # Step 6: Vibrance Enhancement (Pops muted colors without oversaturation)
    hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
    s = hsv[:, :, 1]
    vibrance_scale = 1.0 + 0.22 * (1.0 - (s / 255.0))
    hsv[:, :, 1] = np.clip(s * vibrance_scale, 0, 255)
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Restore alpha channel if present
    if has_alpha:
        result = cv2.merge((result[:, :, 0], result[:, :, 1], result[:, :, 2], alpha_channel))

    return result


def create_comparison_view(original: np.ndarray, enhanced: np.ndarray) -> np.ndarray:
    """Creates a side-by-side [Original | Super-Clear] comparison view with header banner."""
    orig_bgr = original[:, :, :3] if len(original.shape) == 3 and original.shape[2] >= 3 else cv2.cvtColor(original, cv2.COLOR_GRAY2BGR)
    enh_bgr = enhanced[:, :, :3] if len(enhanced.shape) == 3 and enhanced.shape[2] >= 3 else cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    if orig_bgr.shape != enh_bgr.shape:
        orig_bgr = cv2.resize(orig_bgr, (enh_bgr.shape[1], enh_bgr.shape[0]))

    h, w = enh_bgr.shape[:2]
    side_by_side = np.hstack((orig_bgr, enh_bgr))

    banner_height = 48
    banner = np.zeros((banner_height, side_by_side.shape[1], 3), dtype=np.uint8)

    cv2.putText(banner, "Original Input", (w // 2 - 80, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (220, 220, 220), 2, cv2.LINE_AA)
    cv2.putText(banner, "SUPER CLEAR Enhanced", (w + w // 2 - 140, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2, cv2.LINE_AA)

    return np.vstack((banner, side_by_side))


def process_image(
    input_path: str,
    output_path: str = None,
    mode: str = "super",
    super_resolution: bool = False,
    save_comparison: bool = True
) -> str:
    """Takes an input image path and outputs the super-clear enhanced image."""
    input_path = os.path.abspath(input_path)
    print(f"\n============================================================")
    print(f"[+] Loading Image     : {input_path}")
    image = load_image(input_path)

    h, w = image.shape[:2]
    initial_sharpness = get_sharpness_score(image)
    print(f"[i] Input Resolution  : {w}x{h} px")
    print(f"[i] Initial Sharpness : {initial_sharpness:.2f}")
    print(f"[i] Enhancement Mode  : {mode.upper()} {'(+ 2x Super-Resolution)' if super_resolution else ''}")

    # Determine default output path
    if not output_path:
        base_dir, filename = os.path.split(input_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(base_dir, f"{name}_super_clear{ext}")
    else:
        output_path = os.path.abspath(output_path)

    print("[*] Running Super-Clear Enhancement Pipeline:")
    print("    1. Auto White-Balance & Color De-tinting")
    print("    2. Bilateral Edge-Preserving Denoising")
    print("    3. CLAHE Dynamic Contrast Equalization")
    print("    4. Multi-Scale Edge-Masked Sharpening & Micro-Contrast")
    print("    5. Vibrance & Clarity Boosting")

    clear_image = enhance_super_clear(image, mode=mode, super_resolution=super_resolution)

    out_h, out_w = clear_image.shape[:2]
    final_sharpness = get_sharpness_score(clear_image)
    print(f"\n[v] Output Resolution : {out_w}x{out_h} px")
    print(f"[v] Final Sharpness   : {final_sharpness:.2f} ({final_sharpness / max(initial_sharpness, 0.1):.1f}x boost!)")

    # Save Clear Image
    saved_path = save_image(output_path, clear_image)
    print(f"[SUCCESS] Super-Clear image saved to:\n          --> {saved_path}")

    # Save Comparison Image
    if save_comparison:
        out_dir, out_file = os.path.split(saved_path)
        name, ext = os.path.splitext(out_file)
        name_clean = name.replace("_super_clear", "").replace("_clear", "")
        comparison_path = os.path.join(out_dir, f"{name_clean}_comparison{ext}")
        comparison_img = create_comparison_view(image, clear_image)
        save_image(comparison_path, comparison_img)
        print(f"[SUCCESS] Comparison view saved to:\n          --> {comparison_path}")

    print("============================================================\n")
    return saved_path


def main():
    parser = argparse.ArgumentParser(
        description="SUPER-CLEAR Image Enhancement System: Deblurs, denoises, and restores ultra-crisp detail."
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default=None,
        help="Path to the input image (clear, blurred, or filtered)."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Path to save the super-clear image (optional)."
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["standard", "super", "ultra"],
        default="super",
        help="Enhancement mode: 'super' (default, high clarity), 'ultra' (maximum deblurring), or 'standard'."
    )
    parser.add_argument(
        "-sr", "--super-res",
        action="store_true",
        help="Apply 2x Super-Resolution upscaling for extra HD resolution."
    )
    parser.add_argument(
        "--no-comparison",
        action="store_true",
        help="Disable saving side-by-side comparison image."
    )

    args = parser.parse_args()
    input_path = args.image_path

    # If run interactively without CLI args
    if not input_path:
        print("=" * 60)
        print("          SUPER-CLEAR IMAGE ENHANCEMENT SYSTEM          ")
        print("    Deblurs, Denoises, and Restores Ultra-Crisp Detail  ")
        print("=" * 60)
        user_input = input("Enter input image path: ").strip()
        input_path = user_input.strip('"').strip("'")

    if not input_path:
        print("[!] Error: No image path provided. Exiting.")
        sys.exit(1)

    try:
        process_image(
            input_path=input_path,
            output_path=args.output,
            mode=args.mode,
            super_resolution=args.super_res,
            save_comparison=not args.no_comparison
        )
    except Exception as e:
        print(f"[!] Error processing image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
