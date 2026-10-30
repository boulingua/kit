"""Model-specific speech input preparation. Displayed transcripts are never changed."""

def prepare_model_text(text, config):
    if config.get('phoneme_type') == 'text' and config.get('language', {}).get('family') == 'uk':
        # The Ukrainian character-model alphabet contains lowercase letters and
        # ASCII apostrophe. Piper's text frontend does not normalize these itself.
        return text.lower().replace('ʼ', "'").replace('’', "'")
    return text
