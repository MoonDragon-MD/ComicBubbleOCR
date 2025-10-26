Plugin to translate comics via OCR and LibreTranslate (full offline) for GIMP 2.10.* (python 2.7)

System to compute background and text color, auto centering and auto reduce/enlarge text on bubble.

Various options and auto retries if text is not detected, since version 1.2, it has been possible to set custom fonts and font colors.

I took a cue from the windows project: [BubbleOCR](https://github.com/snakeotakon/BubbleOCR)


### Dependencies

Instructions for Debiane derivatives such as Ubuntu

```
wget https://old-releases.ubuntu.com/ubuntu/pool/universe/p/pygtk/python-gtk2_2.24.0-6_amd64.deb
wget https://old-releases.ubuntu.com/ubuntu/pool/universe/g/gimp/gimp-python_2.10.8-2_amd64.deb
sudo dpkg -i python-gtk2_2.24.0-6_amd64.deb
sudo dpkg -i gimp-python_2.10.8-2_amd64.deb
```
```
sudo apt-get install python-tk tesseract-ocr-eng [tesseract-ocr-*] 
```
(*= language es jpn)
```
sudo apt install -f  (Fix any dependency issues)
```
Install pip on python 2.7:
```
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
python2.7 get-pip.py
python2.7 -m pip install requests Pillow 
```
- LibreTranslate (Argos) set to localhost:5000 [LibreTranslate on Docker](https://hub.docker.com/r/libretranslate/libretranslate)

I also set google translation but since the library is old it will not work,

I left the option for a future (for new GIMP versions with python3 the library works)
(googletrans==2.4.0 last supported version on python 2.7 is deprecated)

### Installation

Put ComicBubbleOCR.py in the folder:
```
 ~/.config/GIMP/2.10/plug-ins/
 ```
Give the file execution permissions
```
chmod +x ~/.config/GIMP/2.10/plug-ins/ComicBubbleOCR.py
```

### Usage

Open the image with GIMP,

Select by the method you want the bubble to be translated

then in the menu bar click on "Filters" > "ComicBubbleOCR..."

1) Set the language of the text to be translated (otherwise in automatic it is English for OCR and auto for translator)

2) You will find various options, for better translation I recommend you to enable in text pre-processing “Merge all line breaks with a space” then if you have text in uppercase set to translate to lowercase (it will be then converted back to uppercase anyway), this helps a lot libreTraslate to give you a good translation

3) Click the “Process Selection” button.

4a) If the OCR text is misspelled correct it and click Re-translate

4b) If you don't like the translation edit it, you can break the sentences with enter so that you have more lines like the original (if you had set “Merge all line breaks with a space”)

5) Click the “Apply to GIMP” button.

NB: The OCR PSM modes are used to further optimize the determination of the text, the default is almost always fine, also if it doesn't find the text I have set up automatic systems that try various PSMs until it finds the text, if it still doesn't find it, again in automatic, try decreasing the scanning portion so that it gets closer to the text if you have a large bubble and small scribed text in the middle.

NB-1: The “Invert colors” option is needed if you have light text on a dark background, it helps OCR determine the text better.

NB-2: The option “Automatically anchor text” is to make the text layer a non-editable image right away

### Screenshots

ENG

![alt text](https://github.com/MoonDragon-MD/ComicBubbleOCR/blob/main/img/1.jpg?raw=true)

result

![alt text](https://github.com/MoonDragon-MD/ComicBubbleOCR/blob/main/img/2.jpg?raw=true)

ITA

![alt text](https://github.com/MoonDragon-MD/ComicBubbleOCR/blob/main/img/3.jpg?raw=true)

ITA V.1.2

![alt text](https://github.com/MoonDragon-MD/ComicBubbleOCR/blob/main/img/4.jpg?raw=true)

ENG V.1.2

![alt text](https://github.com/MoonDragon-MD/ComicBubbleOCR/blob/main/img/5.jpg?raw=true)

The comic strip featuring a witch and a cat is David Revoy's fantastic open-source work [“Pepper & Carrot.”](https://www.peppercarrot.com/)

### Info

Remember to always start selecting from the image layer (original imported image) if you want to translate more than one bubble on the same image, otherwise it will obviously find nothing.

I hope you like it, I understand that many would like the version for the new GIMPs with python3, maybe in the future I will think about it.
