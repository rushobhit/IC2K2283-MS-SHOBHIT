import cv2
import matplotlib.pyplot as plt

img = cv2.imread("D:/IC2K2283-MS-SHOBHIT/Multimedia-Systems-Lab/datasets/universe.jpg")

# Handle case where image path is invalid or file doesn't exist
if img is None:
    raise FileNotFoundError("Could not read 'sample.jpg'. Ensure the path is correct.")

# Print image metadata
print("shape :", img.shape)    # (height, width, 3)
print("dtype :", img.dtype)    # uint8 → values 0..255
print("min/max:", img.min(), img.max())

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("gray shape:", gray.shape)  # (height, width)

# Display images side-by-side
plt.figure(figsize=(10, 5))

plt.subplot(1, 2, 1)
plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
plt.title("RGB Image")
plt.axis('off')

plt.subplot(1, 2, 2)
plt.imshow(gray, cmap='gray')
plt.title("Grayscale Image")
plt.axis('off')

plt.tight_layout()
plt.show()