import arabic_reshaper
from bidi.algorithm import get_display

def reshape(text):
    return get_display(arabic_reshaper.reshape(text))
