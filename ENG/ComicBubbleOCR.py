#!/usr/bin/python
# -*- coding: utf-8 -*-
from gimpfu import *
import subprocess
import os
import configparser # To store the settings in the ini file
import tempfile
import Tkinter as tk
import tkMessageBox
from Tkinter import Toplevel, Button, Label, Canvas # By color choice if it finds 50% background color
from collections import Counter
import numpy as np
from PIL import Image # for Pillow
import requests
import re
import time
import sys
import gimpcolor
import locale
locale.setlocale(locale.LC_ALL, 'C')  # Force English location to avoid numerical formatting problems


# ComicBubbleOCR by MoonDragon
# V. 1.1 rev.17
# Website: https://github.com/MoonDragon-MD/ComicBubbleOCR

## Dependencies
# wget https://old-releases.ubuntu.com/ubuntu/pool/universe/p/pygtk/python-gtk2_2.24.0-6_amd64.deb
# wget https://old-releases.ubuntu.com/ubuntu/pool/universe/g/gimp/gimp-python_2.10.8-2_amd64.deb
# sudo dpkg -i python-gtk2_2.24.0-6_amd64.deb
# sudo dpkg -i gimp-python_2.10.8-2_amd64.deb
# sudo apt-get install python-tk tesseract-ocr-* (*= language es jpn)
# sudo apt install -f  # Fix any dependency issues
# curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
# python2.7 get-pip.py
# python2.7 -m pip install requests Pillow [googletrans==2.4.0]
## Put ComicBubbleOCR.py in
# ~/.config/GIMP/2.10/plug-ins/
# execute permits
# chmod +x ~/.config/GIMP/2.10/plug-ins/ComicBubbleOCR.py

# Enable/disable debug log txt file
ENABLE_DEBUG = False

# Global bubble counter
bubble_counter = 0

# Mapping for languages
LANGUAGE_MAP = {
    "auto": "eng", "en": "eng", "it": "ita", "fr": "fra", "es": "spa", "de": "deu",
    "ja": "jpn", "zh": "chi_sim", "ru": "rus", "pt": "por", "ar": "ara",
    "ko": "kor", "nl": "nld", "tr": "tur", "pl": "pol", "sv": "swe",
    "id": "ind", "hi": "hin", "bn": "ben", "ms": "msa", "th": "tha"
}

TRANSLATION_LANG_MAP = {
    "eng": "en", "ita": "it", "fra": "fr", "spa": "es", "deu": "de",
    "jpn": "ja", "chi_sim": "zh", "rus": "ru", "por": "pt", "ara": "ar",
    "kor": "ko", "nld": "nl", "tur": "tr", "pol": "pl", "swe": "sv",
    "ind": "id", "hin": "hi", "ben": "bn", "msa": "ms", "tha": "th"
}

# Constant
BText = "GlobeText"
g_nameFileImageOCR = "ocr_image.png"

# PSM Tesseract OCR options
psm_options = [
    ("0", "Orientation and detection (OSD)"),
    ("1", "Automatic detection with OSD"),
    ("2", "Automatic detection, no OSD or OCR"),
    ("3", "Fully automatic, no osd (default)"),
    ("4", "Single text column of variable size"),
    ("5", "Single uniform block of vertical text"),
    ("6", "Single block of uniform text"),
    ("7", "Single text line"),
    ("8", "Single word"),
    ("9", "Single word in circle"),
    ("10", "Single character"),
    ("11", "Scattered text, find as much text as possible"),
    ("12", "Sparse text with OSD"),
    ("13", "Raw line, bypassing hacks")
]

# Configuration file path
CONFIG_FILE = "/tmp/ComicBubbleOCR.ini"

# IDefault Mostations
DEFAULT_SETTINGS = {
    "lang_input": "auto",
    "lang_output": "it",
    "psm_var": "3",
    "psm_display": psm_options[3][1],
    "preprocess_var": "none",
    "auto_color_var": "True",
    "invert_colors_var": "False",
    "lowercase_translate_var": "False",
    "translator_var": "libre",
    "auto_anchor_var": "False"
}

# Text preprocessing options
preprocess_options = [
    ("none", "No pre-elaboration"),
    ("join_hyphen", "Combines row interruptions with -"),
    ("join_space", "It combines all line interruptions with a space"),
    ("remove_duplicate_returns", "Remove double interruptions"),
    ("remove_duplicate_spaces", "Remove double spaces")
]

# Manage the saving of the settings in the ini file
def load_settings():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        print("Configuration files %s not found, creation with predefined values" % CONFIG_FILE)
        config['Settings'] = DEFAULT_SETTINGS
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            print("Error in creating the configuration file: %s" % str(e))
            return DEFAULT_SETTINGS
    try:
        config.read(CONFIG_FILE)
        settings = dict(config['Settings'])
        # Converts Boolean strings into Boolean values
        settings['auto_color_var'] = config.getboolean('Settings', 'auto_color_var')
        settings['invert_colors_var'] = config.getboolean('Settings', 'invert_colors_var')
        settings['lowercase_translate_var'] = config.getboolean('Settings', 'lowercase_translate_var')
        settings['auto_anchor_var'] = config.getboolean('Settings', 'auto_anchor_var')
        print("Settings uploaded from %s: %s" % (CONFIG_FILE, settings))
        return settings
    except Exception as e:
        print("Reading the configuration file error: %s, use default values" % str(e))
        return DEFAULT_SETTINGS
    
def save_settings(settings):
    config = configparser.ConfigParser()
    config['Settings'] = {
        'lang_input': settings['lang_input'],
        'lang_output': settings['lang_output'],
        'psm_var': settings['psm_var'],
        'psm_display': settings['psm_display'],
        'preprocess_var': settings['preprocess_var'],
        'auto_color_var': str(settings['auto_color_var']),
        'invert_colors_var': str(settings['invert_colors_var']),
        'lowercase_translate_var': str(settings['lowercase_translate_var']),
        'translator_var': settings['translator_var'],
        'auto_anchor_var': str(settings['auto_anchor_var'])
    }
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        print("Settings saved in %s: %s" % (CONFIG_FILE, settings))
    except Exception as e:
        print("Error in saving the configuration file: %s" % str(e))

# Preprocessing function
def preprocess_text(text, preprocess_mode):
    if preprocess_mode == "none":
        return text
    elif preprocess_mode == "join_hyphen":
        text = re.sub(r'-\s*\n', '', text)
    elif preprocess_mode == "join_space":
        text = re.sub(r'\s*\n', ' ', text)
    elif preprocess_mode == "remove_duplicate_returns":
        text = re.sub(r'\n+', '\n', text)
    elif preprocess_mode == "remove_duplicate_spaces":
        text = re.sub(r' +', ' ', text)
    return text

# Translation functions
def translate_with_google(text, target_lang="it"):
    try:
        from googletrans import Translator
        translator = Translator()
        print("Translation attempt with Google Translate, testo: '%s', lang: '%s'" % (text, target_lang))
        translated = translator.translate(text, dest=target_lang)
        if translated is None or translated.text is None:
            raise ValueError("Reply from Google Translate empty or not valid")
        print("Translate Google translation successful: '%s'" % translated.text)
        return translated.text
    except Exception as e:
        error_msg = "Google Translate error: %s" % str(e)
        print(error_msg)
        tkMessageBox.showwarning("Notice", "%s. Attempt with LibreTranslate..." % error_msg)
        try:
            translated_text = translate_with_libre(text, source_lang="auto", target_lang=target_lang)
            print("Translation LibreTranslate successful: '%s'" % translated_text)
            return translated_text
        except Exception as libre_e:
            error_msg = "LibreTranslate error: %s" % str(libre_e)
            print(error_msg)
            tkMessageBox.showerror("Error", "%s. I return the original text." % error_msg)
            return text

