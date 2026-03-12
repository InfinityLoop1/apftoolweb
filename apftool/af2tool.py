from PIL import Image, ImageSequence
import io, textwrap

# width and height are 320x200 for standard apf files
af2headertext = "APERTURE IMAGE FORMAT (c) 1993" # af2 header

def af2_apfdecodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: list, trans: bool = False):
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

    colmode = "RGB"
    if trans:
        colmode+="A"
    img = Image.new(colmode, (w, h))
    pixels = img.load()

    for y in range(h):
        row = apfbuffer[y]

        for x in range(w):
            if row[x]:
                pixels[x, y] = pals[1]
            else:
                pixels[x, y] = pals[0]
    return img

def af2decodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: str, trans: bool = False):
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
    if trans:
        pal[" "] = (0, 0, 0, 0)

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

    colmode = "RGB"
    if trans:
        colmode+="A"
    img = Image.new(colmode, (w, h))
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
    istrans = ("t" in arguments)

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
                if istrans:
                    pals[0] = (0,0,0,0)
                else:
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
                imgs.append(af2_apfdecodedata(ds, h, w, apfbuffer, lineskip, pals, istrans))
        else:
            pals = apf_lines[2]
            for ds in data:
                imgs.append(af2decodedata(ds, h, w, apfbuffer, lineskip, pals, istrans))
        imageData = io.BytesIO()
        imgs[0].save(
            imageData,
            format="GIF",
            save_all=True,
            append_images=imgs[1:],
            loop=0,
            duration=100,
            disposal=2
        )
        imageData = imageData.getvalue()
    else:
        if mode == "legacy":
            pals = apf_lines[2].split(".")
            if pals[0] == "":
                if istrans:
                    pals[0] = (0,0,0,0)
                else:
                    pals[0] = (0,0,0)
            else:
                hexcsegment = textwrap.wrap(pals[0], 2)
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))
            if pals[1] == "":
                pals[1] = (255,255,255)
            else:
                hexcsegment = textwrap.wrap(pals[1], 2)
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

            img = af2_apfdecodedata(data, h, w, apfbuffer, lineskip, pals, istrans)
        else:
            pals = apf_lines[2]
            img = af2decodedata(data, h, w, apfbuffer, lineskip, pals, istrans)
        imageData = io.BytesIO()
        img.save(imageData, format=format)
        imageData = imageData.getvalue()

    return imageData

def reduce_to_af2_quality(img: Image, num_colors: int = 95, animated: bool = False, trans: bool = False):
    if animated:
        ifuckinghatequantize = (253, 0, 254)

        frames = []
        if trans:
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert("RGBA")
                background = Image.new("RGBA", frame.size, ifuckinghatequantize + (255,))
                composited = Image.alpha_composite(background, frame)
                frames.append(composited.convert("RGB"))
        else:
            frames = [frame.copy().convert("RGB") for frame in ImageSequence.Iterator(img)]

        widths, heights = zip(*(f.size for f in frames))
        total_width = max(widths)
        total_height = sum(heights)
        combined = Image.new("RGB", (total_width, total_height))
        y_offset = 0

        for frame in frames:
            combined.paste(frame, (0, y_offset))
            y_offset += frame.height

        if trans:
            combined_p = combined.convert("P", palette=Image.ADAPTIVE, colors=num_colors-1, dither=Image.NONE)

            pal = combined_p.getpalette()
            pal = [253, 0, 254] + pal
            combined_p.putpalette(pal)
        else:
            combined_p = combined.convert("P", palette=Image.ADAPTIVE, colors=num_colors-1, dither=Image.NONE)
        
        frames_p = []
        for frame in frames:
            f_p = frame.quantize(palette=combined_p, dither=Image.NONE)
            if trans:
                f_p.info["transparency"] = 0
            frames_p.append(f_p)

        raw_palette = combined_p.getpalette()[:num_colors*3]
        seen = set()
        palette = [tuple(raw_palette[i:i+3]) for i in range(0, len(raw_palette), 3) if not (tuple(raw_palette[i:i+3]) in seen or seen.add(tuple(raw_palette[i:i+3])))]
        
        return frames_p, palette
    else:
        img = img.convert("P", palette=Image.ADAPTIVE, colors=num_colors, dither=Image.NONE) # disable dithering to reduce file sizes
    
        # get the palette as tuples
        raw_palette = img.getpalette()[:num_colors*3]
        seen = set()
        palette = [c for c in (tuple(raw_palette[i:i+3]) for i in range(0, len(raw_palette), 3)) if not (c in seen or seen.add(c))]

        return img, palette

def reduce_to_apf_in_af2_quality(img: Image, animated: bool = False):
    if animated:
        frames = []

        for frame in ImageSequence.Iterator(img):
            bw = frame.convert("1")  # 1-bit black/white
            frames.append(bw)

        return frames
    else:
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

def generate_runs_af2(bitmap: list, palette: list, lineskip: int, w: int, h: int, trans: bool = False):
    colpal = {}
    colpalbnr = {}
    reservespace = False
    if not len(palette) == 95:
        reservespace = True

    for i in range(0,len(palette)):
        colpal[chr(i+32+int(reservespace))] = palette[i]
    if trans:
        for key in colpal:
            kreisi = list(colpal[key])
            kreisi.append(255)
            kreisi = tuple(kreisi)
            colpalbnr[kreisi] = key
        colpalbnr[(0, 0, 0, 0)] = " "
        colpalbnr[(253, 0, 254, 0)] = " "
    else:
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

