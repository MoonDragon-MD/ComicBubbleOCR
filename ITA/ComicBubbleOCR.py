#!/usr/bin/python
# -*- coding: utf-8 -*-
from gimpfu import *
import subprocess
import os
import configparser # Per memorizzare le impostazioni nel file ini
import tempfile
import Tkinter as tk
import tkMessageBox
from Tkinter import Toplevel, Button, Label, Canvas # Per scelta colore se trova 50% di colore di sfondo
from collections import Counter
import numpy as np
from PIL import Image # per Pillow
import requests
import re
import time
import sys
import gimpcolor
import locale
locale.setlocale(locale.LC_ALL, 'C')  # Forza la localizzazione inglese per evitare problemi di formattazione numerica


# ComicBubbleOCR by MoonDragon
# V. 1.1 rev.17
# Sito web: https://github.com/MoonDragon-MD/ComicBubbleOCR

## Dipendenze
# wget https://old-releases.ubuntu.com/ubuntu/pool/universe/p/pygtk/python-gtk2_2.24.0-6_amd64.deb
# wget https://old-releases.ubuntu.com/ubuntu/pool/universe/g/gimp/gimp-python_2.10.8-2_amd64.deb
# sudo dpkg -i python-gtk2_2.24.0-6_amd64.deb
# sudo dpkg -i gimp-python_2.10.8-2_amd64.deb
# sudo apt-get install python-tk tesseract-ocr-* (*= language es jpn)
# sudo apt install -f  # Fix any dependency issues
# curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
# python2.7 get-pip.py
# python2.7 -m pip install requests googletrans==2.4.0 Pillow
## Mettere ComicBubbleOCR.py in
# ~/.config/GIMP/2.10/plug-ins/
# dare permessi di esecuzione
# chmod +x ~/.config/GIMP/2.10/plug-ins/ComicBubbleOCR.py

# Abilita/disabilita creazione txt debug
ENABLE_DEBUG = False

# Contatore globale per le bolle
bubble_counter = 0

# Mappatura per lingue
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

# Costanti
BText = "GlobeText"
g_nameFileImageOCR = "ocr_image.png"

# Opzioni PSM Tesseract OCR
psm_options = [
    ("0", "Orientamento e rilevamento (OSD)"),
    ("1", "Rilevamento automatico con OSD"),
    ("2", "Rilevamento automatico, nessun OSD o OCR"),
    ("3", "Completamente automatico,no OSD (predefinito)"),
    ("4", "Singola colonna di testo di dimensioni variabili"),
    ("5", "Singolo blocco uniforme di testo verticale"),
    ("6", "Singolo blocco di testo uniforme"),
    ("7", "Riga di testo singola"),
    ("8", "Singola parola"),
    ("9", "Singola parola a cerchio"),
    ("10", "Carattere singolo"),
    ("11", "Testo sparso, trova più testo possibile"),
    ("12", "Testo sparso con OSD"),
    ("13", "Raw line, bypassing hacks")
]

# Percorso del file di configurazione
CONFIG_FILE = "/tmp/ComicBubbleOCR.ini"

# Impostazioni predefinite
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

# Opzioni di preelaborazione del testo
preprocess_options = [
    ("none", "Nessuna pre-elaborazione"),
    ("join_hyphen", "Unisce le interruzioni di riga con -"),
    ("join_space", "Unisce tutte le interruzioni di riga con uno spazio"),
    ("remove_duplicate_returns", "Rimuovere a-capo doppi"),
    ("remove_duplicate_spaces", "Rimuovere gli spazi doppi")
]

# Gestiscono il salvataggio delle mpostazioni nel file ini
def load_settings():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        print("File di configurazione %s non trovato, creazione con valori predefiniti" % CONFIG_FILE)
        config['Settings'] = DEFAULT_SETTINGS
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            print("Errore nella creazione del file di configurazione: %s" % str(e))
            return DEFAULT_SETTINGS
    try:
        config.read(CONFIG_FILE)
        settings = dict(config['Settings'])
        # Converti stringhe booleane in valori booleani
        settings['auto_color_var'] = config.getboolean('Settings', 'auto_color_var')
        settings['invert_colors_var'] = config.getboolean('Settings', 'invert_colors_var')
        settings['lowercase_translate_var'] = config.getboolean('Settings', 'lowercase_translate_var')
        settings['auto_anchor_var'] = config.getboolean('Settings', 'auto_anchor_var')
        print("Impostazioni caricate da %s: %s" % (CONFIG_FILE, settings))
        return settings
    except Exception as e:
        print("Errore nella lettura del file di configurazione: %s, uso valori predefiniti" % str(e))
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
        print("Impostazioni salvate in %s: %s" % (CONFIG_FILE, settings))
    except Exception as e:
        print("Errore nel salvataggio del file di configurazione: %s" % str(e))

# Funzione di preelaborazione
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

# Funzioni di traduzione
def translate_with_google(text, target_lang="it"):
    try:
        from googletrans import Translator
        translator = Translator()
        print("Tentativo di traduzione con Google Translate, testo: '%s', lingua: '%s'" % (text, target_lang))
        translated = translator.translate(text, dest=target_lang)
        if translated is None or translated.text is None:
            raise ValueError("Risposta di Google Translate vuota o non valida")
        print("Traduzione Google Translate riuscita: '%s'" % translated.text)
        return translated.text
    except Exception as e:
        error_msg = "Google Translate errore: %s" % str(e)
        print(error_msg)
        tkMessageBox.showwarning("Avviso", "%s. Tentativo con LibreTranslate..." % error_msg)
        try:
            translated_text = translate_with_libre(text, source_lang="auto", target_lang=target_lang)
            print("Traduzione LibreTranslate riuscita: '%s'" % translated_text)
            return translated_text
        except Exception as libre_e:
            error_msg = "LibreTranslate errore: %s" % str(libre_e)
            print(error_msg)
            tkMessageBox.showerror("Errore", "%s. Restituisco il testo originale." % error_msg)
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
        tkMessageBox.showerror("Errore", "LibreTranslate errore: %s" % str(e))
        return text

def get_selection_bounds(image):
    """Ottiene i confini della selezione, restituendo None se vuota."""
    if pdb.gimp_selection_is_empty(image):
        tkMessageBox.showerror("Errore", "Nessuna selezione attiva trovata.")
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
    """Calcola la luminosità di un colore RGB."""
    return (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])

def choose_color_popup(colors, counts, total_samples):
    """Mostra un popup per scegliere tra due colori con frequenze simili."""
    root = Toplevel()
    root.title("Seleziona Colore di Sfondo")
    root.geometry("300x150")
    
    selected_color = [None]  # Variabile per memorizzare il colore scelto
    
    def select_color(color):
        selected_color[0] = color
        root.destroy()
    
    Label(root, text="Due colori hanno frequenze simili. Scegli il colore di sfondo:").pack(pady=10)
    
    for color, count in zip(colors, counts):
        percentage = (count / float(total_samples)) * 100
        color_str = "#{:02x}{:02x}{:02x}".format(*color)
        frame = tk.Frame(root)
        frame.pack(pady=5)
        canvas = Canvas(frame, width=50, height=20, bg=color_str, relief="raised", borderwidth=1)
        canvas.pack(side=tk.LEFT, padx=5)
        Button(frame, text="Scegli (%.1f%%)" % percentage, command=lambda c=color: select_color(c)).pack(side=tk.LEFT)
    
    root.wait_window()  # Aspetta che l'utente chiuda il popup
    return selected_color[0]

