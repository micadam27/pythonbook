from PIL import Image
import os
import argparse
from ebooklib import epub
from natsort import natsorted 
from google.cloud import vision
from google.cloud.vision_v1 import types
import io

client = vision.ImageAnnotatorClient.from_service_account_json("/home/madam/bookgeneration-7b7f6b9fe703.json")

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", type=str, required=True)
parser.add_argument("-n", "--name", type=str, required=True)
parser.add_argument("-a", "--author", type=str, required=True)
args = parser.parse_args()

outputfile = args.path + '/' + args.name + '.epub'
coverpath = args.path + '/cover.jpg'
#initialize the text variable
text = ''
# Initialize the ebook object
book = epub.EpubBook()

# Set the metadata of the ebook
book.set_title(args.name)
book.set_language("en")
book.add_author(args.author)

# Create a list of sections
toc_items = []

# Loop through each subfolder in the main folder
for chapter_folder in natsorted(os.listdir(args.path)):
    chapter_path = os.path.join(args.path, chapter_folder)
    if not os.path.isdir(chapter_path):
        continue

    # Create a new chapter in the ebook
    chapter = epub.EpubHtml(title=chapter_folder, file_name=chapter_folder+'.xhtml', lang='en')
    text = ''

    # Loop through each PNG file in the subfolder
    for image_file in os.listdir(chapter_path):
        if not image_file.endswith(".png"):
            continue

        # Extract text from the image using pytesseract
        image_path = os.path.join(chapter_path, image_file)
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        image = types.Image(content=content)
        response = client.text_detection(image=image)
        text_annotations = response.text_annotations
        text += text_annotations[0].description
    # Split the text into lines
    lines = text.split('\n')

    # Loop through the lines and remove any line that has only one character
    new_lines = []
    for line in lines:
        if len(line.strip()) > 1:
            new_lines.append(line)
        else:
            if(len(new_lines) > 0 ):
                if (new_lines[0].lower()).startswith("chapter"):
                    if len(new_lines) > 1:
                        new_lines[1] ='\n' + line + new_lines[1]
                    else:
                        new_lines.append(line)  
                else:
                    if len(new_lines) > 1:
                        new_lines[0] = '\n' + line + new_lines[0]
                    else:
                        new_lines.append(line)
            else:
                new_lines.append(line)

    if (new_lines[0].lower()).startswith("chapter"):
        if len(new_lines[1].strip()) < 3:
            new_lines[2] = '\n' + new_lines[1] + new_lines[2]
            new_lines.pop(1)
        new_lines[0] += "\n"
    else:
        if len(new_lines[0].strip()) < 3:
            if (new_lines[1].lower()).startswith("chapter"):
                new_lines[2] = '\n' + new_lines[0] + new_lines[2]
                new_lines.pop(0)
            else:
                new_lines[1] = '\n' + new_lines[0] + new_lines[1]
                new_lines.pop(0)
    

    # Combine the lines into a single string
    new_text = '\n'.join(new_lines)
    new_text = new_text.replace("\n", "<br>")
    chapter.content = "<p>" + new_text + "</p>"

    book.add_item(chapter)
    toc_item = epub.Link(chapter_folder+'.xhtml', chapter_folder, chapter_folder+'.xhtml')
    toc_items.append(toc_item)
    book.toc += [toc_item]
    print(chapter_folder + " finished")

  
# Set the table of contents
toc = epub.EpubNav()
toc.toc = tuple(toc_items)
book.add_item(toc)

#Add blank cover
coverimage_content = open(coverpath, 'rb').read()
coverimage = epub.EpubImage()
coverimage.file_name = 'cover.jpg'
coverimage.media_type = 'image/jpeg'
coverimage.content = coverimage_content
book.add_item(coverimage)
coverhtml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
 <head>
  <style>
    body {{margin: 0em; padding: 0em; }}
    img {{ max-width: 100%; max-height: 100%; }}
  </style>
 </head>
 <body>
   <img src="cover.jpg" alt="cover.jpg" />
 </body>
</html>'''
book.add_item(epub.EpubItem(uid="cover", file_name="cover.xhtml", content=coverhtml))


# Set the order of the items in the ebook
book.spine = ['cover', 'nav'] + [str(item) for item in book.toc] + [item for item in book.items if item not in book.toc]
book.spine.pop()
book.spine.pop()
book.spine.pop()

# Save the ebook to a file
epub.write_epub(outputfile, book, {})
print(outputfile)


