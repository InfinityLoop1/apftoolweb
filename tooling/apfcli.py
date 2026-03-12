import sys
import os
import io
import apftool
from PIL import Image

exts = Image.registered_extensions()
supported_extensions = {ex for ex, f in exts.items() if f in Image.OPEN}

def main():
    if len(sys.argv) < 3:
        print("Usage: python apfcli.py <input_file> <output file> <args: --lineskip=INT --findbestlineskip --legacy --transparent --palette=INT --format=IMAGE-FORMAT (decoder)>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    args = None
    if len(sys.argv) > 3:
        args = sys.argv[3:]
    base, ext = os.path.splitext(input_path)
    _, opext = os.path.splitext(output_path)
    ext = ext.lower()
    fbls = False
    legacy = False
    trans = False
    forma = 'PNG'
    maxpalette = 95
    lineskip = 1
    if args:
        if "--findbestlineskip" in args:
            fbls = True
        if "--legacy" in args:
            legacy = True
        if "--transparent" in args:
            trans = True
        for arg in args:
            if arg.startswith("--format="):
                forma = arg.replace("--format=", "")
            if arg.startswith("--palette="):
                maxpalette = int(arg.replace("--palette=", ""))
            if arg.startswith("--lineskip="):
                lineskip = int(arg.replace("--lineskip=", ""))

    # PNG to APF/AF2
    if ext in supported_extensions:
        with open(input_path, "rb") as f:
            img_bytes = f.read()
        if opext in (".apf", ".aif"):
            encoded = apftool.encodeapf(img_bytes, lineskip=lineskip, findbestlineskip=fbls)
        else:
            encoded = apftool.encodeaf2(img_bytes, lineskip=lineskip, findbestlineskip=fbls, legacy=legacy, trans=trans, pal=maxpalette)
        with open(output_path, "w") as f:
            f.write(encoded)
        print(f"Encoded {input_path} -> {output_path}")

    # APF/AF2 to PNG
    elif ext in apftool.extensions:
        with open(input_path, "r") as f:
            apf_content = f.read()
        decoded_bytes = apftool.decodeaf2(apf_content, forma)
        with open(output_path, "wb") as f:
            f.write(decoded_bytes)
        print(f"Decoded {input_path} -> {output_path}")

    else:
        print("Unsupported file type. Please use an image format supported by the encoder/decoder.")
        sys.exit(1)

if __name__ == "__main__":
    main()