def translate_with_libre(text, source_lang="auto", target_lang="it"):
    url = "http://localhost:5000/translate"
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    data = {"q": text, "source": source_lang, "target": target_lang}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('translatedText', '').strip()
    except Exception as e:
        tkMessageBox.showerror("Error", "LibreTranslate error: %s" % str(e))
        return text

def get_selection_bounds(image):
    """Gets the boundaries of the selection, restoring none if empty."""
    if pdb.gimp_selection_is_empty(image):
        tkMessageBox.showerror("Error", "No active selection found.")
        return None
    return pdb.gimp_selection_bounds(image)[1:5]

def get_position_selection(image, x1, y1, x2, y2):
    points = [
        (x1 + 5, y1 + 5), (x2 - 5, y1 + 5), (x1 + 5, y2 - 5), (x2 - 5, y2 - 5),
        (x1 + (x2 - x1) // 2, y1 + 5), (x1 + (x2 - x1) // 2, y2 - 5),
        (x1 + 5, y1 + (y2 - y1) // 2), (x2 - 5, y1 + (y2 - y1) // 2),
        (x1 + 10, y1 + 10), (x2 - 10, y1 + 10), (x1 + 10, y2 - 10), (x2 - 10, y2 - 10)
    ]
    valid_points = []
    for x, y in points:
        if x1 <= x <= x2 and y1 <= y <= y2:
            valid_points.append((x, y))
    return valid_points

def calculate_brightness(color):
    """Calculate the brightness of an RGB color."""
    return (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])

def choose_color_popup(colors, counts, total_samples):
    """Show a popup to choose between two colors with similar frequencies."""
    root = Toplevel()
    root.title("Select background color")
    root.geometry("300x150")
    
    selected_color = [None]  # Variable to memorize the chosen color
    
    def select_color(color):
        selected_color[0] = color
        root.destroy()
    
    Label(root, text="Two colors have similar frequencies. Choose the background color:").pack(pady=10)
    
    for color, count in zip(colors, counts):
        percentage = (count / float(total_samples)) * 100
        color_str = "#{:02x}{:02x}{:02x}".format(*color)
        frame = tk.Frame(root)
        frame.pack(pady=5)
        canvas = Canvas(frame, width=50, height=20, bg=color_str, relief="raised", borderwidth=1)
        canvas.pack(side=tk.LEFT, padx=5)
        Button(frame, text="Scegli (%.1f%%)" % percentage, command=lambda c=color: select_color(c)).pack(side=tk.LEFT)
    
    root.wait_window()  # Wait for the user to close the popup
    return selected_color[0]

def export_image_selectioned(image, drawable, name_layer, auto_color=False, gui_psm='3', source_lang='auto', target_lang='it', translator='libre', invert_colors=False, preprocess_mode='none'):
    temp_files = []  # List to trace all temporary files
    """
    Export the selection of the bubble, create a new layer, prepare the image for the OCR and returns the OCR text.

    Parameters:
    - image: Image GIMP
    - drawable: Active layer from which to copy the selection
    - name_layer: Base name for layers
    - auto_color: If True, the color of the bubble samples
    - gui_psm: PSM mode for Tesseract (default: 7)
    - source_lang: Source language for OCR (default: auto)
    - target_lang: Target language for translation
    - translator: 'google' or 'libre' To choose the translator
    - invert_colors: If True, invert the colors of the OCR image
    - preprocess_mode: Methods of pre-processing the text
    """
    try:
        # 1. Get the boundaries of the selection
        bounds = get_selection_bounds(image)
        if not bounds:
            print("Error: no valid selection")
            tkMessageBox.showerror("Error", "No valid selection. Use free selection or magic wand to include the balloon.")
            return None, None, None, None, None, None
        x1, y1, x2, y2 = bounds
        print("Confini selezione: x1=%d, y1=%d, x2=%d, y2=%d" % (x1, y1, x2, y2))

        # 2. Save the original selection
        original_selection = pdb.gimp_selection_save(image)
        original_selection.name = "Original_Selection"
        print("Original saved, empty selection: %s" % pdb.gimp_selection_is_empty(image))

        # 3. Create a new layer with the copied selection
        pdb.gimp_image_select_item(image, 2, original_selection)
        if not pdb.gimp_edit_copy(drawable):
            print("Error: impossible to copy the selection")
            tkMessageBox.showerror("Error", "Unable to copy the selection")
            return None, None, None, None, None, None
        new_layer = pdb.gimp_layer_new(image, image.width, image.height, RGBA_IMAGE, "BubbleLayer", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image, new_layer, None, 0)
        pdb.gimp_drawable_fill(new_layer, FILL_TRANSPARENT)
        floating_sel = pdb.gimp_edit_paste(new_layer, False)
        pdb.gimp_floating_sel_anchor(floating_sel)
        print("New layer 'BubbleLayer' created with the copied selection")

        # 4. Prepare the image for the OCR using the external rectangle
        print("Image preparation for OCR")
        margin = 2
        ocr_x1 = max(0, x1 - margin)
        ocr_y1 = max(0, y1 - margin)
        ocr_x2 = min(image.width, x2 + margin)
        ocr_y2 = min(image.height, y2 + margin)
        print("Rettangolo OCR: x1=%d, y1=%d, x2=%d, y2=%d" % (ocr_x1, ocr_y1, ocr_x2, ocr_y2))
        pdb.gimp_image_select_rectangle(image, 2, ocr_x1, ocr_y1, ocr_x2 - ocr_x1, ocr_y2 - ocr_y1)
        width, height = ocr_x2 - ocr_x1, ocr_y2 - ocr_y1
        if width < 10 or height < 10:
            print("Error: OCR selection too small (larghezza=%d, altezza=%d)" % (width, height))
            tkMessageBox.showerror("Error", "OCR selection too small (minimum 10x10 pixels)")
            return None, None, None, None, None, None
        if not pdb.gimp_edit_copy(drawable):
            raise Exception("Error: Impossible to copy the selection for OCR")
        image_selection = pdb.gimp_edit_paste_as_new_image()
        if not image_selection or not image_selection.layers:
            raise Exception("Error: Impossible to create the temporary image for OCR")
        layer_background = pdb.gimp_layer_new(image_selection, image_selection.width, image_selection.height,
                                             RGBA_IMAGE, "Background", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image_selection, layer_background, None, 1)
        pdb.gimp_layer_set_lock_alpha(layer_background, False)
        pdb.gimp_context_set_background(gimpcolor.RGB(1.0, 1.0, 1.0))
        pdb.gimp_drawable_fill(layer_background, FILL_BACKGROUND)
        temp_dir = tempfile.gettempdir()
        path_image_ocr = os.path.join(temp_dir, "ocr_image.png")

        # 5. OCR attempts with several PSMs
        ocr_text = ""
        psm_values = [gui_psm, '7', '6', '11']  # Use gui_psm as the first attempt, followed by 7, 6, 11
        successful_attempt = None

        # Create a copy of the selected image once and for all attempts
        if not pdb.gimp_edit_copy(drawable):
            raise Exception("Error: Impossible to copy the selection for OCR")
        image_selection = pdb.gimp_edit_paste_as_new_image()
        if not image_selection or not image_selection.layers:
            raise Exception("Error: Impossible to create the temporary image for OCR")

        # Add a white background layer for uniformity
        layer_background = pdb.gimp_layer_new(image_selection, image_selection.width, image_selection.height,
                                              RGBA_IMAGE, "Background", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image_selection, layer_background, None, 1)
        pdb.gimp_layer_set_lock_alpha(layer_background, False)
        pdb.gimp_context_set_background(gimpcolor.RGB(1.0, 1.0, 1.0))
        pdb.gimp_drawable_fill(layer_background, FILL_BACKGROUND)

        # Cycle on the different PSM for OCR attempts
        for attempt, psm in enumerate(psm_values, 1):
            print("OCR attempt %d con PSM %s" % (attempt, psm))

            # Duplicate the original image for each attempt
            temp_image = pdb.gimp_image_duplicate(image_selection)
            output_path = os.path.join(temp_dir, "ocr_image_attempt_%d.png" % attempt)
            temp_files.append(output_path)  # Add the file to the list

            # Preprocessing of the image based on brightness or color reversal
            if invert_colors:
                print("Color inversion application")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Save the pre -procured image as PNG
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Image saved in: %s" % output_path)
                # Check that the file exists and is not too small
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Error: File %s not created or too small" % output_path)
            except Exception as e:
                print("Error in rescue OCR image (attempt %d): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                continue

            # Check the variance of the image to avoid false negatives
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Pixel image variance (attempt %d): %f" % (attempt, variance))
                if variance < 20:
                    print("Image with low variance, probable absence of text (attempt %d)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    continue
            except Exception as e:
                print("Image control error image (attempt %d): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                continue

            # Run Tesseract with the current PSM
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Add the text file to the list
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", psm, "-l", source_lang]
            print("Run Tesseract (attempt %d): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (attempt %d): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Testo estratto (attempt %d): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                        break
                else:
                    print("Error: output files %s not found" % output_file)
            except subprocess.CalledProcessError as e:
                print("Error in Tesseract (attempt %d): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Errore in Tesseract (attempt %d): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # 5.1 Additional attempt with inscribed rectangle (10%%)
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Additional OCR attempt with inscribed rectangle (reduction 10%%, PSM 7)")
            attempt = 4

            # Duplicate the original image
            temp_image = pdb.gimp_image_duplicate(image_selection)

            # Calculate the rectangle inscribed (reduce 10%%)
            shrink_margin = int(min(temp_image.width, temp_image.height) * 0.1)
            inner_x1 = shrink_margin
            inner_y1 = shrink_margin
            inner_x2 = temp_image.width - shrink_margin
            inner_y2 = temp_image.height - shrink_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Rectangle inscribed (10%%) too small, original selection use")
                inner_x1, inner_y1, inner_x2, inner_y2 = 0, 0, temp_image.width, temp_image.height
            else:
                print("Rectangle inscribed (10%%): x1=%d, y1=%d, x2=%d, y2=%d" % (inner_x1, inner_y1, inner_x2, inner_y2))
                pdb.gimp_image_select_rectangle(temp_image, 2, inner_x1, inner_y1, inner_x2 - inner_x1, inner_y2 - inner_y1)
                if not pdb.gimp_edit_copy(temp_image.layers[0]):
                    print("Error: impossible to copy the rectangle inscribed (10%%)")
                    pdb.gimp_image_delete(temp_image)
                else:
                    inscribed_image = pdb.gimp_edit_paste_as_new_image()
                    pdb.gimp_image_delete(temp_image)
                    temp_image = inscribed_image

            output_path = os.path.join(temp_dir, "ocr_image_attempt_inscribed_%d.png" % attempt)
            temp_files.append(output_path)  # Add the file to the list

            # Preprocessing (color inversion if necessary)
            if invert_colors:
                print("Color inversion application (inscribed 10%%)")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Save the image
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Image saved in: %s" % output_path)
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Error: File %s not created or too small" % output_path)
            except Exception as e:
                print("Error in rescue OCR image (attempt %d, inscribed 10%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Check the variance
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Pixel image variance (attempt %d, inscribed 10%%): %f" % (attempt, variance))
                if variance < 20:
                    print("Image with low variance, probable absence of text (attempt %d, inscribed 10%%)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    return None, None, None, None, None, None
            except Exception as e:
                print("Image control error image (attempt %d, inscribed 10%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Esegui Tesseract con PSM 7
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Add the text file to the list
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", "7", "-l", source_lang]
            print("Run Tesseract (attempt %d, inscribed 10%%): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (attempt %d, inscribed 10%%): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Extract text (attempt %d, inscribed 10%%): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                else:
                    print("Error: output files %s not found" % output_file)
            except subprocess.CalledProcessError as e:
                print("Error in Tesseract (attempt %d, inscribed 10%%): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Error in Tesseract (attempt %d, inscribed 10%%): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # 5.2 Additional attempt with smaller insulted rectangle (20%%)
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Additional OCR attempt with smaller insulted rectangle (reduction 20%%, PSM 6)")
            attempt = 5

            # Duplicate the original image
            temp_image = pdb.gimp_image_duplicate(image_selection)

            # Calculate the rectangle inscribed (reduce 20%%)
            shrink_margin = int(min(temp_image.width, temp_image.height) * 0.2)
            inner_x1 = shrink_margin
            inner_y1 = shrink_margin
            inner_x2 = temp_image.width - shrink_margin
            inner_y2 = temp_image.height - shrink_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Rectangle inscribed (20%%) too small, original selection use")
                inner_x1, inner_y1, inner_x2, inner_y2 = 0, 0, temp_image.width, temp_image.height
            else:
                print("Rectangle inscribed (20%%): x1=%d, y1=%d, x2=%d, y2=%d" % (inner_x1, inner_y1, inner_x2, inner_y2))
                pdb.gimp_image_select_rectangle(temp_image, 2, inner_x1, inner_y1, inner_x2 - inner_x1, inner_y2 - inner_y1)
                if not pdb.gimp_edit_copy(temp_image.layers[0]):
                    print("Error: impossible to copy the rectangle inscribed (20%%)")
                    pdb.gimp_image_delete(temp_image)
                else:
                    inscribed_image = pdb.gimp_edit_paste_as_new_image()
                    pdb.gimp_image_delete(temp_image)
                    temp_image = inscribed_image

            output_path = os.path.join(temp_dir, "ocr_image_attempt_inscribed_%d.png" % attempt)
            temp_files.append(output_path)  # Add the file to the list

            # Preprocessing (Forced color reversal for the fifth attempt)
            if invert_colors or attempt == 5:
                print("Color inversion application (inscribed 20%%)")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Save the image
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Image saved in: %s" % output_path)
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Error: File %s not created or too small" % output_path)
            except Exception as e:
                print("Error in rescue OCR image (attempt %d, inscritto 20%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Check the variance
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Pixel image variance (attempt %d, inscribed 20%%): %f" % (attempt, variance))
                if variance < 20:
                    print("Image with low variance, probable absence of text (attempt %d, inscribed 20%%)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    return None, None, None, None, None, None
            except Exception as e:
                print("Image control error image (attempt %d, inscribed 20%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Tesseract with PSM 8 (single word) for the fifth attempt
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Add the text file to the list
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", "6", "-l", source_lang]
            print("Run Tesseract (attempt %d, inscribed 20%%): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (attempt %d, inscribed 20%%): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Extract text (attempt %d, inscribed 20%%): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                else:
                    print("Error: output files %s not found" % output_file)
            except subprocess.CalledProcessError as e:
                print("Error in Tesseract (attempt %d, inscribed 20%%): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Error in Tesseract (attempt %d, inscribed 20%%): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # Final control for the OCR result
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Error: no valid text extracted from Tesseract after %d attempts" % (len(psm_values) + 2))
            tkMessageBox.showwarning("Notice", "No valid extract text. Check the language (e.g. 'ara' for Arabic) and check %s/ocr_image_attempt_*.png per debug." % temp_dir)
            return None, None, None, None, None, None

        # 6. Pre-elaborate the OCR text
        ocr_text = preprocess_text(ocr_text, preprocess_mode)

        # 7. Color sampling (only within the registered rectangle)
        color_balloon = (255, 255, 255)  # Default background: white
        text_color = (0, 0, 0)  # Default text: black
        if auto_color:
            print("Starting colors sampling...")
            colors = []
            pdb.gimp_image_select_item(image, 2, original_selection)
            width, height = x2 - x1, y2 - y1
            # Sample only within the inscribed rectangle (avoid edges to exclude borders)
            edge_margin = 5
            inner_x1, inner_y1 = x1 + edge_margin, y1 + edge_margin
            inner_x2, inner_y2 = x2 - edge_margin, y2 - edge_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Error: too small rectangle registered, complete selection use")
                inner_x1, inner_y1, inner_x2, inner_y2 = x1, y1, x2, y2
            step = max(1, min(inner_x2 - inner_x1, inner_y2 - inner_y1) // 10)  # Finer sampling
            for y in range(inner_y1, inner_y2, step):
                for x in range(inner_x1, inner_x2, step):
                    if pdb.gimp_selection_value(image, x, y) > 0:
                        pixel = pdb.gimp_drawable_get_pixel(new_layer, x, y)
                        if pixel and len(pixel[1]) >= 4 and pixel[1][3] > 0:
                            colors.append(tuple(pixel[1][:3]))
                            print("Championship color a (%d, %d): %s" % (x, y, tuple(pixel[1][:3])))
            if colors:
                color_counts = Counter(colors)
                # Filter colors with at least 5% frequency
                total_samples = len(colors)
                min_count = total_samples * 0.05  # 5% per includere #f3e6d3
                top_colors = [(color, count) for color, count in color_counts.most_common() if count >= min_count]
                if len(top_colors) >= 1:
                    color_balloon = top_colors[0][0]  # Most common color for background
                    brightness = calculate_brightness(color_balloon)
                    if len(top_colors) >= 2:
                        count1, count2 = top_colors[0][1], top_colors[1][1]
                        percent1, percent2 = (count1 / float(total_samples)) * 100, (count2 / float(total_samples)) * 100
                        if abs(percent1 - percent2) <= 5:  # Similar frequencies (50% ± 5%), show popup
                            print("Two colors with similar frequencies: %s (%.1f%%), %s (%.1f%%)" % (top_colors[0][0], percent1, top_colors[1][0], percent2))
                            chosen_color = choose_color_popup([top_colors[0][0], top_colors[1][0]], [count1, count2], total_samples)
                            if chosen_color:
                                color_balloon = chosen_color
                                text_color = top_colors[1][0] if chosen_color == top_colors[0][0] else top_colors[0][0]
                                print("Color background chosen: %s, Text color: %s" % (color_balloon, text_color))
                            else:
                                print("No color chosen, I use the most common: %s" % str(color_balloon))
                                text_color = top_colors[1][0]  # Default to second color
                        else:
                            # Two colors with different frequencies
                            text_color = top_colors[1][0]  # Use second color for text
                            print("Two colors detected, background: %s (%.1f%%), testo: %s (%.1f%%)" % (color_balloon, percent1, text_color, percent2))
                    else:
                        # One or more than two colors: brightness-based text color
                        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                        print("Only one color or more colors detected, background: %s, brightness: %f, testo: %s" % (color_balloon, brightness, text_color))

                    # Check if background and text color are the same or too similar
                    def color_distance(c1, c2):
                        return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)**0.5

                    if color_balloon == text_color or color_distance(color_balloon, text_color) < 20:  # Similarity threshold
                        print("Notice: background color (%s) and text color (%s) they are the same or too similar" % (color_balloon, text_color))
                        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                        print("Modified text color based on brightness: %s" % str(text_color))
                else:
                    # Fallback if there are no valid colors
                    color_balloon = top_colors[0][0] if top_colors else (255, 255, 255)
                    brightness = calculate_brightness(color_balloon)
                    text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                    print("No color valid with frequency >= 5%, background use: %s, text: %s" % (color_balloon, text_color))
            else:
                print("No color valid championship, white use of default")
                color_balloon = (255, 255, 255)
                brightness = calculate_brightness(color_balloon)
                text_color = (0, 0, 0)
                print("Final background color: %s, final text color: %s" % (color_balloon, text_color))
            print("Final background color: %s, final text color: %s" % (color_balloon, text_color))

        # 8. Optimizes the selection to fill the bubble
        pdb.gimp_image_select_item(image, 2, original_selection)
        temp_mask = pdb.gimp_selection_save(image)
        temp_mask.name = "Temp_Mask"
        print("Temp_Mask channel created")
        for _ in range(2):  # Reduced to 2 iterations
            # Apply blur and optimization
            pdb.plug_in_gauss(image, temp_mask, 10.0, 10.0, 0)  # Ray reduced to 10.0
        print("Exec pdb.plug_in_gauss (iterative)")
        pdb.gimp_drawable_threshold(temp_mask, HISTOGRAM_VALUE, 0.1, 1.0)
        pdb.gimp_image_select_item(image, 2, temp_mask)
        pdb.gimp_selection_grow(image, 3)  # Expansion reduced to 3 pixels
        pdb.gimp_selection_shrink(image, 2)
        pdb.gimp_selection_feather(image, 2.0)
        optimized_selection = pdb.gimp_selection_save(image)
        optimized_selection.name = "Optimized_Selection"
        print("Optimized selection saved, empty: %s" % pdb.gimp_selection_is_empty(image))

        # 8.1 Reduce the 4% selection to compensate for the thick
        pdb.gimp_image_select_item(image, 2, optimized_selection)
        bounds = pdb.gimp_selection_bounds(image)[1:5]
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        shrink_amount = max(3, int(min(width, height) * 0.04))  # 4% with minimum 3 pixels
        if shrink_amount > 0:
            pdb.gimp_selection_shrink(image, shrink_amount)
            print("Reduced selection of 4 %% (shrink_amount=%d)" % shrink_amount)
        else:
            print("Shrink amount è 0, No reduction applied")
        optimized_selection_reduced = pdb.gimp_selection_save(image)
        optimized_selection_reduced.name = "Optimized_Selection_Reduced"
        print("Reduced selection saved, empty: %s" % pdb.gimp_selection_is_empty(image))

        # Visual debug of the reduced selection
        if ENABLE_DEBUG:
            temp_selection_image = pdb.gimp_image_new(width, height, RGB)
            temp_layer = pdb.gimp_layer_new(temp_selection_image, width, height, RGBA_IMAGE, "Selection_Debug", 100, LAYER_MODE_NORMAL)
            pdb.gimp_image_insert_layer(temp_selection_image, temp_layer, None, 0)
            pdb.gimp_drawable_fill(temp_layer, FILL_TRANSPARENT)
            pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
            pdb.gimp_context_set_background(gimpcolor.RGB(1.0, 1.0, 1.0))
            pdb.gimp_drawable_edit_fill(temp_layer, FILL_BACKGROUND)
            debug_path = os.path.join(tempfile.gettempdir(), "debug_selection_reduced.png")
            pdb.file_png_save(temp_selection_image, temp_layer, debug_path, debug_path, 0, 9, 1, 1, 1, 1, 1)
            temp_files.append(debug_path)
            print("Reduced selection saved for debugs: %s" % debug_path)
            pdb.gimp_image_delete(temp_selection_image)

        # 9. Create and fill a new bubble layer
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        layer_group = pdb.gimp_layer_group_new(image)
        layer_group.name = "Group_%s_%s" % (name_layer, timestamp)
        pdb.gimp_image_insert_layer(image, layer_group, None, 0)
        print("New group of layer created: %s" % layer_group.name)
        layer_globe_text = pdb.gimp_layer_new(image, image.width, image.height, RGBA_IMAGE,
                                              "GlobeText_%s" % timestamp, 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image, layer_globe_text, layer_group, 0)
        pdb.gimp_drawable_fill(layer_globe_text, FILL_TRANSPARENT)
        print("Empty Globetext Layer creation")

        # 10. Fill the selection with the background color
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)  # Usa la selezione ridotta
        pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
        print("Basic filling with color: %s" % str(color_balloon))

        # Calculate the size of the selection and divide into a 3x3 grid
        width = x2 - x1
        height = y2 - y1
        print("Selection size: length=%d, height=%d" % (width, height))

        # Divide into three parts by width and height
        x_step = width // 3
        y_step = height // 3
        # Define the central points of the 3x3 grid
        brush_points = []
        margin = 10  # Margin to avoid the edges
        for i in range(3):
            for j in range(3):
                bx = x1 + (i * x_step + x_step // 2)
                by = y1 + (j * y_step + y_step // 2)
                bx = min(max(x1 + margin, bx), x2 - margin)
                by = min(max(y1 + margin, by), y2 - margin)
                brush_points.append((bx, by))
        print("3x3 grid points for the brush: %s" % str(brush_points))

        # Set the brush and its properties
        try:
            pdb.gimp_context_set_brush("2. Hardness 100")
            pdb.gimp_context_set_dynamics("Basic Simple")
        except:
            print("Brush '2. Hardness 100' a dynamic 'Basic Simple' not found, use 'GIMP Brush'")
            pdb.gimp_context_set_brush("GIMP Brush")
            pdb.gimp_context_set_dynamics("Dynamics Off")

        # Set the brush size according to the selection size
        brush_size = max(100.0, min(width, height) * 0.4)  # 40% of the minor size, minimum 100
        pdb.gimp_context_set_brush_size(brush_size)
        pdb.gimp_context_set_opacity(100.0)
        pdb.gimp_context_set_paint_mode(LAYER_MODE_NORMAL)
        print("Set brush size: %f" % brush_size)

        # Apply the brush three times for each central point
        for i, (bx, by) in enumerate(brush_points, 1):
            print("STUDRO application to the point %d (%d, %d) with size %f" % (i, bx, by, brush_size))
            for pass_num in range(1, 4):
                pdb.gimp_paintbrush(layer_globe_text, 0, 4, [bx, by, bx, by, bx, by, bx, by], PAINT_INCREMENTAL, 0)
                print("Use %d Completed by point (%d, %d)" % (pass_num, bx, by))

        # Add brush strokes along the axes of the 3x3 grid
        print("Application brush strokes along the axes of the grid")
        # Define the start and end points for each line (horizontal) and column (vertical)
        rows = [y1 + (j * y_step + y_step // 2) for j in range(3)]  # Centers of the Stripeds
        cols = [x1 + (i * x_step + x_step // 2) for i in range(3)]  # Centers of the columns
        for row_y in rows:
            row_y = min(max(y1 + margin, row_y), y2 - margin)
            # Left-to-right
            coords_lr = []
            for x in range(x1 + margin, x2 - margin + 1, max(1, int(brush_size / 4))):
                coords_lr.extend([x, row_y])
            if len(coords_lr) >= 4:
                print("Left brush stroke a y=%d: %s" % (row_y, coords_lr))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_lr), coords_lr, PAINT_INCREMENTAL, 0)
                    print("Give %d left-right completed to y=%d" % (pass_num, row_y))
            # Right-to-left
            coords_rl = []
            for x in range(x2 - margin, x1 + margin - 1, -max(1, int(brush_size / 4))):
                coords_rl.extend([x, row_y])
            if len(coords_rl) >= 4:
                print("Right-left brushstroke a y=%d: %s" % (row_y, coords_rl))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_rl), coords_rl, PAINT_INCREMENTAL, 0)
                    print("Give %d right-right completed to y=%d" % (pass_num, row_y))
        for col_x in cols:
            col_x = min(max(x1 + margin, col_x), x2 - margin)
            # Top-to-bottom
            coords_tb = []
            for y in range(y1 + margin, y2 - margin + 1, max(1, int(brush_size / 4))):
                coords_tb.extend([col_x, y])
            if len(coords_tb) >= 4:
                print("High-low brush stroke a x=%d: %s" % (col_x, coords_tb))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_tb), coords_tb, PAINT_INCREMENTAL, 0)
                    print("Give %d high-low completed a x=%d" % (pass_num, col_x))
            # Bottom-to-top
            coords_bt = []
            for y in range(y2 - margin, y1 + margin - 1, -max(1, int(brush_size / 4))):
                coords_bt.extend([col_x, y])
            if len(coords_bt) >= 4:
                print("Low-high brush stroke a x=%d: %s" % (col_x, coords_bt))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_bt), coords_bt, PAINT_INCREMENTAL, 0)
                    print("Give %d Low-high completed a x=%d" % (pass_num, col_x))

        print("Final filling with optimized selection")
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)

        # 11. I blur the layer and apply the mask
        print("Layer blurring application GlobeText")
        pdb.plug_in_gauss(image, layer_globe_text, 10.0, 10.0, 0)
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_selection_shrink(image, 2)
        layer_mask = pdb.gimp_layer_create_mask(layer_globe_text, ADD_MASK_SELECTION)
        pdb.gimp_layer_add_mask(layer_globe_text, layer_mask)
        pdb.plug_in_gauss(image, layer_mask, 5.0, 5.0, 0)
        pdb.gimp_layer_remove_mask(layer_globe_text, MASK_APPLY)
        print("Layer mask creation with optimized selection")

        # 10.bis Additional filling application with reduced selection of 10%
        print("Additional filling application with reduced selection of 10%%")
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        bounds = pdb.gimp_selection_bounds(image)[1:5]
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        shrink_amount = int(min(width, height) * 0.05)  # 5% of the smaller size
        if shrink_amount > 0:
            pdb.gimp_selection_shrink(image, shrink_amount)
            if not pdb.gimp_selection_is_empty(image):
                pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                print("Additional filling applied with shrink_amount=%d" % shrink_amount)
            else:
                print("Reduced selection is empty, no additional filling")
        else:
            print("Shrink amount is 0, No additional filling")

        # Final filling for uniformity
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
        print("Completed final filling")

        # 12. Check the content of the layer
        center_x = x1 + (x2 - x1) // 2
        center_y = y1 + (y2 - y1) // 2
        print("Check Layer transparency GlobeText to the central point (%d, %d)" % (center_x, center_y))
        pixel_value = pdb.gimp_drawable_get_pixel(layer_globe_text, center_x, center_y)
        print("Value pixel layer GlobeText to the point (%d, %d): %s" % (center_x, center_y, pixel_value))

    except Exception as e:
        print("Errore: %s" % str(e))
        tkMessageBox.showerror("Error", "Error in creating the layer GlobeText: %s" % str(e))
        return None, None, None, None, None, None

    finally:
        # Cleaning
        if 'original_selection' in locals() and pdb.gimp_item_is_valid(original_selection):
            pdb.gimp_image_remove_channel(image, original_selection) # I could also comment on it if I have problems with filling
        if 'temp_mask' in locals() and pdb.gimp_item_is_valid(temp_mask):
            pdb.gimp_image_remove_channel(image, temp_mask)
        if 'optimized_selection' in locals() and pdb.gimp_item_is_valid(optimized_selection):
            pdb.gimp_image_remove_channel(image, optimized_selection)
        if 'optimized_selection_reduced' in locals() and pdb.gimp_item_is_valid(optimized_selection_reduced):
            pdb.gimp_image_remove_channel(image, optimized_selection_reduced)
        if 'new_layer' in locals() and pdb.gimp_item_is_valid(new_layer):
            pdb.gimp_image_remove_layer(image, new_layer)
        pdb.gimp_selection_none(image)
        # Remove all the temporary files, unless ENABLE_DEBUG is true
        if not ENABLE_DEBUG:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        print("Temporary file removed: %s" % temp_file)
                    except Exception as e:
                        print("File removal error %s: %s" % (temp_file, str(e)))

    return path_image_ocr, (x1, y1, x2, y2), color_balloon, "GlobeText_%s" % timestamp, text_color, ocr_text

def run_tesseract(image_path, lang="eng", psm="3", invert_colors=False):
    temp_dir = tempfile.gettempdir()
    output_base = os.path.join(temp_dir, "ocr_output")
    temp_image_path = image_path
    if invert_colors:
        try:
            from PIL import Image
            img = Image.open(image_path)
            img = img.convert("RGB")
            img = Image.eval(img, lambda x: 255 - x)
            temp_image_path = os.path.join(temp_dir, "ocr_image_inverted.png")
            img.save(temp_image_path)
            print("Inverted image saved in:", temp_image_path)
        except Exception as e:
            print("Error in the reverse of colors: %s" % str(e))
            tkMessageBox.showerror("Error", "Error in the reverse of colors: %s" % str(e))
            temp_image_path = image_path

    cmd = ["tesseract", temp_image_path, output_base, "--oem", "3", "--psm", psm, "-l", lang]
    try:
        print("Run Tesseract:", cmd)
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        print("Output Tesseract:", result)
        with open(output_base + ".txt", "r") as f:
            text = f.read().strip()
        print("Extract text:", text)
        os.remove(output_base + ".txt")
        if invert_colors and temp_image_path != image_path:
            os.remove(temp_image_path)
        return text
    except Exception as e:
        error_msg = "Tesseract fail: %s" % str(e)
        print(error_msg)
        tkMessageBox.showerror("Error", "%s. Try to change the PSM mode or enable color reversal." % error_msg)
        if invert_colors and temp_image_path != image_path:
            os.remove(temp_image_path)
        return ""

class TranslationGUI(tk.Tk):
    def __init__(self, image, drawable):
        tk.Tk.__init__(self)
        self.title("ComicBubbleOCR")
        self.geometry("600x775")
        self.image = image
        self.drawable = drawable
        self.translated_text = ""
        self.selection_bounds = None
        self.path_image_ocr = None
        self.color_balloon = None
        self.unique_layer_name = None
        self.text_color = (0, 0, 0)
        self.settings = load_settings()  # Upload the settings from the ini file
        self.init_ui()

    def init_ui(self):
        tk.Label(self, text="Input language (3 letters):").pack()
        self.lang_input = tk.Entry(self)
        self.lang_input.insert(0, self.settings["lang_input"])
        self.lang_input.pack()

        tk.Label(self, text="Output language (2 letters):").pack()
        self.lang_output = tk.Entry(self)
        self.lang_output.insert(0, self.settings["lang_output"])
        self.lang_output.pack()

        tk.Label(self, text="PSM mode of Tesseract:").pack()
        self.psm_var = tk.StringVar(value=self.settings["psm_var"])
        self.psm_display = tk.StringVar(value=self.settings["psm_display"])
        tk.OptionMenu(self, self.psm_display, *[opt[1] for opt in psm_options],
                      command=self.update_psm_selection).pack()

        tk.Label(self, text="Pre-processing of the text:").pack()
        self.preprocess_var = tk.StringVar(value=self.settings["preprocess_var"])
        tk.OptionMenu(self, self.preprocess_var, *[opt[1] for opt in preprocess_options],
                      command=self.update_preprocess_selection).pack()

        self.auto_color_var = tk.BooleanVar(value=self.settings["auto_color_var"])
        tk.Checkbutton(self, text="Automatically detects the background color",
                       variable=self.auto_color_var).pack()

        self.invert_colors_var = tk.BooleanVar(value=self.settings["invert_colors_var"])
        tk.Checkbutton(self, text="Invert colors for Tesseract (clear text on dark background)",
                       variable=self.invert_colors_var).pack()

        self.lowercase_translate_var = tk.BooleanVar(value=self.settings["lowercase_translate_var"])
        tk.Checkbutton(self, text="Translate tiny and then convert into capital letters",
                       variable=self.lowercase_translate_var).pack()

        tk.Label(self, text="Traduttore:").pack()
        self.translator_var = tk.StringVar(value=self.settings["translator_var"])
        tk.Radiobutton(self, text="LibreTranslate", variable=self.translator_var, value="libre").pack()
        tk.Radiobutton(self, text="Google Translate (At the moment it doesn't work)", variable=self.translator_var, value="google").pack()

        self.auto_anchor_var = tk.BooleanVar(value=self.settings["auto_anchor_var"])
        tk.Checkbutton(self, text="Automatically anchor the text", variable=self.auto_anchor_var).pack()

        self.process_button = tk.Button(self, text="Process selection", command=self.process_image)
        self.process_button.pack()

        tk.Label(self, text="Testo OCR:").pack()
        self.ocr_text_display = tk.Text(self, height=5, width=60)
        self.ocr_text_display.pack()

        self.retranslate_button = tk.Button(self, text="Re-Translate", command=self.retranslate_text)
        self.retranslate_button.pack()

        tk.Label(self, text="Testo tradotto:").pack()
        self.text_display = tk.Text(self, height=10, width=60)
        self.text_display.pack()

        self.save_button = tk.Button(self, text="Apply to GIMP", command=self.apply_to_gimp)
        self.save_button.pack()

        tk.Label(self, text="V. 1.1 rev.17 by MoonDragon").pack()

    def update_psm_selection(self, value):
        for opt in psm_options:
            if opt[1] == value:
                self.psm_var.set(opt[0])
                break

    def update_preprocess_selection(self, value):
        for opt in preprocess_options:
            if opt[1] == value:
                self.preprocess_var.set(opt[0])
                break

    def retranslate_text(self):
        ocr_text = self.ocr_text_display.get(1.0, tk.END).strip()
        if not ocr_text:
            tkMessageBox.showwarning("Notice", "No OCR text to be translated.")
            return

        translator = self.translator_var.get()
        lang_output = self.lang_output.get().strip().lower()
        if translator == "google":
            translated_text = translate_with_google(ocr_text, lang_output)
        else:
            lang_input = self.lang_input.get().strip().lower()
            if lang_input == "auto":
                translation_source_lang = "auto"
            else:
                tesseract_lang = LANGUAGE_MAP.get(lang_input, lang_input)
                translation_source_lang = TRANSLATION_LANG_MAP.get(tesseract_lang, "auto")
            translated_text = translate_with_libre(ocr_text, translation_source_lang, lang_output)

        self.text_display.delete(1.0, tk.END)
        self.text_display.insert(tk.END, translated_text)
        print("Re-translated text inserted into GUI: %s" % translated_text)

    def process_image(self):
        log_file = None
        if ENABLE_DEBUG:
            try:
                log_file = open("/tmp/ComicBubbleOCR_log.txt", "a")
                sys.stdout = log_file
                print("--- START LOG: %s ---" % time.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                tkMessageBox.showwarning("Notice", "Impossible to open the log file in /tmp: %s" % str(e))

        try:
            # Check the selection
            if pdb.gimp_selection_is_empty(self.image):
                print("Error: no active selection in GIMP")
                tkMessageBox.showerror("Error", "No selection active. Use the magic wand or the free selection to select the bubble.")
                self.destroy()
                return

            self.selection_bounds = get_selection_bounds(self.image)
            if not self.selection_bounds:
                print("Error: no valid selection")
                tkMessageBox.showerror("Error", "No valid selection")
                self.destroy()
                return

            lang_input = self.lang_input.get().strip().lower()
            if lang_input == "auto":
                tesseract_lang = "eng"
                translation_source_lang = "auto"
            else:
                tesseract_lang = LANGUAGE_MAP.get(lang_input, lang_input)
                translation_source_lang = TRANSLATION_LANG_MAP.get(tesseract_lang, "auto")

            self.path_image_ocr, bounds, self.color_balloon, self.unique_layer_name, self.text_color, self.ocr_text = export_image_selectioned(
                self.image, self.drawable, self.drawable.name, 
                auto_color=self.auto_color_var.get(),
                gui_psm=self.psm_var.get(),
                source_lang=tesseract_lang,
                target_lang=self.lang_output.get().strip().lower(),
                translator=self.translator_var.get(),
                invert_colors=self.invert_colors_var.get(),
                preprocess_mode=self.preprocess_var.get()
            )
            if not self.path_image_ocr or not bounds:
                print("Error: Impossible to export the selected image")
                tkMessageBox.showerror("Error", "Unable to export the selected image")
                self.destroy()
                return

            if not self.ocr_text or "Empty page" in self.ocr_text or len(self.ocr_text) <= 2:
                print("Error: no valid text extracted from Tesseract")
                tkMessageBox.showwarning("Notice", "No valid extract text. Try to modify PSM (e.g. 7 or 11) or enable/disable the reversal of colors. Control %s/ocr_image_attempt_*.png for debug." % tempfile.gettempdir())
                self.destroy()
                return

            self.ocr_text_display.delete(1.0, tk.END)
            self.ocr_text_display.insert(tk.END, self.ocr_text)

            # Translate the text
            translator = self.translator_var.get()
            lang_output = self.lang_output.get().strip().lower()
            self.translated_text = ""
            if self.ocr_text:
                text_to_translate = self.ocr_text
                if self.lowercase_translate_var.get():  # Check if the option is selected
                    text_to_translate = text_to_translate.lower()  # Converts in lowercase

                if translator == "google":
                    self.translated_text = translate_with_google(text_to_translate, lang_output)
                else:
                    lang_input = self.lang_input.get().strip().lower()
                    if lang_input == "auto":
                        translation_source_lang = "auto"
                    else:
                        tesseract_lang = LANGUAGE_MAP.get(lang_input, lang_input)
                        translation_source_lang = TRANSLATION_LANG_MAP.get(tesseract_lang, "auto")
                    self.translated_text = translate_with_libre(text_to_translate, translation_source_lang, lang_output)

                if self.lowercase_translate_var.get():  # If the option is selected, it converts in capital letters
                    self.translated_text = self.translated_text.upper()
            else:
                print("No OCR text to be translated")
                tkMessageBox.showwarning("Notice", "No OCR text to be translated")

            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(tk.END, self.translated_text)
            tkMessageBox.showinfo("Info", "Completed processing. Change the OCR or translated text if necessary.")

            # Salva le impostazioni
            self.settings.update({
                "lang_input": self.lang_input.get().strip().lower(),
                "lang_output": self.lang_output.get().strip().lower(),
                "psm_var": self.psm_var.get(),
                "psm_display": self.psm_display.get(),
                "preprocess_var": self.preprocess_var.get(),
                "auto_color_var": self.auto_color_var.get(),
                "invert_colors_var": self.invert_colors_var.get(),
                "lowercase_translate_var": self.lowercase_translate_var.get(),
                "translator_var": self.translator_var.get(),
                "auto_anchor_var": self.auto_anchor_var.get()
            })
            save_settings(self.settings)

        except Exception as e:
            print("Error in process_image: %s" % str(e))
            tkMessageBox.showerror("Error", "Error when processing: %s" % str(e))
            self.destroy()
        finally:
            if log_file:
                print("--- END log: %s ---" % time.strftime("%Y-%m-%d %H:%M:%S"))
                sys.stdout = sys.__stdout__
                log_file.close()

    def apply_to_gimp(self):
        if not self.selection_bounds:
            tkMessageBox.showerror("Error", "No valid selection.")
            print("Error in apply_to_gimp: No valid selection")
            self.destroy()
            return

        x1, y1, x2, y2 = self.selection_bounds
        text = self.text_display.get(1.0, tk.END).strip()
        if not text:
            tkMessageBox.showerror("Error", "No text to be applied.")
            print("Error in apply_to_gimp: No text provided")
            self.destroy()
            return

        try:
            print("Layer search GlobeText: %s" % self.unique_layer_name)
            layer_globe_text = pdb.gimp_image_get_layer_by_name(self.image, self.unique_layer_name)
            if not layer_globe_text:
                tkMessageBox.showerror("Error", "Layer GlobeText not found: %s" % self.unique_layer_name)
                print("Error in apply_to_gimp: Layer GlobeText not found: %s" % self.unique_layer_name)
                self.destroy()
                return

            # Calculate the rectangle inscribed (reduce 5% for the edges with a minimum of 5 pixels)
            margin = 0.05  # 5% di margine
            fixed_margin = 5  # Margine fisso in pixel
            inscribed_x1 = x1 + max(fixed_margin, (x2 - x1) * margin)
            inscribed_y1 = y1 + max(fixed_margin, (y2 - y1) * margin)
            inscribed_x2 = x2 - max(fixed_margin, (x2 - x1) * margin)
            inscribed_y2 = y2 - max(fixed_margin, (y2 - y1) * margin)
            inscribed_width = inscribed_x2 - inscribed_x1
            inscribed_height = inscribed_y2 - inscribed_y1
            print("Calculated rectangle: x1=%d, y1=%d, x2=%d, y2=%d, larghezza=%d, altezza=%d" % 
                  (inscribed_x1, inscribed_y1, inscribed_x2, inscribed_y2, inscribed_width, inscribed_height))
            print("Testo da applicare: '%s'" % text)

            # Font parameters
            font = "Sans"  # Main
            fallback_font = "Arial"  # Fallback Font
            min_font_size = 6
            max_font_size = 40  # Reduced to converge on realistic values
            reference_font_size = 10  # Font size for estimates
            interlinea_factor = 1.3  # Fixed value calibrated for Sans

            # Check Font availability
            try:
                fonts = pdb.gimp_fonts_get_list(font)
                if not fonts or not any(font.lower() in f.lower() for f in fonts[1]):
                    print("Font '%s' not found, I use Fallback '%s'" % (font, fallback_font))
                    font = fallback_font
            except Exception as e:
                print("Error in checking the font: %s, uso fallback '%s'" % (str(e), fallback_font))
                font = fallback_font
            print("Selected font: %s" % font)

            # Function to obtain the size of the text
            def get_text_extents(text, font_size):
                try:
                    width, height, _, _ = pdb.gimp_text_get_extents_fontname(text, font_size, PIXELS, font)
                    print("get_text_extents: testo='%s', font_size=%d, width=%d, height=%d" % (text, font_size, width, height))
                    return width, height
                except Exception as e:
                    print("Error in get_text_extents for text='%s', font_size=%d: %s" % (text, font_size, str(e)))
                    return 0, 0

            # Function to estimate the height of a line
            def get_line_height(font_size):
                try:
                    sample_text = "Sample Text"  # Representative text
                    _, height = get_text_extents(sample_text, font_size)
                    if height == 0:
                        print("Zero height for test text, use Fallback: %d * 1.3" % font_size)
                        return font_size * 1.3
                    estimated_height = height / 2  # Approximation for a line
                    print("get_line_height: font_size=%d, estimated_height=%f" % (font_size, estimated_height))
                    return estimated_height
                except Exception as e:
                    print("Error in get_line_height for font_size=%d: %s" % (font_size, str(e)))
                    return font_size * 1.3

            # Use Interlinea_factor Fixed to avoid problems
            print("Interlineal factor for %s: %f" % (font, interlinea_factor))

            # Function to estimate the number of lines needed
            def estimate_num_lines(text, font_size, box_width):
                words = text.split()
                current_line = ""
                num_lines = 1
                for word in words:
                    test_line = current_line + word + " " if current_line else word + " "
                    line_width, _ = get_text_extents(test_line, font_size)
                    print("estimate_num_lines: test_line='%s', line_width=%d, box_width=%d" % 
                          (test_line, line_width, box_width * 0.75))
                    if line_width > box_width * 0.75:  # Security margin of 25%
                        if current_line:
                            num_lines += 1
                            current_line = word + " "
                            print("Nuova riga: %d, corrente='%s'" % (num_lines, current_line))
                        else:
                            num_lines += 1
                            current_line = ""
                            print("Nuova riga per parola lunga: %d" % num_lines)
                    else:
                        current_line = test_line
                if current_line:
                    line_width, _ = get_text_extents(current_line, font_size)
                    if line_width > 0:
                        num_lines += 1
                        print("Adding final line for '%s', num_lines=%d" % (current_line, num_lines))
                return max(1, num_lines)

            # Create a text layer with a fixed box
            try:
                text_layer = pdb.gimp_text_layer_new(self.image, text, font, reference_font_size, PIXELS)
                if not text_layer:
                    raise Exception("Impossible to create the text layer")
                pdb.gimp_image_insert_layer(self.image, text_layer, None, 0)
                text_layer.name = "Text_" + self.unique_layer_name.split("_")[1]
                print("Created text layer: %s con font_size=%d" % (text_layer.name, reference_font_size))
            except Exception as e:
                print("Error in creating text layer: %s" % str(e))
                tkMessageBox.showerror("Error", "Error in creating text layer: %s" % str(e))
                self.destroy()
                return

            # Set the text box
            try:
                pdb.gimp_text_layer_set_text(text_layer, text)
                pdb.gimp_text_layer_resize(text_layer, inscribed_width, inscribed_height)
                pdb.gimp_layer_set_offsets(text_layer, inscribed_x1, inscribed_y1)
                pdb.gimp_text_layer_set_justification(text_layer, TEXT_JUSTIFY_CENTER)
                pdb.gimp_text_layer_set_color(text_layer, gimpcolor.RGB(*[c / 255.0 for c in self.text_color]))
                print("Text box set: width=%d, height=%d, position: x=%d, y=%d" % 
                      (inscribed_width, inscribed_height, inscribed_x1, inscribed_y1))
            except Exception as e:
                print("Error in setting the text box: %s" % str(e))
                tkMessageBox.showerror("Error", "Error in setting the text box: %s" % str(e))
                self.destroy()
                return

            # Function to check if the text adapts to the box
            def text_fits_in_box(text_layer, font_size):
                try:
                    pdb.gimp_text_layer_set_font_size(text_layer, font_size, PIXELS)
                    temp_layer = pdb.gimp_layer_new_from_drawable(text_layer, self.image)
                    pdb.gimp_image_insert_layer(self.image, temp_layer, None, 0)
                    pdb.gimp_image_select_item(self.image, CHANNEL_OP_REPLACE, temp_layer)
                    bounds = pdb.gimp_selection_bounds(self.image)
                    pdb.gimp_selection_none(self.image)
                    pdb.gimp_image_remove_layer(self.image, temp_layer)
                    if not bounds[0]:
                        print("No selection for font_size=%d" % font_size)
                        return False, 0
                    content_height = bounds[4] - bounds[2]
                    is_truncated = content_height >= inscribed_height * 0.90
                    fits = content_height <= inscribed_height * fill_factor and not is_truncated
                    print("text_fits_in_box: font_size=%d, content_height=%d, inscribed_height=%d, fill_factor=%f, is_truncated=%s, fits=%s" % 
                          (font_size, content_height, inscribed_height, fill_factor, is_truncated, fits))
                    return fits, content_height
                except Exception as e:
                    print("Error in text_fits_in_box for font_size=%d: %s" % (font_size, str(e)))
                    return False, 0

            # Determine the filling percentage
            num_lines = estimate_num_lines(text, reference_font_size, inscribed_width)
            print("Numero di righe stimato: %d" % num_lines)
            if num_lines <= 2:
                fill_factor = 0.70  # Reduced from 0.80
            elif num_lines <= 4:
                fill_factor = 0.68  # Reduced from 0.78
            else:
                fill_factor = 0.66  # Reduced from 0.76
            print("Percentage of filling: %f" % fill_factor)

            # Calculate the initial estimate of the size of the font
            estimated_font_size = int((inscribed_height * fill_factor) / (num_lines * interlinea_factor))
            estimated_font_size = max(min_font_size, min(max_font_size, estimated_font_size))
            print("Initial estimated font size: %d" % estimated_font_size)

            # Binary research to refine the size of the font
            low = max(min_font_size, estimated_font_size - 5)
            high = min(max_font_size, estimated_font_size + 5)
            best_font_size = min_font_size
            best_height = 0

            while low <= high:
                mid = (low + high) // 2
                fits, content_height = text_fits_in_box(text_layer, mid)
                print("Binary research: font_size=%d, fits=%s, content_height=%d, low=%d, high=%d" % 
                      (mid, fits, content_height, low, high))
                if fits and content_height > 0:
                    best_font_size = mid
                    best_height = content_height
                    low = mid + 1
                else:
                    high = mid - 1

            # Set the optimal font size
            try:
                pdb.gimp_text_layer_set_font_size(text_layer, best_font_size, PIXELS)
                fits, final_height = text_fits_in_box(text_layer, best_font_size)
                print("Font size: %d, final height=%d, fits=%s" % (best_font_size, final_height, fits))
            except Exception as e:
                print("Error in setting the size of the font: %s" % str(e))
                tkMessageBox.showerror("Error", "Error in setting the size of the font: %s" % str(e))
                self.destroy()
                return

            # Notice if the text is too high or the font is too small
            if final_height > inscribed_height or best_font_size == min_font_size:
                print("NOTICE: The text could be too long for the box or the font size is minimal")
                tkMessageBox.showwarning("NOTICE", "The text may not adapt correctly. "
                                                  "Consider reducing the text or font size is too small.")

            # Enter the text layer in the group
            try:
                layer_group = pdb.gimp_item_get_parent(layer_globe_text)
                if layer_group and pdb.gimp_item_is_valid(layer_group):
                    position = pdb.gimp_image_get_item_position(self.image, layer_globe_text)
                    pdb.gimp_image_reorder_item(self.image, text_layer, layer_group, position)
                    print("Text layer inserted in the group: %s" % layer_group.name)
                else:
                    position = pdb.gimp_image_get_item_position(self.image, layer_globe_text)
                    pdb.gimp_image_reorder_item(self.image, text_layer, None, position)
                    print("Text layer inserted without a group, location: %d" % position)
            except Exception as e:
                print("Error in inserting the text layer in the group: %s" % str(e))
                tkMessageBox.showerror("Error", "Error in inserting the text layer in the group: %s" % str(e))
                self.destroy()
                return

            # Automatic anchor
            if self.auto_anchor_var.get():
                print("Automatic anchor of the text layer...")
                try:
                    pdb.gimp_image_set_active_layer(self.image, layer_globe_text)
                    merged_layer = pdb.gimp_image_merge_down(self.image, text_layer, EXPAND_AS_NECESSARY)
                    merged_layer.name = self.unique_layer_name
                    print("United text layer: %s" % merged_layer.name)
                except Exception as e:
                    print("Error in apply_to_gimp during the anchor: %s" % str(e))
                    tkMessageBox.showerror("Error", "Error when anchoring the text: %s" % str(e))
                    self.destroy()
                    return
            else:
                print("Text layer left editable.")

            gimp.displays_flush()
            print("Text successfully applied")
        except Exception as e:
            print("Errore in apply_to_gimp: %s" % str(e))
            tkMessageBox.showerror("Error", "Error in the application of the text: %s" % str(e))
            self.destroy()
            return

        self.destroy()

def comic_bubble_ocr(image, drawable):
    global bubble_counter
    bubble_counter = 0
    if not pdb.gimp_selection_is_empty(image):
        gui = TranslationGUI(image, drawable)
        gui.mainloop()
    else:
        tkMessageBox.showerror("Error", "Make a selection before performing the plug-in.")

register(
    "python_fu_comic_bubble_ocr",
    "ComicBubbleOCR",
    "OCRs and translation for comics",
    "MoonDragon",
    "MoonDragon",
    "2025",
    "<Image>/Filters/ComicBubbleOCR...",
    "RGB*, GRAY*",
    [
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None)
    ],
    [],
    comic_bubble_ocr,
    menu="<Image>/Filters"
)

main()
