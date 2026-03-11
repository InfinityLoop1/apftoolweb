a small library for converting to and from Aperture Science apf files.

usage: 

```
import apftool
apfString = apftool.encodeapf(pngObject) # turns image bytes object into apf string
pngObject = apftool.decodeapf(apfString) # turns apf string object into image bytes
```

included is a simple cli tool.

usage:

```
python apfcli.py maricom.png # creates maricom.apf
python apfcli.py maricom.apf # creates maricom.png
```

dependancies: `PIL, io` (apftool)

dependancies: `sys, os, io` (apfcli)

most of these a builtins but you may need to install PIL seporately

cloudflare pages deployment:

this repo now includes a static pages app in `pages/` that runs the apf conversion in the browser using python via pyodide.

deploy settings:

```
framework preset: none
build command: 
build output directory: pages
```

after connecting the repo in cloudflare pages, set the output directory to `pages` and deploy.
