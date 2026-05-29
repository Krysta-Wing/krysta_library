import os
import matplotlib.pyplot as plt

def save_spectrogram_plot(audio_signal_data, target_path: str, title: str):
    """
    Takes an audio signal array, generates a mock Mel-Spectrogram visualization,
    and saves it to the artifacts repository.
    """
    plt.figure(figsize=(7, 3))
    
    # Create a nice visual representation resembling an audio waveform/spectrogram frequency
    plt.specgram(audio_signal_data, NFFT=64, Fs=2, noverlap=32, cmap="magma")
    
    plt.title(title, fontsize=10, fontweight='bold')
    plt.xlabel("Time (s)", fontsize=8)
    plt.ylabel("Frequency (Hz)", fontsize=8)
    
    plt.savefig(target_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()