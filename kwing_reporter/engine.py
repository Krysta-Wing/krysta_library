import os
from datetime import datetime
from jinja2 import Template

class ModelReport:
    def __init__(self, week: int, model_name: str, modality: str):
        self.artifact_counter = 0
        self.week = week
        self.model_name = model_name
        self.modality = modality.lower()
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Setup path tracking
        self.year = datetime.now().strftime("%Y")
        self.folder_name = f"week-{self.week}_{self.model_name}"
        self.report_dir = os.path.join("workspace_reports", self.year, self.folder_name)
        self.artifacts_dir = os.path.join(self.report_dir, "artifacts")
        
        # 2. Automatically create the folders if they don't exist
        os.makedirs(self.artifacts_dir, exist_ok=True)
        
        # 3. Baseline storage dictionary for metrics
        self.metrics = {}
        self.logged_artifacts = []

    def log_benchmarks(self, latency: float, vram: float, loss: float):
        """Logs standard performance engineering parameters."""
        self.metrics["latency"] = latency
        self.metrics["vram"] = vram
        self.metrics["loss"] = round(loss, 4)

    def log_vision_artifact(self, image_matrix, title: str = "Model Attention Heatmap"):
        """Captures a visual matrix, names it uniquely, and saves it to disk."""
        from .modalities.vision import save_analysis_plot

        self.artifact_counter += 1
        filename = f"artifact_{self.artifact_counter}.png"
        target_path = os.path.join(self.artifacts_dir, filename)

        # Call our modality function to save the image file
        save_analysis_plot(image_matrix, target_path, title)

        # Store relative path for markdown embedding (using forward slashes for Markdown compatibility)
        relative_markdown_path = f"artifacts/{filename}"
        self.logged_artifacts.append((title, relative_markdown_path))

        print(f"[✓] Visual artifact saved to: {target_path}")

    def log_text_artifact(self, tokens: list, confidences: list, sample_phrase: str, threshold: float = 0.5):
        """Processes NLP evaluation data and catches text extraction anomalies."""
        from .modalities.text import analyze_token_confidence
        
        # Run the sub-module analysis
        low_conf_words = analyze_token_confidence(tokens, confidences, threshold)
        
        # Build a raw text summary block
        text_summary = f"#### Evaluated Sequence Sample:\n`\"{sample_phrase}\"`\n\n"
        if low_conf_words:
            text_summary += f"⚠️ **Low Confidence Anomaly Tokens (Below {int(threshold*100)}%):**\n"
            text_summary += f"{', '.join(low_conf_words)}\n"
        else:
            text_summary += "✓ **All tokens parsed with high confidence spectral safety.**\n"
            
        # Store it to be compiled later
        if not hasattr(self, 'logged_text_blocks'):
            self.logged_text_blocks = []
        self.logged_text_blocks.append(text_summary)
        
        print(f"[✓] Text analysis artifact logged for sequence.")

    def log_audio_artifact(self, raw_audio_array, title: str = "Audio Mel-Spectrogram"):
        """Processes raw audio data arrays, converts to a spectrogram, and logs the path."""
        from .modalities.audio import save_spectrogram_plot
        
        self.artifact_counter += 1
        filename = f"audio_artifact_{self.artifact_counter}.png"
        target_path = os.path.join(self.artifacts_dir, filename)
        
        # Call our audio module to save the spectrogram image
        save_spectrogram_plot(raw_audio_array, target_path, title)
        
        # Store relative path for markdown embedding
        relative_markdown_path = f"artifacts/{filename}"
        if not hasattr(self, 'logged_artifacts'):
            self.logged_artifacts = []
        self.logged_artifacts.append((title, relative_markdown_path))
        
        print(f"[✓] Audio spectrogram artifact saved to: {target_path}")

    def compile(self):
        """Reads template, hydrates variables, and exports the final file."""
        # Find the template relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", "base_report.md")
        
        with open(template_path, "r") as f:
            raw_template = f.read()
            
        # Initialize Jinja2 Template
        template = Template(raw_template)
        
        # Create a placeholder block for modality content until we build those modules
        modality_content = f"### {self.modality.upper()} EXTRAPOLATION INSIGHTS\n\n"
        
        if self.modality in ["vision", "audio"]:
            if hasattr(self, 'logged_artifacts') and self.logged_artifacts:
                for title, path in self.logged_artifacts:
                    modality_content += f"#### {title}\n![{title}]({path})\n\n"
            else:
                modality_content += "*No visual or audio artifacts logged for this run.*"
                
        elif self.modality == "text":
            if hasattr(self, 'logged_text_blocks') and self.logged_text_blocks:
                for block in self.logged_text_blocks:
                    modality_content += block
            else:
                modality_content += "*No text data blocks logged for this run.*"
        
        # Render/Hydrate the template with our data
        rendered_md = template.render(
            model_name=self.model_name,
            week=self.week,
            timestamp=self.timestamp,
            modality=self.modality,
            latency=self.metrics.get("latency", 0.0),
            vram=self.metrics.get("vram", 0.0),
            loss=self.metrics.get("loss", 0.0),
            modality_specific_content=modality_content
        )
        
        # Save the finalized report file
        output_file_path = os.path.join(self.report_dir, "report.md")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(rendered_md)
            
        print(f"[✓] Report successfully compiled at: {output_file_path}")