from PIL import Image, ImageDraw
import webbrowser
import time
import re
import json

im = Image.open("M:\\basement-2.png")

#im.save("M:\\GitHub\\find_your_meeting\Ground Floor_test.png")

floor = input("Floor: ")

location = {}

width, height = im.size

found_pixels = []
found_color = []
for i, pixel in enumerate(im.getdata()):
    #print(pixel)
    if pixel not in found_color:
        found_color.append(pixel)
    if pixel == (128):
        found_pixels.append(i)

print(found_color)

found_pixels_coords = [divmod(index, width) for index in found_pixels]

i=0

for y,x in found_pixels_coords:
    i+=1
    print(x,y)

    draw = ImageDraw.Draw(im)

    draw.ellipse([x-7, y-7, x+7, y+7], fill="#ff0000")
    draw.text((x-2, y-5), str(i), fill="#000000")
    location[i] = (x, y)

im.show()

new_location = {}

for n in location:
    formatting = False
    while formatting == False:
        room = input("Room {0}: ".format(n)).upper()
        formatting = (re.fullmatch("H\d\.(\d\d|\d\d\w)", room) is not None)
        if formatting == False:
            print("Try Again")

    new_location[room] = location[n]


print(new_location)

with open("{0}.json".format(floor), "w") as f:
        json.dump(new_location, f)