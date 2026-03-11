w = 320
h = 200
headertext = "APERTURE IMAGE FORMAT (c) 1985"


def build_bitmap(flat_pixels, width, height):
    bitmap = []
    index = 0
    for _ in range(height):
        row = []
        for _ in range(width):
            row.append(bool(flat_pixels[index]))
            index += 1
        bitmap.append(row)
    return bitmap


def generate_runs(bitmap, lineskip):
    runcounter = 0
    currentrun = False
    runlens = []
    curline = h - 1
    revmap = []
    passoffset = 0
    for _ in range(h):
        revmap.append(bitmap[curline])
        curline -= lineskip
        if curline < 0:
            curline = h - 1
            passoffset += 1
            curline -= passoffset

    for vline in revmap:
        for pixel in vline:
            if currentrun == pixel:
                if runcounter + 1 > 94:
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


def encode_flat_bitmap(flat_pixels, width=320, height=200, lineskip=1, findbestlineskip=False):
    if width != w or height != h:
        raise ValueError("APF expects 320x200 input")

    bitmap = build_bitmap(flat_pixels, width, height)
    apflist = [headertext]

    if findbestlineskip:
        lens = {}
        shortest_id = None
        shortest_len = 999999999
        for i in range(1, h - 1):
            lens[str(i)] = generate_runs(bitmap, i)
        for ls, runlens in lens.items():
            total_len = len(runlens) + len(str(ls))
            if total_len < shortest_len:
                shortest_len = total_len
                shortest_id = ls
        apflist.append(shortest_id)
        runlens = lens[shortest_id]
    else:
        apflist.append(str(lineskip))
        runlens = generate_runs(bitmap, lineskip)

    output = ""
    for num in runlens:
        output += chr(num + 32)
    apflist.append(output)
    return "\n".join(apflist)


def decodeapf_flat(apf):
    apf_list = apf.splitlines()
    apf_lines = []
    for line in apf_list:
        if line:
            apf_lines.append(line)
    if apf_lines[0].strip() != headertext:
        raise ValueError("Invalid Aperture Image Format File")

    lineskip = int(apf_lines[1].strip())
    data = apf_lines[2]
    apfbuffer = []
    for _ in range(h):
        row = []
        for _ in range(w):
            row.append(False)
        apfbuffer.append(row)

    state = False
    x = 0
    y = h - 1
    passoffset = 0

    for char in data:
        runlen = ord(char) - 32
        for _ in range(runlen):
            apfbuffer[y][x] = state
            x += 1
            if not x < w:
                y = y - lineskip
                x = 0
            if y < 0:
                y = h - 1
                passoffset += 1
                y -= passoffset
        state = not state

    flat = []
    for y in range(h):
        row = apfbuffer[y]
        for x in range(w):
            flat.append(1 if row[x] else 0)
    return flat