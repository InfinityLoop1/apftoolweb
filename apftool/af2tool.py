from PIL import Image, ImageSequence
import io, textwrap

# width and height are 320x200 for standard apf files
af2headertext = "APERTURE IMAGE FORMAT (c) 1993" # af2 header

def af2_apfdecodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: list):
    x = 0
    y = h-1
    passoffset = 0
    state = False # swapping this will invert the image.

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
                pixels[x, y] = pals[1]
            else:
                pixels[x, y] = pals[0]
    return img

def af2decodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: str):
    x = 0
    y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    palsegments = textwrap.wrap(pals, 7)
    pal = {}
    for col in palsegments:
        ind = col[0]
        hexcs = col[1:]
        hexcsegment = textwrap.wrap(hexcs, 2)
        pal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

    for pair in range(len(data)//2):
        color = data[pair*2]
        runlen = ord(data[pair*2+1]) - 32

        for i in range(runlen):
            apfbuffer[y][x] = pal[color]

            x += 1
            if x >= w:
                y -= lineskip
                x = 0

            if y < 0:
                y = h-1
                passoffset += 1
                y -= passoffset

    img = Image.new("RGB", (w, h))
    pixels = img.load()

    for y in range(h):
        row = apfbuffer[y]

        for x in range(w):
            pixels[x, y] = row[x]

    return img

def decodeaf2(af2: str, format: str = 'PNG'):
    apf_list = af2.splitlines()
    apf_lines = []
    for line in apf_list:
        if line:
            apf_lines.append(line)
    if apf_lines[0].strip() == "APERTURE IMAGE FORMAT (c) 1985":
        af2 = f"APERTURE IMAGE FORMAT (c) 1993\n320x200,l,{apf_list[1]}\n.\n{apf_list[2]}"
        apf_lines = af2.splitlines()

    if not apf_lines[0].strip() == af2headertext:
        raise Exception("Invalid Aperture Image Format File")
    metadata = apf_lines[1].strip().split(",")
    res = metadata[0]
    res = res.split("x")
    w = int(res[0])
    h = int(res[1])
    arguments = metadata[1]
    lineskip = int(metadata[2])
    if "l" in arguments:
        mode = "legacy"
    else:
        mode = "apf2"
    if "m" in arguments:
        datatype = "multistream"
        data = apf_lines[3:]
    else:
        datatype = "singlestream"
        data = apf_lines[3]

    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    imgs = []
    if datatype == "multistream":
        if mode == "legacy":
            pals = apf_lines[2].split(".")
            if pals[0] == "":
                pals[0] = (0,0,0)
            else:
                hexcsegment = textwrap.wrap(pals[0], 2)
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))
            if pals[1] == "":
                pals[1] = (255,255,255)
            else:
                hexcsegment = textwrap.wrap(pals[1], 2)
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

            for ds in data:
                imgs.append(af2_apfdecodedata(ds, h, w, apfbuffer, lineskip, pals))
        else:
            pals = apf_lines[2]
            for ds in data:
                imgs.append(af2decodedata(ds, h, w, apfbuffer, lineskip, pals))
        imageData = io.BytesIO()
        imgs[0].save(
            imageData,
            format="GIF",
            save_all=True,
            append_images=imgs[1:],
            loop=0,
            duration=100
        )
        imageData = imageData.getvalue()
    else:
        if mode == "legacy":
            pals = apf_lines[2].split(".")
            if pals[0] == "":
                pals[0] = (0,0,0)
            else:
                hexcsegment = textwrap.wrap(pals[0], 2)
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))
            if pals[1] == "":
                pals[1] = (255,255,255)
            else:
                hexcsegment = textwrap.wrap(pals[1], 2)
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

            img = af2_apfdecodedata(data, h, w, apfbuffer, lineskip, pals)
        else:
            pals = apf_lines[2]
            img = af2decodedata(data, h, w, apfbuffer, lineskip, pals)
        imageData = io.BytesIO()
        img.save(imageData, format=format)
        imageData = imageData.getvalue()

    return imageData

def reduce_to_af2_quality(img: Image, num_colors: int = 95):
    img = img.convert("P", palette=Image.ADAPTIVE, colors=num_colors, dither=Image.NONE) # disable dithering to reduce file sizes
    
    # get the palette as tuples
    raw_palette = img.getpalette()[:num_colors*3]
    palette = [tuple(raw_palette[i:i+3]) for i in range(0, len(raw_palette), 3)]
    
    return img, palette

def reduce_to_apf_in_af2_quality(img: Image):
    img = img.convert("1")
    return img