def encodeaf2(img: bytes, lineskip: int = 1, findbestlineskip: bool = False, legacy: bool = False, trans: bool = False, pal: int = 95):
    if pal > 95:
        pal = 95
    if trans and (pal == 95):
        pal = 94

    img = Image.open(io.BytesIO(img))
    animated = getattr(img, "is_animated", False)
    if legacy:
        img = reduce_to_apf_in_af2_quality(img, animated)
    else:
        img, palette = reduce_to_af2_quality(img, pal, animated, trans)

    imageData = io.StringIO()
    apflist = [af2headertext]
    metadata = []
    frames = []
    if animated:
        for image in img:
            if legacy:
                frames.append(image.load())
            else:
                frames.append(image)
        #pixels = frames[0]
        res = img[0].size
    else:
        pixels = img.load()
        res = img.size
    metadata.append(f"{res[0]}x{res[1]}")
    w = res[0]
    h = res[1]

    args = ""
    if legacy:
        args+="l"
    if trans:
        args+="t"
    if animated:
        args+="m"

    metadata.append(args)
    if not findbestlineskip:
        metadata.append(str(lineskip))
        metadata = ",".join(metadata)
        apflist.append(metadata)
    if legacy and not findbestlineskip:
        apflist.append(".")
    if legacy:
        if animated:
            bitmaps = []
            for pixels in frames:
                bitmaps.append([[pixels[x, y] != 0 for x in range(w)] for y in range(h)])
        else:
            bitmap = [[pixels[x, y] != 0 for x in range(w)] for y in range(h)]
    else:
        colmode = "RGB"
        if trans:
            colmode+="A"
        if animated:
            bitmaps = []
            for img in frames:
                if trans:
                    img = img.convert("RGBA")
                img_rgb = img.convert(colmode)
                pixels = img_rgb.load()
                if trans:
                    bitmaps.append([[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(img.width)] for y in range(img.height)])
                else:
                    bitmaps.append([[pixels[x, y] for x in range(img.width)] for y in range(img.height)])
        else:
            img_rgb = img.convert(colmode)
            pixels = img_rgb.load()
            if trans:
                bitmap = [[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(img.width)] for y in range(img.height)]
            else:
                bitmap = [[pixels[x, y] for x in range(img.width)] for y in range(img.height)]

        img_rgb = None # take out the trash
        pixels = None
        frames = None

    output = ""
    if findbestlineskip and not animated: # animated images may be wildly inconsistant, and computing them all would take a really long time for what is a small efficiency gain in file size.
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
                lens[ls], af2pal = generate_runs_af2(bitmap, palette, int(ls), w, h, trans)
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
        if trans and not legacy:
            af2pal = " FF00FF"+af2pal # this is for decoders without transparency support
        apflist.append(af2pal)
    else:
        if animated:
            if legacy:
                outputs = []
                for bitmap in bitmaps:
                    temp = ""
                    runlens = generate_runs_af2_l(bitmap, lineskip, w, h)
                    for num in runlens:
                        temp += chr(num+32)
                    outputs.append(temp)
                output = "\n".join(outputs)
            else:
                #raise Exception("Unsupported!")
                outputs = []
                _, af2pal = generate_runs_af2(bitmaps[0], palette, lineskip, w, h, trans)
                for bitmap in bitmaps:
                    temp = ""
                    runlens, _ = generate_runs_af2(bitmap, palette, lineskip, w, h, trans)
                    for num in runlens:
                        temp += num[0]+chr(num[1]+32)
                    outputs.append(temp)

                output = "\n".join(outputs)
                if trans:
                    af2pal = " FF00FF"+af2pal # this is for decoders without transparency support
                apflist.append(af2pal)
        else:
            if legacy:
                runlens = generate_runs_af2_l(bitmap, lineskip, w, h)
                for num in runlens:
                    output += chr(num+32)
            else:
                runlens, af2pal = generate_runs_af2(bitmap, palette, lineskip, w, h, trans)
                if trans and not legacy:
                    af2pal = " FF00FF"+af2pal # this is for decoders without transparency support
                apflist.append(af2pal)
                for num in runlens:
                    output += num[0]+chr(num[1]+32)
    apflist.append(output)
    apftext = "\n".join(apflist)
    return apftext

# the following is an example of usage of the decoder. it expects a string as an input, outputs a bytes image.
#file_path = 'input.af2'
#with open(file_path, 'r') as f:
#    file_content = f.read()
#decodedapf = decodeaf2(file_content, 'PNG')
#with open("output.png", "wb") as f:
#    f.write(decodedapf)

# the following is an example of usage of the encoder. it expects a bytes image as an input, outputs a string.
#file_path = 'input.png'
#with open(file_path, "rb") as f:
#    data = io.BytesIO()
#    data = f.read()

#encodedapf = encodeaf2(data, 1, False, True, False)
#with open("output.af2", "w") as f:
#    f.write(encodedapf)
