import os
import time
from datetime import datetime
import yaml
from jinja2 import Template

class ModelReport:
    def __init__(self, week: int, model_name: str, modality: str):
        self.week = week
        self.model_name = model_name
        self.modality = modality
        self.artifact_counter = 0
        
        # Core data metrics and artifact trackers
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.metrics = {} 
        self.logged_artifacts = []
        self.logged_text_blocks = []
        
        # 1. Load configuration profiles safely
        self.config = self._load_global_config()
        
        # 2. Extract workspace paths from config or default back to standard pathways
        base_workspace = self.config.get("workspace_root", "workspace_reports")
        self.output_dir = os.path.join(base_workspace, "2026", f"week-{week}_{model_name}")
        self.report_dir = self.output_dir  
        self.artifacts_dir = os.path.join(self.output_dir, "artifacts")
        
        os.makedirs(self.artifacts_dir, exist_ok=True)
        
    def _load_global_config(self):
        """Looks for a local kwing_config.yaml file in the user's working directory."""
        config_filename = "kwing_config.yaml"
        default_config = {
            "workspace_root": "workspace_reports",
            "thresholds": {
                "token_confidence": 0.50,
                "vram_limit_mb": 4000.0,
                "latency_limit_ms": 100.0
            }
        }
        
        if os.path.exists(config_filename):
            try:
                with open(config_filename, "r") as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        print("[INFO] Krysta :: NoA loaded runtime profile from kwing_config.yaml")
                        return user_config
            except Exception as e:
                print(f"[WARN] Krysta :: NoA configuration parsing failed ({e}). using defaults.")
                
        return default_config

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

        save_analysis_plot(image_matrix, target_path, title)

        relative_markdown_path = f"artifacts/{filename}"
        self.logged_artifacts.append((title, relative_markdown_path))

        print(f"[✓] Visual artifact saved to: {target_path}")

    def log_text_artifact(self, tokens: list, confidences: list, sample_phrase: str, threshold: float = 0.5):
        """Processes NLP evaluation data and catches text extraction anomalies."""
        from .modalities.text import analyze_token_confidence
        
        low_conf_words = analyze_token_confidence(tokens, confidences, threshold)
        
        text_summary = f"#### Evaluated Sequence Sample:\n`\"{sample_phrase}\"`\n\n"
        if low_conf_words:
            text_summary += f"**Low Confidence Anomaly Tokens (Below {int(threshold*100)}%):**\n"
            text_summary += f"{', '.join(low_conf_words)}\n"
        else:
            text_summary += "✓ **All tokens parsed with high confidence spectral safety.**\n"
            
        self.logged_text_blocks.append(text_summary)
        print(f"[✓] Text analysis artifact logged for sequence.")

    def log_audio_artifact(self, raw_audio_array, title: str = "Audio Mel-Spectrogram"):
        """Processes raw audio data arrays, converts to a spectrogram, and logs the path."""
        from .modalities.audio import save_spectrogram_plot
        
        self.artifact_counter += 1
        filename = f"audio_artifact_{self.artifact_counter}.png"
        target_path = os.path.join(self.artifacts_dir, filename)
        
        save_spectrogram_plot(raw_audio_array, target_path, title)
        
        relative_markdown_path = f"artifacts/{filename}"
        self.logged_artifacts.append((title, relative_markdown_path))
        
        print(f"[✓] Audio spectrogram artifact saved to: {target_path}")

    def log_custom_artifact(self, data, artifact_type: str, title: str, **kwargs):
        """Universal gateway method routing data dynamically to modality processors."""
        self.artifact_counter += 1
        
        # Route 1: Vision / Spatial Heatmaps
        if artifact_type == "heatmap":
            from .modalities.vision import save_analysis_plot
            filename = f"custom_vision_{self.artifact_counter}.png"
            target_path = os.path.join(self.artifacts_dir, filename)
            save_analysis_plot(data, target_path, title)
            self.logged_artifacts.append((title, f"artifacts/{filename}"))
            print(f"[CORE] Krysta :: NoA registered vision artifact ↳ {filename}")

        # Route 2: Text Token Streams
        elif artifact_type == "tokens":
            from .modalities.text import analyze_token_confidence
            confidences = kwargs.get("confidences", [])
            sample_phrase = kwargs.get("sample_phrase", "Raw Token String Segment Passed")

            config_threshold = self.config.get("thresholds", {}).get("token_confidence", 0.50)
            threshold = kwargs.get("threshold", config_threshold)
            
            low_conf_words = analyze_token_confidence(data, confidences, threshold)
            
            text_summary = f"#### Custom Token Stream Analysis: {title}\n"
            text_summary += f"`\"{sample_phrase}\"`\n\n"
            if low_conf_words:
                text_summary += f"**Low Confidence Anomaly Tokens (Below {int(threshold*100)}%):**\n"
                text_summary += f"{', '.join(low_conf_words)}\n\n"
            else:
                text_summary += "**All tokens parsed securely above target boundary criteria.**\n\n"
            
            self.logged_text_blocks.append(text_summary)
            print(f"[CORE] Krysta :: NoA registered text token anomalies")

        # Route 3: Audio Waveform Signals
        elif artifact_type == "audio":
            from .modalities.audio import save_spectrogram_plot
            filename = f"custom_audio_{self.artifact_counter}.png"
            target_path = os.path.join(self.artifacts_dir, filename)
            save_spectrogram_plot(data, target_path, title)
            self.logged_artifacts.append((title, f"artifacts/{filename}"))
            print(f"[✓] Krysta :: NoA Logged Audio Spectrogram -> {filename}")

        else:
            raise ValueError(f"Unsupported artifact type variant: '{artifact_type}'. Choose 'heatmap', 'tokens', or 'audio'.")

    def compile(self):
        """Reads template, hydrates variables, and exports the final file report."""
        regression_alerts = self._compute_regression_analysis()
        current_dir = os.path.dirname(os.path.abspath(__file__))
            
        # Explicit top-level variables used instead of a nested metrics dictionary
        template_content = """# Model Evaluation Summary: {{ model_name }}
Generated by Krysta NoA on: {{ timestamp }} | Week: {{ week }} | Modality: {{ modality }}

## Performance Benchmarks
- **Loss Rating:** {{ loss }}
- **VRAM Footprint:** {{ vram }} MB
- **Latency Overlap:** {{ latency }} ms

## Logged Metrics Analysis
{% for block in text_blocks %}
{{ block }}
{% endfor %}

## Regression Alerts
{% for alert in regression_alerts %}
- {{ alert }}
{% endfor %}

## Visual Artifact References
{% for title, path in artifacts %}
### {{ title }}
![{{ title }}]({{ path }})
{% endfor %}
"""
            
        template_path = os.path.join(current_dir, "templates", "base_report.md")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

        # Safely extract metrics values with clear defaults to pass to Jinja
        latency_val = self.metrics.get("latency", 0.0)
        vram_val = self.metrics.get("vram", 0.0)
        loss_val = self.metrics.get("loss", 0.0)

        # Render the template by defining every single variable explicitly
        template = Template(template_content)
        rendered_report = template.render(
            model_name=self.model_name,
            timestamp=self.timestamp,
            week=self.week,
            modality=self.modality,
            latency=latency_val,
            vram=vram_val,
            loss=loss_val,
            text_blocks=self.logged_text_blocks,
            artifacts=self.logged_artifacts,
            regression_alerts=regression_alerts
        )

        # Write output file report to the folder path
        report_filename = f"report_week_{self.week}_{self.model_name.lower()}.md"
        final_output_path = os.path.join(self.report_dir, report_filename)
            
        with open(final_output_path, "w", encoding="utf-8") as f:
            f.write(rendered_report)
                
        print(f"\n[SUCCESS] Krysta :: NoA Evaluation report compiled flawlessly at: {final_output_path}")



    def _compute_regression_analysis(self):
        """
        Saves run metrics locally and runs a 2-sigma anomaly verification pass 
        against historical evaluation baselines.
        """
        import json
        history_file = ".kwing_history.json"
        
        # Pull current performance parameters cleanly
        current_latency = self.metrics.get("latency", 0.0)
        current_vram = self.metrics.get("vram", 0.0)
        
        # Load historical benchmarks state
        history_data = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    history_data = json.load(f)
            except Exception:
                history_data = []

        regression_alerts = []

        # Run statistical checks only if we have a viable baseline (minimum 3 historical runs)
        if len(history_data) >= 3:
            import math
            
            latencies = [run["latency"] for run in history_data if "latency" in run]
            vrams = [run["vram"] for run in history_data if "vram" in run]
            
            def calculate_stats(data_list):
                mean = sum(data_list) / len(data_list)
                variance = sum((x - mean) ** 2 for x in data_list) / len(data_list)
                std_dev = math.sqrt(variance)
                return mean, std_dev

            # Check 1: Latency Regression Spike Checks
            if latencies:
                mean_lat, std_lat = calculate_stats(latencies)
                # If standard deviation is near zero, protect against false positives by setting a minimum window
                threshold_lat = mean_lat + max(2 * std_lat, 5.0) 
                if current_latency > threshold_lat:
                    regression_alerts.append(
                        f"**PERFORMANCE REGRESSION:** Inference Latency spiked to **{current_latency:.1f}ms** "
                        f"(Historical Baseline: {mean_lat:.1f}ms ± {std_lat:.1f}ms). Exceeded 2σ limit threshold."
                    )

            # Check 2: Graphics Memory Allocation Checks
            if vrams:
                mean_vram, std_vram = calculate_stats(vrams)
                threshold_vram = mean_vram + max(2 * std_vram, 256.0)
                if current_vram > threshold_vram:
                    regression_alerts.append(
                        f"**RESOURCE ANOMALY:** Peak VRAM consumption reached **{current_vram:.1f}MB** "
                        f"(Historical Baseline: {mean_vram:.1f}MB ± {std_vram:.1f}MB). Potential memory leak detected."
                    )

        # Append the current profile parameters safely to history logs
        history_data.append({
            "timestamp": self.timestamp,
            "model_name": self.model_name,
            "week": self.week,
            "latency": current_latency,
            "vram": current_vram,
            "loss": self.metrics.get("loss", 0.0)
        })

        try:
            with open(history_file, "w") as f:
                json.dump(history_data, f, indent=4)
        except Exception as e:
            print(f"Warning: Unable to save runtime profile data to history store ({e})")

        return regression_alerts