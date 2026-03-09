from PIL import Image
import io

# width and height are 320x200 for standard apf files
w = 320
h = 200
headertext = "APERTURE IMAGE FORMAT (c) 1985" # header may change for alternate variations with different resolutions

def decodeapf(apf: str):
    apf_list = apf.splitlines()
    apf_lines = []
    for line in apf_list:
        if line:
            apf_lines.append(line)
    if not apf_lines[0].strip() == headertext:
        raise Exception("Invalid Aperture Image Format File")
    lineskip = int(apf_lines[1].strip())
    data = apf_lines[2]
    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    state = False # swapping this will invert the image, hehe
    x = 0
    y = h-1
    passoffset = 0

    for char in data:
        runlen = ord(char) - 32
        for i in range(runlen):
            apfbuffer[y][x] = (state)
            x += 1
            if not x < w:
                y = y - lineskip
                x = 0
            if y < 0:
                y = h-1
                passoffset +=1
                y -= passoffset

        state = not state

    img = Image.new("RGB", (w, h))
    pixels = img.load()

    for y in range(h):
        row = apfbuffer[y]

        for x in range(w):
            if row[x]:
                pixels[x, y] = (255, 255, 255)
            else:
                pixels[x, y] = (0, 0, 0)

    imageData = io.BytesIO()
    img.save(imageData, format='PNG')
    imageData = imageData.getvalue()
    return imageData

def reduce_to_apf_quality(img: Image):
    size = (w, h) # size for apf encoder
    img = img.resize(size)
    img = img.convert("1")
    return img

def generate_runs(bitmap: list, lineskip: int):
    runcounter = 0
    currentrun = False  # swapping this will invert the image as well
    runlens = []
    curline = h-1
    revmap = []
    passoffset = 0
    for i in range(h):
        revmap.append(bitmap[curline])
        curline -= lineskip
        if curline < 0:
            curline = h-1
            passoffset +=1
            curline -= passoffset

    for vline in revmap:
        for pixel in vline:
            if currentrun == pixel:
                if runcounter+1 > 94:
                    runlens.append(runcounter)
                    runlens.append(0)
                    runcounter = 0
                runcounter += 1
            else:
                runlens.append(runcounter)
                runcounter = 1
                currentrun = pixel
    if runcounter > 0:
        runlens.append(runcounter)
    return runlens

def encodeapf(img: bytes, lineskip: int = 1, findbestlineskip: bool = False):
    img = Image.open(io.BytesIO(img))
    img = reduce_to_apf_quality(img)
    imageData = io.StringIO()
    apflist = [headertext]
    if not findbestlineskip:
        apflist.append(str(lineskip))
    pixels = img.load()

    bitmap = [[pixels[x, y] != 0 for x in range(w)] for y in range(h)]

    output = ""
    if findbestlineskip:
        lens = {}
        shortestId = None
        shortestlen = 999999999
        for i in range(1, h-1):
            lens[str(i)] = None
        for ls in lens:
            lens[ls] = generate_runs(bitmap, int(ls))
        for ls in lens:
            totallen = len(lens[ls])+len(str(ls))
            if totallen < shortestlen:
                shortestlen = totallen
                shortestId = ls
        runlens = lens[shortestId]
        apflist.append(shortestId)
    else:
        runlens = generate_runs(bitmap, lineskip)

    for num in runlens:
        output += chr(num+32)
    apflist.append(output)
    apftext = "\n".join(apflist)
    return apftext

# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'input.apf'
#with open(file_path, 'r') as f:
#    file_content = f.read()
#decodedapf = decodeapf(file_content)
#with open("output.png", "wb") as f:
#    f.write(decodedapf)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
#file_path = 'output.png'
#with open(file_path, "rb") as f:
#    data = io.BytesIO()
#    data = f.read()

#encodedapf = encodeapf(data, 3, True)
#with open("output.apf", "w") as f:
#    f.write(encodedapf)