def export_image_selectioned(image, drawable, name_layer, auto_color=False, gui_psm='3', source_lang='auto', target_lang='it', translator='libre', invert_colors=False, preprocess_mode='none'):
    temp_files = []  # Lista per tracciare tutti i file temporanei
    """
    Esporta la selezione della bolla, crea un nuovo layer, prepara l'immagine per l'OCR e restituisce il testo OCR.

    Parametri:
    - image: Immagine GIMP
    - drawable: Layer attivo da cui copiare la selezione
    - name_layer: Nome base per i layer
    - auto_color: Se True, campiona il colore della bolla
    - gui_psm: Modalità PSM per Tesseract (default: 7)
    - source_lang: Lingua sorgente per OCR (default: auto)
    - target_lang: Lingua target per la traduzione
    - translator: 'google' o 'libre' per scegliere il traduttore
    - invert_colors: Se True, inverte i colori dell'immagine OCR
    - preprocess_mode: Modalità di pre-elaborazione del testo
    """
    try:
        # 1. Ottieni i confini della selezione
        bounds = get_selection_bounds(image)
        if not bounds:
            print("Errore: Nessuna selezione valida")
            tkMessageBox.showerror("Errore", "Nessuna selezione valida. Usa la selezione libera o la bacchetta magica per includere il balloon.")
            return None, None, None, None, None, None
        x1, y1, x2, y2 = bounds
        print("Confini selezione: x1=%d, y1=%d, x2=%d, y2=%d" % (x1, y1, x2, y2))

        # 2. Salva la selezione originale
        original_selection = pdb.gimp_selection_save(image)
        original_selection.name = "Original_Selection"
        print("Selezione originale salvata, vuota: %s" % pdb.gimp_selection_is_empty(image))

        # 3. Crea un nuovo layer con la selezione copiata
        pdb.gimp_image_select_item(image, 2, original_selection)
        if not pdb.gimp_edit_copy(drawable):
            print("Errore: Impossibile copiare la selezione")
            tkMessageBox.showerror("Errore", "Impossibile copiare la selezione")
            return None, None, None, None, None, None
        new_layer = pdb.gimp_layer_new(image, image.width, image.height, RGBA_IMAGE, "BubbleLayer", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image, new_layer, None, 0)
        pdb.gimp_drawable_fill(new_layer, FILL_TRANSPARENT)
        floating_sel = pdb.gimp_edit_paste(new_layer, False)
        pdb.gimp_floating_sel_anchor(floating_sel)
        print("Nuovo layer 'BubbleLayer' creato con la selezione copiata")

        # 4. Prepara l'immagine per l'OCR usando il rettangolo esterno
        print("Preparazione immagine per OCR")
        margin = 2
        ocr_x1 = max(0, x1 - margin)
        ocr_y1 = max(0, y1 - margin)
        ocr_x2 = min(image.width, x2 + margin)
        ocr_y2 = min(image.height, y2 + margin)
        print("Rettangolo OCR: x1=%d, y1=%d, x2=%d, y2=%d" % (ocr_x1, ocr_y1, ocr_x2, ocr_y2))
        pdb.gimp_image_select_rectangle(image, 2, ocr_x1, ocr_y1, ocr_x2 - ocr_x1, ocr_y2 - ocr_y1)
        width, height = ocr_x2 - ocr_x1, ocr_y2 - ocr_y1
        if width < 10 or height < 10:
            print("Errore: Selezione OCR troppo piccola (larghezza=%d, altezza=%d)" % (width, height))
            tkMessageBox.showerror("Errore", "Selezione OCR troppo piccola (minimo 10x10 pixel)")
            return None, None, None, None, None, None
        if not pdb.gimp_edit_copy(drawable):
            raise Exception("Errore: Impossibile copiare la selezione per OCR")
        image_selection = pdb.gimp_edit_paste_as_new_image()
        if not image_selection or not image_selection.layers:
            raise Exception("Errore: Impossibile creare l'immagine temporanea per OCR")
        layer_background = pdb.gimp_layer_new(image_selection, image_selection.width, image_selection.height,
                                             RGBA_IMAGE, "Background", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image_selection, layer_background, None, 1)
        pdb.gimp_layer_set_lock_alpha(layer_background, False)
        pdb.gimp_context_set_background(gimpcolor.RGB(1.0, 1.0, 1.0))
        pdb.gimp_drawable_fill(layer_background, FILL_BACKGROUND)
        temp_dir = tempfile.gettempdir()
        path_image_ocr = os.path.join(temp_dir, "ocr_image.png")

        # 5. Tentativi OCR con diversi PSM
        ocr_text = ""
        psm_values = [gui_psm, '7', '6', '11']  # Usa gui_psm come primo tentativo, seguito da 7, 6, 11
        successful_attempt = None

        # Crea una copia dell'immagine selezionata una volta per tutti i tentativi
        if not pdb.gimp_edit_copy(drawable):
            raise Exception("Errore: Impossibile copiare la selezione per OCR")
        image_selection = pdb.gimp_edit_paste_as_new_image()
        if not image_selection or not image_selection.layers:
            raise Exception("Errore: Impossibile creare l'immagine temporanea per OCR")

        # Aggiungi un layer di sfondo bianco per uniformità
        layer_background = pdb.gimp_layer_new(image_selection, image_selection.width, image_selection.height,
                                              RGBA_IMAGE, "Background", 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image_selection, layer_background, None, 1)
        pdb.gimp_layer_set_lock_alpha(layer_background, False)
        pdb.gimp_context_set_background(gimpcolor.RGB(1.0, 1.0, 1.0))
        pdb.gimp_drawable_fill(layer_background, FILL_BACKGROUND)

        # Ciclo sui diversi PSM per tentativi OCR
        for attempt, psm in enumerate(psm_values, 1):
            print("Tentativo OCR %d con PSM %s" % (attempt, psm))

            # Duplica l'immagine originale per ogni tentativo
            temp_image = pdb.gimp_image_duplicate(image_selection)
            output_path = os.path.join(temp_dir, "ocr_image_attempt_%d.png" % attempt)
            temp_files.append(output_path)  # Aggiungi il file alla lista

            # Preprocessing dell'immagine in base alla luminosità o inversione colori
            if invert_colors:
                print("Applicazione inversione colori")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Salva l'immagine preprocessata come PNG
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Immagine salvata in: %s" % output_path)
                # Verifica che il file esista e non sia troppo piccolo
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Errore: File %s non creato o troppo piccolo" % output_path)
            except Exception as e:
                print("Errore nel salvataggio immagine OCR (tentativo %d): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                continue

            # Controlla la varianza dell'immagine per evitare falsi negativi
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Varianza pixel immagine (tentativo %d): %f" % (attempt, variance))
                if variance < 20:
                    print("Immagine con varianza bassa, probabile assenza di testo (tentativo %d)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    continue
            except Exception as e:
                print("Errore nel controllo varianza immagine (tentativo %d): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                continue

            # Esegui Tesseract con il PSM corrente
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Aggiungi il file di testo alla lista
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", psm, "-l", source_lang]
            print("Esecuzione Tesseract (tentativo %d): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (tentativo %d): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Testo estratto (tentativo %d): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                        break
                else:
                    print("Errore: File di output %s non trovato" % output_file)
            except subprocess.CalledProcessError as e:
                print("Errore in Tesseract (tentativo %d): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Errore in Tesseract (tentativo %d): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # 5.1 Tentativo aggiuntivo con rettangolo inscritto (10%%)
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Tentativo OCR aggiuntivo con rettangolo inscritto (riduzione 10%%, PSM 7)")
            attempt = 4

            # Duplica l'immagine originale
            temp_image = pdb.gimp_image_duplicate(image_selection)

            # Calcola il rettangolo inscritto (riduci del 10%%)
            shrink_margin = int(min(temp_image.width, temp_image.height) * 0.1)
            inner_x1 = shrink_margin
            inner_y1 = shrink_margin
            inner_x2 = temp_image.width - shrink_margin
            inner_y2 = temp_image.height - shrink_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Rettangolo inscritto (10%%) troppo piccolo, uso selezione originale")
                inner_x1, inner_y1, inner_x2, inner_y2 = 0, 0, temp_image.width, temp_image.height
            else:
                print("Rettangolo inscritto (10%%): x1=%d, y1=%d, x2=%d, y2=%d" % (inner_x1, inner_y1, inner_x2, inner_y2))
                pdb.gimp_image_select_rectangle(temp_image, 2, inner_x1, inner_y1, inner_x2 - inner_x1, inner_y2 - inner_y1)
                if not pdb.gimp_edit_copy(temp_image.layers[0]):
                    print("Errore: Impossibile copiare il rettangolo inscritto (10%%)")
                    pdb.gimp_image_delete(temp_image)
                else:
                    inscribed_image = pdb.gimp_edit_paste_as_new_image()
                    pdb.gimp_image_delete(temp_image)
                    temp_image = inscribed_image

            output_path = os.path.join(temp_dir, "ocr_image_attempt_inscribed_%d.png" % attempt)
            temp_files.append(output_path)  # Aggiungi il file alla lista

            # Preprocessing (inversione colori se necessario)
            if invert_colors:
                print("Applicazione inversione colori (inscritto 10%%)")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Salva l'immagine
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Immagine salvata in: %s" % output_path)
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Errore: File %s non creato o troppo piccolo" % output_path)
            except Exception as e:
                print("Errore nel salvataggio immagine OCR (tentativo %d, inscritto 10%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Controlla la varianza
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Varianza pixel immagine (tentativo %d, inscritto 10%%): %f" % (attempt, variance))
                if variance < 20:
                    print("Immagine con varianza bassa, probabile assenza di testo (tentativo %d, inscritto 10%%)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    return None, None, None, None, None, None
            except Exception as e:
                print("Errore nel controllo varianza immagine (tentativo %d, inscritto 10%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Esegui Tesseract con PSM 7
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Aggiungi il file di testo alla lista
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", "7", "-l", source_lang]
            print("Esecuzione Tesseract (tentativo %d, inscritto 10%%): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (tentativo %d, inscritto 10%%): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Testo estratto (tentativo %d, inscritto 10%%): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                else:
                    print("Errore: File di output %s non trovato" % output_file)
            except subprocess.CalledProcessError as e:
                print("Errore in Tesseract (tentativo %d, inscritto 10%%): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Errore in Tesseract (tentativo %d, inscritto 10%%): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # 5.2 Tentativo aggiuntivo con rettangolo inscritto più piccolo (20%%)
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Tentativo OCR aggiuntivo con rettangolo inscritto più piccolo (riduzione 20%%, PSM 6)")
            attempt = 5

            # Duplica l'immagine originale
            temp_image = pdb.gimp_image_duplicate(image_selection)

            # Calcola il rettangolo inscritto (riduci del 20%%)
            shrink_margin = int(min(temp_image.width, temp_image.height) * 0.2)
            inner_x1 = shrink_margin
            inner_y1 = shrink_margin
            inner_x2 = temp_image.width - shrink_margin
            inner_y2 = temp_image.height - shrink_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Rettangolo inscritto (20%%) troppo piccolo, uso selezione originale")
                inner_x1, inner_y1, inner_x2, inner_y2 = 0, 0, temp_image.width, temp_image.height
            else:
                print("Rettangolo inscritto (20%%): x1=%d, y1=%d, x2=%d, y2=%d" % (inner_x1, inner_y1, inner_x2, inner_y2))
                pdb.gimp_image_select_rectangle(temp_image, 2, inner_x1, inner_y1, inner_x2 - inner_x1, inner_y2 - inner_y1)
                if not pdb.gimp_edit_copy(temp_image.layers[0]):
                    print("Errore: Impossibile copiare il rettangolo inscritto (20%%)")
                    pdb.gimp_image_delete(temp_image)
                else:
                    inscribed_image = pdb.gimp_edit_paste_as_new_image()
                    pdb.gimp_image_delete(temp_image)
                    temp_image = inscribed_image

            output_path = os.path.join(temp_dir, "ocr_image_attempt_inscribed_%d.png" % attempt)
            temp_files.append(output_path)  # Aggiungi il file alla lista

            # Preprocessing (inversione colori forzata per il quinto tentativo)
            if invert_colors or attempt == 5:
                print("Applicazione inversione colori (inscritto 20%%)")
                pdb.gimp_drawable_invert(temp_image.layers[0], False)

            # Salva l'immagine
            try:
                pdb.gimp_image_merge_visible_layers(temp_image, CLIP_TO_IMAGE)
                pdb.file_png_save(temp_image, temp_image.layers[0], output_path, output_path, 0, 9, 1, 1, 1, 1, 1)
                print("Immagine salvata in: %s" % output_path)
                if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
                    raise Exception("Errore: File %s non creato o troppo piccolo" % output_path)
            except Exception as e:
                print("Errore nel salvataggio immagine OCR (tentativo %d, inscritto 20%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Controlla la varianza
            try:
                img = Image.open(output_path).convert("L")
                pixel_data = np.array(img)
                variance = np.var(pixel_data)
                print("Varianza pixel immagine (tentativo %d, inscritto 20%%): %f" % (attempt, variance))
                if variance < 20:
                    print("Immagine con varianza bassa, probabile assenza di testo (tentativo %d, inscritto 20%%)" % attempt)
                    pdb.gimp_image_delete(temp_image)
                    return None, None, None, None, None, None
            except Exception as e:
                print("Errore nel controllo varianza immagine (tentativo %d, inscritto 20%%): %s" % (attempt, str(e)))
                pdb.gimp_image_delete(temp_image)
                return None, None, None, None, None, None

            # Esegui Tesseract con PSM 8 (singola parola) per il quinto tentativo
            output_base = os.path.join(temp_dir, "ocr_output_%d" % attempt)
            temp_files.append(output_base + ".txt")  # Aggiungi il file di testo alla lista
            cmd = ["tesseract", output_path, output_base, "--oem", "3", "--psm", "6", "-l", source_lang]
            print("Esecuzione Tesseract (tentativo %d, inscritto 20%%): %s" % (attempt, " ".join(cmd)))
            try:
                result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                print("Output Tesseract (tentativo %d, inscritto 20%%): %s" % (attempt, result))
                output_file = output_base + ".txt"
                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        ocr_text = f.read().strip()
                    print("Testo estratto (tentativo %d, inscritto 20%%): %s" % (attempt, ocr_text))
                    if ocr_text and "Empty page" not in ocr_text and len(ocr_text) > 2:
                        successful_attempt = attempt
                else:
                    print("Errore: File di output %s non trovato" % output_file)
            except subprocess.CalledProcessError as e:
                print("Errore in Tesseract (tentativo %d, inscritto 20%%): %s, output: %s" % (attempt, str(e), e.output))
            except Exception as e:
                print("Errore in Tesseract (tentativo %d, inscritto 20%%): %s" % (attempt, str(e)))
            finally:
                if os.path.exists(output_base + ".txt"):
                    os.remove(output_base + ".txt")
                pdb.gimp_image_delete(temp_image)

        # Controllo finale per il risultato dell'OCR
        if not ocr_text or "Empty page" in ocr_text or len(ocr_text) <= 2:
            print("Errore: Nessun testo valido estratto da Tesseract dopo %d tentativi" % (len(psm_values) + 2))
            tkMessageBox.showwarning("Avviso", "Nessun testo valido estratto. Verifica la lingua (es. 'ara' per Arabo) e controlla %s/ocr_image_attempt_*.png per debug." % temp_dir)
            return None, None, None, None, None, None

        # 6. Pre-elabora il testo OCR
        ocr_text = preprocess_text(ocr_text, preprocess_mode)

        # 7. Campionamento del colore (solo all'interno del rettangolo iscritto)
        color_balloon = (255, 255, 255)  # Default background: white
        text_color = (0, 0, 0)  # Default text: black
        if auto_color:
            print("Iniziando campionamento colori...")
            colors = []
            pdb.gimp_image_select_item(image, 2, original_selection)
            width, height = x2 - x1, y2 - y1
            # Campione solo all'interno del rettangolo inscritto (per escludere i bordi)
            edge_margin = 5
            inner_x1, inner_y1 = x1 + edge_margin, y1 + edge_margin
            inner_x2, inner_y2 = x2 - edge_margin, y2 - edge_margin
            if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
                print("Errore: Rettangolo iscritto troppo piccolo, uso selezione completa")
                inner_x1, inner_y1, inner_x2, inner_y2 = x1, y1, x2, y2
            step = max(1, min(inner_x2 - inner_x1, inner_y2 - inner_y1) // 10)  # Finer sampling
            for y in range(inner_y1, inner_y2, step):
                for x in range(inner_x1, inner_x2, step):
                    if pdb.gimp_selection_value(image, x, y) > 0:
                        pixel = pdb.gimp_drawable_get_pixel(new_layer, x, y)
                        if pixel and len(pixel[1]) >= 4 and pixel[1][3] > 0:
                            colors.append(tuple(pixel[1][:3]))
                            print("Colore campionato a (%d, %d): %s" % (x, y, tuple(pixel[1][:3])))
            if colors:
                color_counts = Counter(colors)
                # Filter colors with at least 5% frequency
                total_samples = len(colors)
                min_count = total_samples * 0.05  # 5% per includere #f3e6d3
                top_colors = [(color, count) for color, count in color_counts.most_common() if count >= min_count]
                if len(top_colors) >= 1:
                    color_balloon = top_colors[0][0]  # Colore più comune per lo sfondo
                    brightness = calculate_brightness(color_balloon)
                    if len(top_colors) >= 2:
                        count1, count2 = top_colors[0][1], top_colors[1][1]
                        percent1, percent2 = (count1 / float(total_samples)) * 100, (count2 / float(total_samples)) * 100
                        if abs(percent1 - percent2) <= 5:  # Similar frequencies (50% ± 5%), show popup
                            print("Due colori con frequenze simili: %s (%.1f%%), %s (%.1f%%)" % (top_colors[0][0], percent1, top_colors[1][0], percent2))
                            chosen_color = choose_color_popup([top_colors[0][0], top_colors[1][0]], [count1, count2], total_samples)
                            if chosen_color:
                                color_balloon = chosen_color
                                text_color = top_colors[1][0] if chosen_color == top_colors[0][0] else top_colors[0][0]
                                print("Colore sfondo scelto: %s, colore testo: %s" % (color_balloon, text_color))
                            else:
                                print("Nessun colore scelto, uso il più comune: %s" % str(color_balloon))
                                text_color = top_colors[1][0]  # Default to second color
                        else:
                            # Due colori con frequenze diverse
                            text_color = top_colors[1][0]  # Use second color for text
                            print("Due colori rilevati, sfondo: %s (%.1f%%), testo: %s (%.1f%%)" % (color_balloon, percent1, text_color, percent2))
                    else:
                        # Un solo colore rilevato
                        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                        print("Un solo colore rilevato, sfondo: %s, luminosità: %f, testo: %s" % (color_balloon, brightness, text_color))

                    # Verifica se colore sfondo e colore testo sono uguali o troppo simili
                    def color_distance(c1, c2):
                        return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)**0.5

                    if color_balloon == text_color or color_distance(color_balloon, text_color) < 20:  # Soglia di similarità
                        print("Avviso: Colore sfondo (%s) e colore testo (%s) sono uguali o troppo simili" % (color_balloon, text_color))
                        text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                        print("Colore testo modificato in base alla luminosità: %s" % str(text_color))
                else:
                    # Fallback se non ci sono colori validi
                    color_balloon = top_colors[0][0] if top_colors else (255, 255, 255)
                    brightness = calculate_brightness(color_balloon)
                    text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                    print("Nessun colore valido con frequenza >= 5%, uso sfondo: %s, testo: %s" % (color_balloon, text_color))
            else:
                print("Nessun colore valido campionato, uso bianco di default")
                color_balloon = (255, 255, 255)
                brightness = calculate_brightness(color_balloon)
                text_color = (0, 0, 0)
                print("Colore sfondo finale: %s, colore testo finale: %s" % (color_balloon, text_color))
            print("Colore sfondo finale: %s, colore testo finale: %s" % (color_balloon, text_color))

        # 8. Ottimizza la selezione per riempire la bolla
        pdb.gimp_image_select_item(image, 2, original_selection)
        temp_mask = pdb.gimp_selection_save(image)
        temp_mask.name = "Temp_Mask"
        print("Canale Temp_Mask creato")
        for _ in range(2):  # Ridotto a 2 iterazioni
            # Applica sfocatura e ottimizzazione
            pdb.plug_in_gauss(image, temp_mask, 10.0, 10.0, 0)  # Raggio ridotto a 10.0
        print("Esecuzione pdb.plug_in_gauss (iterativa)")
        pdb.gimp_drawable_threshold(temp_mask, HISTOGRAM_VALUE, 0.1, 1.0)
        pdb.gimp_image_select_item(image, 2, temp_mask)
        pdb.gimp_selection_grow(image, 3)  # Espansione ridotta a 3 pixel
        pdb.gimp_selection_shrink(image, 2)
        pdb.gimp_selection_feather(image, 2.0)
        optimized_selection = pdb.gimp_selection_save(image)
        optimized_selection.name = "Optimized_Selection"
        print("Selezione ottimizzata salvata, vuota: %s" % pdb.gimp_selection_is_empty(image))

        # 8.1 Riduci la selezione del 4% per compensare lo sbordamento
        pdb.gimp_image_select_item(image, 2, optimized_selection)
        bounds = pdb.gimp_selection_bounds(image)[1:5]
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        shrink_amount = max(3, int(min(width, height) * 0.04))  # 4% con minimo 3 pixel
        if shrink_amount > 0:
            pdb.gimp_selection_shrink(image, shrink_amount)
            print("Selezione ridotta del 4%% (shrink_amount=%d)" % shrink_amount)
        else:
            print("Shrink amount è 0, nessuna riduzione applicata")
        optimized_selection_reduced = pdb.gimp_selection_save(image)
        optimized_selection_reduced.name = "Optimized_Selection_Reduced"
        print("Selezione ridotta salvata, vuota: %s" % pdb.gimp_selection_is_empty(image))

        # Debug visivo della selezione ridotta
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
            print("Selezione ridotta salvata per debug: %s" % debug_path)
            pdb.gimp_image_delete(temp_selection_image)

        # 9. Crea e riempi un nuovo layer per la bolla
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        layer_group = pdb.gimp_layer_group_new(image)
        layer_group.name = "Group_%s_%s" % (name_layer, timestamp)
        pdb.gimp_image_insert_layer(image, layer_group, None, 0)
        print("Nuovo gruppo di layer creato: %s" % layer_group.name)
        layer_globe_text = pdb.gimp_layer_new(image, image.width, image.height, RGBA_IMAGE,
                                              "GlobeText_%s" % timestamp, 100, LAYER_MODE_NORMAL)
        pdb.gimp_image_insert_layer(image, layer_globe_text, layer_group, 0)
        pdb.gimp_drawable_fill(layer_globe_text, FILL_TRANSPARENT)
        print("Creazione layer GlobeText vuoto")

        # 10. Riempi la selezione con il colore di sfondo
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)  # Usa la selezione ridotta
        pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
        print("Riempimento base con colore: %s" % str(color_balloon))

        # Calcola le dimensioni della selezione e dividi in una griglia 3x3
        width = x2 - x1
        height = y2 - y1
        print("Dimensioni selezione: larghezza=%d, altezza=%d" % (width, height))

        # Dividi in tre parti per larghezza e altezza
        x_step = width // 3
        y_step = height // 3
        # Definisci i punti centrali della griglia 3x3
        brush_points = []
        margin = 10  # Margine per evitare i bordi
        for i in range(3):
            for j in range(3):
                bx = x1 + (i * x_step + x_step // 2)
                by = y1 + (j * y_step + y_step // 2)
                bx = min(max(x1 + margin, bx), x2 - margin)
                by = min(max(y1 + margin, by), y2 - margin)
                brush_points.append((bx, by))
        print("Punti della griglia 3x3 per il pennello: %s" % str(brush_points))

        # Imposta il pennello e le sue proprietà
        try:
            pdb.gimp_context_set_brush("2. Hardness 100")
            pdb.gimp_context_set_dynamics("Basic Simple")
        except:
            print("Pennello '2. Hardness 100' o dinamica 'Basic Simple' non trovato, uso 'GIMP Brush'")
            pdb.gimp_context_set_brush("GIMP Brush")
            pdb.gimp_context_set_dynamics("Dynamics Off")

        # Imposta la dimensione del pennello in base alla dimensione della selezione
        brush_size = max(100.0, min(width, height) * 0.4)  # 40% della dimensione minore, minimo 100
        pdb.gimp_context_set_brush_size(brush_size)
        pdb.gimp_context_set_opacity(100.0)
        pdb.gimp_context_set_paint_mode(LAYER_MODE_NORMAL)
        print("Dimensione pennello impostata: %f" % brush_size)

        # Applica il pennello tre volte per ogni punto centrale
        for i, (bx, by) in enumerate(brush_points, 1):
            print("Applicazione pennello al punto %d (%d, %d) con dimensione %f" % (i, bx, by, brush_size))
            for pass_num in range(1, 4):
                pdb.gimp_paintbrush(layer_globe_text, 0, 4, [bx, by, bx, by, bx, by, bx, by], PAINT_INCREMENTAL, 0)
                print("Passata %d completata per punto (%d, %d)" % (pass_num, bx, by))

        # Aggiungi pennellate lungo gli assi della griglia 3x3
        print("Applicazione pennellate lungo gli assi della griglia")
        # Definisci i punti di inizio e fine per ogni riga (orizzontale) e colonna (verticale)
        rows = [y1 + (j * y_step + y_step // 2) for j in range(3)]  # Centri delle righe
        cols = [x1 + (i * x_step + x_step // 2) for i in range(3)]  # Centri delle colonne
        for row_y in rows:
            row_y = min(max(y1 + margin, row_y), y2 - margin)
            # Left-to-right
            coords_lr = []
            for x in range(x1 + margin, x2 - margin + 1, max(1, int(brush_size / 4))):
                coords_lr.extend([x, row_y])
            if len(coords_lr) >= 4:
                print("Pennellata sinistra-destra a y=%d: %s" % (row_y, coords_lr))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_lr), coords_lr, PAINT_INCREMENTAL, 0)
                    print("Passata %d sinistra-destra completata a y=%d" % (pass_num, row_y))
            # Right-to-left
            coords_rl = []
            for x in range(x2 - margin, x1 + margin - 1, -max(1, int(brush_size / 4))):
                coords_rl.extend([x, row_y])
            if len(coords_rl) >= 4:
                print("Pennellata destra-sinistra a y=%d: %s" % (row_y, coords_rl))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_rl), coords_rl, PAINT_INCREMENTAL, 0)
                    print("Passata %d destra-sinistra completata a y=%d" % (pass_num, row_y))
        for col_x in cols:
            col_x = min(max(x1 + margin, col_x), x2 - margin)
            # Top-to-bottom
            coords_tb = []
            for y in range(y1 + margin, y2 - margin + 1, max(1, int(brush_size / 4))):
                coords_tb.extend([col_x, y])
            if len(coords_tb) >= 4:
                print("Pennellata alto-basso a x=%d: %s" % (col_x, coords_tb))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_tb), coords_tb, PAINT_INCREMENTAL, 0)
                    print("Passata %d alto-basso completata a x=%d" % (pass_num, col_x))
            # Bottom-to-top
            coords_bt = []
            for y in range(y2 - margin, y1 + margin - 1, -max(1, int(brush_size / 4))):
                coords_bt.extend([col_x, y])
            if len(coords_bt) >= 4:
                print("Pennellata basso-alto a x=%d: %s" % (col_x, coords_bt))
                for pass_num in range(1, 4):
                    pdb.gimp_paintbrush(layer_globe_text, 0, len(coords_bt), coords_bt, PAINT_INCREMENTAL, 0)
                    print("Passata %d basso-alto completata a x=%d" % (pass_num, col_x))

        print("Riempimento finale con selezione ottimizzata")
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)

        # 11. Sfoca il layer e applica la maschera
        print("Applicazione sfocatura al layer GlobeText")
        pdb.plug_in_gauss(image, layer_globe_text, 10.0, 10.0, 0)
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_selection_shrink(image, 2)
        layer_mask = pdb.gimp_layer_create_mask(layer_globe_text, ADD_MASK_SELECTION)
        pdb.gimp_layer_add_mask(layer_globe_text, layer_mask)
        pdb.plug_in_gauss(image, layer_mask, 5.0, 5.0, 0)
        pdb.gimp_layer_remove_mask(layer_globe_text, MASK_APPLY)
        print("Creazione maschera di layer dalla selezione ottimizzata")

        # 10.bis Applicazione riempimento addizionale con selezione ridotta del 10%
        print("Applicazione riempimento addizionale con selezione ridotta del 10%%")
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        bounds = pdb.gimp_selection_bounds(image)[1:5]
        x1, y1, x2, y2 = bounds
        width = x2 - x1
        height = y2 - y1
        shrink_amount = int(min(width, height) * 0.05)  # 5% della dimensione minore
        if shrink_amount > 0:
            pdb.gimp_selection_shrink(image, shrink_amount)
            if not pdb.gimp_selection_is_empty(image):
                pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
                print("Riempimento addizionale applicato con shrink_amount=%d" % shrink_amount)
            else:
                print("Selezione ridotta è vuota, nessun riempimento addizionale")
        else:
            print("Shrink amount è 0, nessun riempimento addizionale")

        # Riempimento finale per uniformità
        pdb.gimp_image_select_item(image, 2, optimized_selection_reduced)
        pdb.gimp_context_set_background(gimpcolor.RGB(*[c / 255.0 for c in color_balloon]))
        pdb.gimp_drawable_edit_fill(layer_globe_text, FILL_BACKGROUND)
        print("Riempimento finale completato")

        # 12. Verifica il contenuto del layer
        center_x = x1 + (x2 - x1) // 2
        center_y = y1 + (y2 - y1) // 2
        print("Verifica trasparenza layer GlobeText al punto centrale (%d, %d)" % (center_x, center_y))
        pixel_value = pdb.gimp_drawable_get_pixel(layer_globe_text, center_x, center_y)
        print("Valore pixel layer GlobeText al punto (%d, %d): %s" % (center_x, center_y, pixel_value))

    except Exception as e:
        print("Errore: %s" % str(e))
        tkMessageBox.showerror("Errore", "Errore nella creazione del layer GlobeText: %s" % str(e))
        return None, None, None, None, None, None

    finally:
        # Pulizia
        if 'original_selection' in locals() and pdb.gimp_item_is_valid(original_selection):
            pdb.gimp_image_remove_channel(image, original_selection) # potrei anche commentarlo in caso se ho problemi con il riempimento
        if 'temp_mask' in locals() and pdb.gimp_item_is_valid(temp_mask):
            pdb.gimp_image_remove_channel(image, temp_mask)
        if 'optimized_selection' in locals() and pdb.gimp_item_is_valid(optimized_selection):
            pdb.gimp_image_remove_channel(image, optimized_selection)
        if 'optimized_selection_reduced' in locals() and pdb.gimp_item_is_valid(optimized_selection_reduced):
            pdb.gimp_image_remove_channel(image, optimized_selection_reduced)
        if 'new_layer' in locals() and pdb.gimp_item_is_valid(new_layer):
            pdb.gimp_image_remove_layer(image, new_layer)
        pdb.gimp_selection_none(image)
        # Rimuovi tutti i file temporanei, a meno che ENABLE_DEBUG non sia True
        if not ENABLE_DEBUG:
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        print("File temporaneo rimosso: %s" % temp_file)
                    except Exception as e:
                        print("Errore nella rimozione del file %s: %s" % (temp_file, str(e)))

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
            print("Immagine invertita salvata in:", temp_image_path)
        except Exception as e:
            print("Errore nell'inversione dei colori: %s" % str(e))
            tkMessageBox.showerror("Errore", "Errore nell'inversione dei colori: %s" % str(e))
            temp_image_path = image_path

    cmd = ["tesseract", temp_image_path, output_base, "--oem", "3", "--psm", psm, "-l", lang]
    try:
        print("Esecuzione Tesseract:", cmd)
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        print("Output Tesseract:", result)
        with open(output_base + ".txt", "r") as f:
            text = f.read().strip()
        print("Testo estratto:", text)
        os.remove(output_base + ".txt")
        if invert_colors and temp_image_path != image_path:
            os.remove(temp_image_path)
        return text
    except Exception as e:
        error_msg = "Tesseract fallito: %s" % str(e)
        print(error_msg)
        tkMessageBox.showerror("Errore", "%s. Prova a modificare la modalità PSM o abilita l'inversione dei colori." % error_msg)
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
        self.settings = load_settings()  # Carica le impostazioni dal file ini
        self.init_ui()

    def init_ui(self):
        tk.Label(self, text="Lingua di input (3 lettere):").pack()
        self.lang_input = tk.Entry(self)
        self.lang_input.insert(0, self.settings["lang_input"])
        self.lang_input.pack()

        tk.Label(self, text="Lingua di output (2 lettere):").pack()
        self.lang_output = tk.Entry(self)
        self.lang_output.insert(0, self.settings["lang_output"])
        self.lang_output.pack()

        tk.Label(self, text="Modalità PSM di Tesseract:").pack()
        self.psm_var = tk.StringVar(value=self.settings["psm_var"])
        self.psm_display = tk.StringVar(value=self.settings["psm_display"])
        tk.OptionMenu(self, self.psm_display, *[opt[1] for opt in psm_options],
                      command=self.update_psm_selection).pack()

        tk.Label(self, text="Pre-elaborazione del testo:").pack()
        self.preprocess_var = tk.StringVar(value=self.settings["preprocess_var"])
        tk.OptionMenu(self, self.preprocess_var, *[opt[1] for opt in preprocess_options],
                      command=self.update_preprocess_selection).pack()

        self.auto_color_var = tk.BooleanVar(value=self.settings["auto_color_var"])
        tk.Checkbutton(self, text="Rileva automaticamente il colore di sfondo",
                       variable=self.auto_color_var).pack()

        self.invert_colors_var = tk.BooleanVar(value=self.settings["invert_colors_var"])
        tk.Checkbutton(self, text="Inverti colori per Tesseract (testo chiaro su sfondo scuro)",
                       variable=self.invert_colors_var).pack()

        self.lowercase_translate_var = tk.BooleanVar(value=self.settings["lowercase_translate_var"])
        tk.Checkbutton(self, text="Traduci in minuscolo e poi converti in maiuscolo",
                       variable=self.lowercase_translate_var).pack()

        tk.Label(self, text="Traduttore:").pack()
        self.translator_var = tk.StringVar(value=self.settings["translator_var"])
        tk.Radiobutton(self, text="LibreTranslate", variable=self.translator_var, value="libre").pack()
        tk.Radiobutton(self, text="Google Translate (Al momento non funziona)", variable=self.translator_var, value="google").pack()

        self.auto_anchor_var = tk.BooleanVar(value=self.settings["auto_anchor_var"])
        tk.Checkbutton(self, text="Ancora automaticamente il testo", variable=self.auto_anchor_var).pack()

        self.process_button = tk.Button(self, text="Processa selezione", command=self.process_image)
        self.process_button.pack()

        tk.Label(self, text="Testo OCR:").pack()
        self.ocr_text_display = tk.Text(self, height=5, width=60)
        self.ocr_text_display.pack()

        self.retranslate_button = tk.Button(self, text="Ritraduci", command=self.retranslate_text)
        self.retranslate_button.pack()

        tk.Label(self, text="Testo tradotto:").pack()
        self.text_display = tk.Text(self, height=10, width=60)
        self.text_display.pack()

        self.save_button = tk.Button(self, text="Applica a GIMP", command=self.apply_to_gimp)
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
            tkMessageBox.showwarning("Avviso", "Nessun testo OCR da tradurre.")
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
        print("Testo ritradotto inserito nella GUI: %s" % translated_text)

    def process_image(self):
        log_file = None
        if ENABLE_DEBUG:
            try:
                log_file = open("/tmp/ComicBubbleOCR_log.txt", "a")
                sys.stdout = log_file
                print("--- Inizio log: %s ---" % time.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                tkMessageBox.showwarning("Avviso", "Impossibile aprire il file di log in /tmp: %s" % str(e))

        try:
            # Verifica la selezione
            if pdb.gimp_selection_is_empty(self.image):
                print("Errore: Nessuna selezione attiva in GIMP")
                tkMessageBox.showerror("Errore", "Nessuna selezione attiva. Usa la bacchetta magica o la selezione libera per selezionare la bolla.")
                self.destroy()
                return

            self.selection_bounds = get_selection_bounds(self.image)
            if not self.selection_bounds:
                print("Errore: Nessuna selezione valida")
                tkMessageBox.showerror("Errore", "Nessuna selezione valida")
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
                print("Errore: Impossibile esportare l'immagine selezionata")
                tkMessageBox.showerror("Errore", "Impossibile esportare l'immagine selezionata")
                self.destroy()
                return

            if not self.ocr_text or "Empty page" in self.ocr_text or len(self.ocr_text) <= 2:
                print("Errore: Nessun testo valido estratto da Tesseract")
                tkMessageBox.showwarning("Avviso", "Nessun testo valido estratto. Prova a modificare PSM (es. 7 o 11) o abilita/disabilita l'inversione dei colori. Controlla %s/ocr_image_attempt_*.png per debug." % tempfile.gettempdir())
                self.destroy()
                return

            self.ocr_text_display.delete(1.0, tk.END)
            self.ocr_text_display.insert(tk.END, self.ocr_text)

            # Traduci il testo
            translator = self.translator_var.get()
            lang_output = self.lang_output.get().strip().lower()
            self.translated_text = ""
            if self.ocr_text:
                text_to_translate = self.ocr_text
                if self.lowercase_translate_var.get():  # Controlla se l'opzione è selezionata
                    text_to_translate = text_to_translate.lower()  # Converte in minuscolo

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

                if self.lowercase_translate_var.get():  # Se l'opzione è selezionata, converte in maiuscolo
                    self.translated_text = self.translated_text.upper()
            else:
                print("Nessun testo OCR da tradurre")
                tkMessageBox.showwarning("Avviso", "Nessun testo OCR da tradurre")

            self.text_display.delete(1.0, tk.END)
            self.text_display.insert(tk.END, self.translated_text)
            tkMessageBox.showinfo("Info", "Elaborazione completata. Modifica il testo OCR o tradotto se necessario.")

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
            print("Errore in process_image: %s" % str(e))
            tkMessageBox.showerror("Errore", "Errore durante l'elaborazione: %s" % str(e))
            self.destroy()
        finally:
            if log_file:
                print("--- Fine log: %s ---" % time.strftime("%Y-%m-%d %H:%M:%S"))
                sys.stdout = sys.__stdout__
                log_file.close()

    def apply_to_gimp(self):
        if not self.selection_bounds:
            tkMessageBox.showerror("Errore", "Nessuna selezione valida.")
            print("Errore in apply_to_gimp: Nessuna selezione valida")
            self.destroy()
            return

        x1, y1, x2, y2 = self.selection_bounds
        text = self.text_display.get(1.0, tk.END).strip()
        if not text:
            tkMessageBox.showerror("Errore", "Nessun testo da applicare.")
            print("Errore in apply_to_gimp: Nessun testo fornito")
            self.destroy()
            return

        try:
            print("Ricerca layer GlobeText: %s" % self.unique_layer_name)
            layer_globe_text = pdb.gimp_image_get_layer_by_name(self.image, self.unique_layer_name)
            if not layer_globe_text:
                tkMessageBox.showerror("Errore", "Layer GlobeText non trovato: %s" % self.unique_layer_name)
                print("Errore in apply_to_gimp: Layer GlobeText non trovato: %s" % self.unique_layer_name)
                self.destroy()
                return

            # Calcola il rettangolo inscritto (riduci del 5% per i bordi con un minimo di 5 pixel)
            margin = 0.05  # 5% di margine
            fixed_margin = 5  # Margine fisso in pixel
            inscribed_x1 = x1 + max(fixed_margin, (x2 - x1) * margin)
            inscribed_y1 = y1 + max(fixed_margin, (y2 - y1) * margin)
            inscribed_x2 = x2 - max(fixed_margin, (x2 - x1) * margin)
            inscribed_y2 = y2 - max(fixed_margin, (y2 - y1) * margin)
            inscribed_width = inscribed_x2 - inscribed_x1
            inscribed_height = inscribed_y2 - inscribed_y1
            print("Rettangolo inscritto calcolato: x1=%d, y1=%d, x2=%d, y2=%d, larghezza=%d, altezza=%d" % 
                  (inscribed_x1, inscribed_y1, inscribed_x2, inscribed_y2, inscribed_width, inscribed_height))
            print("Testo da applicare: '%s'" % text)

            # Parametri del font
            font = "Sans"  # Font principale
            fallback_font = "Arial"  # Font di fallback
            min_font_size = 6
            max_font_size = 40  # Ridotto per convergere su valori realistici
            reference_font_size = 10  # Font size di riferimento per stime
            interlinea_factor = 1.3  # Valore fisso calibrato per Sans

            # Verifica disponibilità del font
            try:
                fonts = pdb.gimp_fonts_get_list(font)
                if not fonts or not any(font.lower() in f.lower() for f in fonts[1]):
                    print("Font '%s' non trovato, uso fallback '%s'" % (font, fallback_font))
                    font = fallback_font
            except Exception as e:
                print("Errore nella verifica del font: %s, uso fallback '%s'" % (str(e), fallback_font))
                font = fallback_font
            print("Font selezionato: %s" % font)

            # Funzione per ottenere le dimensioni del testo
            def get_text_extents(text, font_size):
                try:
                    width, height, _, _ = pdb.gimp_text_get_extents_fontname(text, font_size, PIXELS, font)
                    print("get_text_extents: testo='%s', font_size=%d, width=%d, height=%d" % (text, font_size, width, height))
                    return width, height
                except Exception as e:
                    print("Errore in get_text_extents per testo='%s', font_size=%d: %s" % (text, font_size, str(e)))
                    return 0, 0

            # Funzione per stimare l'altezza di una riga
            def get_line_height(font_size):
                try:
                    sample_text = "Sample Text"  # Testo rappresentativo
                    _, height = get_text_extents(sample_text, font_size)
                    if height == 0:
                        print("Altezza zero per testo di prova, uso fallback: %d * 1.3" % font_size)
                        return font_size * 1.3
                    estimated_height = height / 2  # Approssimazione per una riga
                    print("get_line_height: font_size=%d, estimated_height=%f" % (font_size, estimated_height))
                    return estimated_height
                except Exception as e:
                    print("Errore in get_line_height per font_size=%d: %s" % (font_size, str(e)))
                    return font_size * 1.3

            # Usa interlinea_factor fisso per evitare problemi
            print("Fattore interlinea per %s: %f" % (font, interlinea_factor))

            # Funzione per stimare il numero di righe necessarie
            def estimate_num_lines(text, font_size, box_width):
                words = text.split()
                current_line = ""
                num_lines = 1
                for word in words:
                    test_line = current_line + word + " " if current_line else word + " "
                    line_width, _ = get_text_extents(test_line, font_size)
                    print("estimate_num_lines: test_line='%s', line_width=%d, box_width=%d" % 
                          (test_line, line_width, box_width * 0.75))
                    if line_width > box_width * 0.75:  # Margine di sicurezza del 25%
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
                        print("Aggiunta riga finale per '%s', num_lines=%d" % (current_line, num_lines))
                return max(1, num_lines)

            # Crea un layer di testo con un box fisso
            try:
                text_layer = pdb.gimp_text_layer_new(self.image, text, font, reference_font_size, PIXELS)
                if not text_layer:
                    raise Exception("Impossibile creare il layer di testo")
                pdb.gimp_image_insert_layer(self.image, text_layer, None, 0)
                text_layer.name = "Text_" + self.unique_layer_name.split("_")[1]
                print("Layer di testo creato: %s con font_size=%d" % (text_layer.name, reference_font_size))
            except Exception as e:
                print("Errore nella creazione del layer di testo: %s" % str(e))
                tkMessageBox.showerror("Errore", "Errore nella creazione del layer di testo: %s" % str(e))
                self.destroy()
                return

            # Imposta il box di testo
            try:
                pdb.gimp_text_layer_set_text(text_layer, text)
                pdb.gimp_text_layer_resize(text_layer, inscribed_width, inscribed_height)
                pdb.gimp_layer_set_offsets(text_layer, inscribed_x1, inscribed_y1)
                pdb.gimp_text_layer_set_justification(text_layer, TEXT_JUSTIFY_CENTER)
                pdb.gimp_text_layer_set_color(text_layer, gimpcolor.RGB(*[c / 255.0 for c in self.text_color]))
                print("Box di testo impostato: larghezza=%d, altezza=%d, posizione: x=%d, y=%d" % 
                      (inscribed_width, inscribed_height, inscribed_x1, inscribed_y1))
            except Exception as e:
                print("Errore nell'impostazione del box di testo: %s" % str(e))
                tkMessageBox.showerror("Errore", "Errore nell'impostazione del box di testo: %s" % str(e))
                self.destroy()
                return

            # Funzione per verificare se il testo si adatta al box
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
                        print("Nessuna selezione per font_size=%d" % font_size)
                        return False, 0
                    content_height = bounds[4] - bounds[2]
                    is_truncated = content_height >= inscribed_height * 0.90
                    fits = content_height <= inscribed_height * fill_factor and not is_truncated
                    print("text_fits_in_box: font_size=%d, content_height=%d, inscribed_height=%d, fill_factor=%f, is_truncated=%s, fits=%s" % 
                          (font_size, content_height, inscribed_height, fill_factor, is_truncated, fits))
                    return fits, content_height
                except Exception as e:
                    print("Errore in text_fits_in_box per font_size=%d: %s" % (font_size, str(e)))
                    return False, 0

            # Determina la percentuale di riempimento
            num_lines = estimate_num_lines(text, reference_font_size, inscribed_width)
            print("Numero di righe stimato: %d" % num_lines)
            if num_lines <= 2:
                fill_factor = 0.70  # Ridotto da 0.80
            elif num_lines <= 4:
                fill_factor = 0.68  # Ridotto da 0.78
            else:
                fill_factor = 0.66  # Ridotto da 0.76
            print("Percentuale di riempimento: %f" % fill_factor)

            # Calcola la stima iniziale della dimensione del font
            estimated_font_size = int((inscribed_height * fill_factor) / (num_lines * interlinea_factor))
            estimated_font_size = max(min_font_size, min(max_font_size, estimated_font_size))
            print("Dimensione font stimata iniziale: %d" % estimated_font_size)

            # Ricerca binaria per affinare la dimensione del font
            low = max(min_font_size, estimated_font_size - 5)
            high = min(max_font_size, estimated_font_size + 5)
            best_font_size = min_font_size
            best_height = 0

            while low <= high:
                mid = (low + high) // 2
                fits, content_height = text_fits_in_box(text_layer, mid)
                print("Ricerca binaria: font_size=%d, fits=%s, content_height=%d, low=%d, high=%d" % 
                      (mid, fits, content_height, low, high))
                if fits and content_height > 0:
                    best_font_size = mid
                    best_height = content_height
                    low = mid + 1
                else:
                    high = mid - 1

            # Imposta la dimensione del font ottimale
            try:
                pdb.gimp_text_layer_set_font_size(text_layer, best_font_size, PIXELS)
                fits, final_height = text_fits_in_box(text_layer, best_font_size)
                print("Dimensione font finale: %d, altezza finale=%d, fits=%s" % (best_font_size, final_height, fits))
            except Exception as e:
                print("Errore nell'impostazione della dimensione del font: %s" % str(e))
                tkMessageBox.showerror("Errore", "Errore nell'impostazione della dimensione del font: %s" % str(e))
                self.destroy()
                return

            # Avviso se il testo è troppo alto o il font è troppo piccolo
            if final_height > inscribed_height or best_font_size == min_font_size:
                print("Avviso: Il testo potrebbe essere troppo lungo per il box o il font size è minimo")
                tkMessageBox.showwarning("Avviso", "Il testo potrebbe non adattarsi correttamente. "
                                                  "Considera di ridurre il testo o il font size è troppo piccolo.")

            # Inserisci il layer di testo nel gruppo
            try:
                layer_group = pdb.gimp_item_get_parent(layer_globe_text)
                if layer_group and pdb.gimp_item_is_valid(layer_group):
                    position = pdb.gimp_image_get_item_position(self.image, layer_globe_text)
                    pdb.gimp_image_reorder_item(self.image, text_layer, layer_group, position)
                    print("Layer di testo inserito nel gruppo: %s" % layer_group.name)
                else:
                    position = pdb.gimp_image_get_item_position(self.image, layer_globe_text)
                    pdb.gimp_image_reorder_item(self.image, text_layer, None, position)
                    print("Layer di testo inserito senza gruppo, posizione: %d" % position)
            except Exception as e:
                print("Errore nell'inserimento del layer di testo: %s" % str(e))
                tkMessageBox.showerror("Errore", "Errore nell'inserimento del layer di testo: %s" % str(e))
                self.destroy()
                return

            # Ancoraggio automatico
            if self.auto_anchor_var.get():
                print("Ancoraggio del layer di testo...")
                try:
                    pdb.gimp_image_set_active_layer(self.image, layer_globe_text)
                    merged_layer = pdb.gimp_image_merge_down(self.image, text_layer, EXPAND_AS_NECESSARY)
                    merged_layer.name = self.unique_layer_name
                    print("Layer di testo unito: %s" % merged_layer.name)
                except Exception as e:
                    print("Errore durante l'ancoraggio: %s" % str(e))
                    tkMessageBox.showerror("Errore", "Errore durante l'ancoraggio del testo: %s" % str(e))
                    self.destroy()
                    return
            else:
                print("Layer di testo lasciato editabile.")

            gimp.displays_flush()
            print("Testo applicato con successo")
        except Exception as e:
            print("Errore in apply_to_gimp: %s" % str(e))
            tkMessageBox.showerror("Errore", "Errore nell'applicazione del testo: %s" % str(e))
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
        tkMessageBox.showerror("Error", "Effettua una selezione prima di eseguire il plug-in.")

register(
    "python_fu_comic_bubble_ocr",
    "ComicBubbleOCR",
    "OCR e traduzione per fumetti",
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
