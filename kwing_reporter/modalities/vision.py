import os
import matplotlib.pyplot as plt

def save_analysis_plot(image_data, target_path: str, title: str):
    """
    Saves a model evaluation image or heatmap to the artifacts directory.
    Accepts a standard NumPy array or PyTorch tensor (if converted to numpy).
    """
    plt.figure(figsize=(6, 6))
    plt.imshow(image_data)
    plt.title(title, fontsize=10, fontweight='bold')
    plt.axis('off')
    
    # Save with clean borders
    plt.savefig(target_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()