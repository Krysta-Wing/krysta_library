def analyze_token_confidence(tokens: list, confidences: list, threshold: float = 0.5):
    """
    Analyzes text tokens and flags low-confidence or high-perplexity words 
    that fell below the safety threshold.
    """
    flagged_tokens = []
    
    for token, conf in zip(tokens, confidences):
        if conf < threshold:
            flagged_tokens.append(f"**{token}** ({round(conf * 100, 1)}%)")
            
    return flagged_tokens