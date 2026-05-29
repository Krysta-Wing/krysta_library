import os
from datetime import datetime
from jinja2 import Template
import yaml
import time

class ModelReport:
    def __init__(self, week: int, model_name: str, modality: str):
        self.week = week
        self.model_name = model_name
        self.modality = modality
        self.artifact_counter = 0
        
        # Core data metrics trackers
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.metrics = {} 
        
        # 1. Load configuration profiles safely
        self.config = self._load_global_config()
        
        # 2. Extract workspace paths from config or default back to standard pathways
        base_workspace = self.config.get("workspace_root", "workspace_reports")
        self.output_dir = os.path.join(base_workspace, "2026", f"week-{week}_{model_name}")
        self.report_dir = self.output_dir  # Add this line to fix the final compile directory lookup
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
                        # Clean, industrial CLI layout
                        print("[INFO] krysta-wing :: loaded runtime profile from kwing_config.yaml")
                        return user_config
            except Exception as e:
                print(f"[WARN] krysta-wing :: configuration parsing failed ({e}). using defaults.")
                
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
            text_summary += f"⚠️ **Low Confidence Anomaly Tokens (Below {int(threshold*100)}%):**\n"
            text_summary += f"{', '.join(low_conf_words)}\n"
        else:
            text_summary += "✓ **All tokens parsed with high confidence spectral safety.**\n"
            
        
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
        
        
        save_spectrogram_plot(raw_audio_array, target_path, title)
        
        
        relative_markdown_path = f"artifacts/{filename}"
        if not hasattr(self, 'logged_artifacts'):
            self.logged_artifacts = []
        self.logged_artifacts.append((title, relative_markdown_path))
        
        print(f"[✓] Audio spectrogram artifact saved to: {target_path}")

    def log_custom_artifact(self, data, artifact_type: str, title: str, **kwargs):
        """
        Universal gateway method making the architecture model-agnostic.
        Routes data dynamically to modality processors based on the artifact_type string.
        
        Supported types: 'heatmap' (Vision Matrix), 'tokens' (NLP Sequences), 'audio' (Waveform Signals)
        """
        self.artifact_counter += 1
        
        if not hasattr(self, 'logged_artifacts'):
            self.logged_artifacts = []
        if not hasattr(self, 'logged_text_blocks'):
            self.logged_text_blocks = []

        # Route 1: Vision / Spatial Heatmaps
        if artifact_type == "heatmap":
            # Updated to match your exact file function name: save_analysis_plot
            from .modalities.vision import save_analysis_plot
            filename = f"custom_vision_{self.artifact_counter}.png"
            target_path = os.path.join(self.artifacts_dir, filename)
            save_analysis_plot(data, target_path, title)
            self.logged_artifacts.append((title, f"artifacts/{filename}"))
            print(f"[CORE] krysta-wing :: registered vision artifact ↳ {filename}")

        # Route 2: Text Token Streams
        elif artifact_type == "tokens":
            # Updated to match your exact file function name: analyze_token_confidence
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
            print(f"[CORE] krysta-wing :: registered text token anomalies")

        
        elif artifact_type == "audio":
            from .modalities.audio import save_spectrogram_plot
            filename = f"custom_audio_{self.artifact_counter}.png"
            target_path = os.path.join(self.artifacts_dir, filename)
            save_spectrogram_plot(data, target_path, title)
            self.logged_artifacts.append((title, f"artifacts/{filename}"))
            print(f"[✓] Model-Agnostic Engine: Logged Audio Spectrogram -> {filename}")

        else:
            raise ValueError(f"Unsupported artifact type variant: '{artifact_type}'. Choose 'heatmap', 'tokens', or 'audio'.")

    def compile(self):
        """Reads template, hydrates variables, and exports the final file."""
    
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", "base_report.md")

        # Run statistical anomaly checks before rendering the template
        alerts = self._compute_regression_analysis()
        alert_markdown_block = ""
        if alerts:
            alert_markdown_block = (
                "### RUNTIME TELEMETRY ANOMALIES\n"
                "> **NOTICE:** The statistical tracking engine flagged performance metrics "
                "exceeding expected variance limits against historical baselines.\n>\n"
            )
            for alert in alerts:
                # Remove emojis from individual alert strings if you have them inside _compute_regression_analysis
                alert_markdown_block += f"> * {alert.replace('⚠️ ', '').replace('🚨 ', '')}\n"
            alert_markdown_block += "\n---\n"
        
        with open(template_path, "r") as f:
            raw_template = f.read()
            
        
        template = Template(raw_template)
        
        
        # Build dynamic markdown blocks tracking ALL custom-logged entries
        modality_content = "SYSTEM INTERPRETABILITY & MULTI-MODAL ARTIFACTS\n\n"
        has_content = False

        
        if hasattr(self, 'logged_artifacts') and self.logged_artifacts:
            has_content = True
            for title, path in self.logged_artifacts:
                modality_content += f"#### {title}\n![{title}]({path})\n\n"

        
        if hasattr(self, 'logged_text_blocks') and self.logged_text_blocks:
            has_content = True
            for block in self.logged_text_blocks:
                modality_content += block

        if not has_content:
            modality_content += "*No evaluation artifacts or modality streams logged during this operational execution pass.*"
        
        
        rendered_md = template.render(
            model_name=self.model_name,
            week=self.week,
            timestamp=self.timestamp,
            modality=self.modality,
            latency=self.metrics.get("latency", 0.0),
            vram=self.metrics.get("vram", 0.0),
            loss=self.metrics.get("loss", 0.0),
            modality_specific_content=modality_content,
            regression_alerts=alert_markdown_block
            
        )
        
        
        output_file_path = os.path.join(self.report_dir, "report.md")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(rendered_md)
            
        print(f"[SUCCESS] krysta-wing :: consolidated report exported to {output_file_path}")

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
                        f"⚠️ **PERFORMANCE REGRESSION:** Inference Latency spiked to **{current_latency:.1f}ms** "
                        f"(Historical Baseline: {mean_lat:.1f}ms ± {std_lat:.1f}ms). Exceeded 2σ limit threshold."
                    )

            # Check 2: Graphics Memory Allocation Checks
            if vrams:
                mean_vram, std_vram = calculate_stats(vrams)
                threshold_vram = mean_vram + max(2 * std_vram, 256.0)
                if current_vram > threshold_vram:
                    regression_alerts.append(
                        f"⚠️ **RESOURCE ANOMALY:** Peak VRAM consumption reached **{current_vram:.1f}MB** "
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
            print(f"⚠️ Warning: Unable to save runtime profile data to history store ({e})")

        return regression_alerts