def generate_runs_af2_l(bitmap: list, lineskip: int, w: int, h: int):
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

def generate_runs_af2(bitmap: list, palette: list, lineskip: int, w: int, h: int):
    colpal = {}
    colpalbnr = {}
    for i in range(0,len(palette)):
        colpal[chr(i+32)] = palette[i]
    for key in colpal:
        colpalbnr[colpal[key]] = key

    af2pal_array = []
    af2pal = ""
    for col in colpal:
        r, g, b = colpal[col]
        liberal = (f"{r:02X}", f"{g:02X}", f"{b:02X}")
        af2pal_array.append(f"{col}{''.join(liberal)}")
    af2pal = ''.join(af2pal_array)
    runcounter = 0
    currentrun = None
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
                    if currentrun is not None:
                        runlens.append([colpalbnr[currentrun], runcounter])
                    currentrun = pixel
                    runcounter = 0
                runcounter += 1
            else:
                if currentrun is not None:
                    runlens.append([colpalbnr[currentrun], runcounter])
                runcounter = 1
                currentrun = pixel
    if runcounter > 0:
        runlens.append([colpalbnr[currentrun], runcounter])

    rldb = []
    for rl in runlens:
        rldb.append(rl[1])
    total = sum(rldb)
    return runlens, af2pal

def encodeaf2(img: bytes, lineskip: int = 1, findbestlineskip: bool = False, legacy: bool = False):
    img = Image.open(io.BytesIO(img))
    if legacy:
        img = reduce_to_apf_in_af2_quality(img)
    else:
        img, palette = reduce_to_af2_quality(img)
    imageData = io.StringIO()
    apflist = [af2headertext]
    metadata = []
    pixels = img.load()
    res = img.size
    metadata.append(f"{res[0]}x{res[1]}")
    w = res[0]
    h = res[1]

    args = ""
    if legacy:
        args+="l"

    metadata.append(args)
    if not findbestlineskip:
        metadata.append(str(lineskip))
        metadata = ",".join(metadata)
        apflist.append(metadata)
    if legacy and not findbestlineskip:
        apflist.append(".")
    if legacy:
        bitmap = [[pixels[x, y] != 0 for x in range(w)] for y in range(h)]
    else:
        img_rgb = img.convert("RGB")
        pixels = img_rgb.load()
        bitmap = [[pixels[x, y] for x in range(img.width)] for y in range(img.height)]
        img_rgb = None # take out the trash
        pixels = None

    output = ""
    if findbestlineskip:
        lens = {}
        shortestId = None
        shortestlen = 999999999
        maxrange = lineskip
        if h-1 < lineskip:
            maxrange = h-1
        for i in range(1, maxrange):
            lens[str(i)] = None
        for ls in lens:
            if legacy:
                lens[ls] = generate_runs_af2_l(bitmap, int(ls), w, h)
            else:
                lens[ls], af2pal = generate_runs_af2(bitmap, palette, int(ls), w, h)
        for ls in lens:
            totallen = len(lens[ls])+len(str(ls))
            if totallen < shortestlen:
                shortestlen = totallen
                shortestId = ls
        runlens = lens[shortestId]
        metadata.append(str(shortestId))
        metadata = ",".join(metadata)
        apflist.append(metadata)
        if legacy:
            af2pal = "."
            for num in runlens:
                output += chr(num+32)
        else:
            for num in runlens:
                output += num[0]+chr(num[1]+32)
        apflist.append(af2pal)
    else:
        if legacy:
            runlens = generate_runs_af2_l(bitmap, lineskip, w, h)
            for num in runlens:
                output += chr(num+32)
        else:
            runlens, af2pal = generate_runs_af2(bitmap, palette, lineskip, w, h)
            apflist.append(af2pal)
            for num in runlens:
                output += num[0]+chr(num[1]+32)

    apflist.append(output)
    apftext = "\n".join(apflist)
    return apftext

# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'randombullshitgo.af2'
#with open(file_path, 'r') as f:
#    file_content = f.read()
#decodedapf = decodeaf2(file_content, 'GIF')
#with open("output.gif", "wb") as f:
#    f.write(decodedapf)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
file_path = 'alarm.png'
with open(file_path, "rb") as f:
    data = io.BytesIO()
    data = f.read()

encodedapf = encodeaf2(data, 20, True, False)
with open("alrmbls.af2", "w") as f:
    f.write(encodedapf)

file_path = 'alrmbls.af2'
with open(file_path, 'r') as f:
    file_content = f.read()
decodedapf = decodeaf2(file_content)
with open("alrmbls.png", "wb") as f:
    f.write(decodedapf)
