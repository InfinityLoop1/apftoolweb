const imageInput = document.getElementById("imageInput");
const uploadForm = document.getElementById("uploadForm");
const originalPreview = document.getElementById("originalPreview");
const convertedCanvas = document.getElementById("convertedCanvas");
const downloadApf = document.getElementById("downloadApf");
const downloadPng = document.getElementById("downloadPng");
const status = document.getElementById("status");
const statusText = document.getElementById("statusText");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");

const hiddenCanvas = document.createElement("canvas");
hiddenCanvas.width = 320;
hiddenCanvas.height = 200;
const hiddenContext = hiddenCanvas.getContext("2d", { willReadFrequently: true });
const convertedContext = convertedCanvas.getContext("2d", { willReadFrequently: true });

let pyodideInstance;
let apfTextUrl;
let pngUrl;
let displayedProgress = 0;
let progressAnimationFrame;
let autoProgressTimer;

function clampProgress(value) {
    return Math.max(0, Math.min(100, value));
}

function paintProgress(value) {
    const clamped = clampProgress(value);
    status.style.setProperty("--progress", `${clamped}%`);
}

function animateProgressTo(target, duration = 260) {
    const clampedTarget = clampProgress(target);
    if (progressAnimationFrame) {
        cancelAnimationFrame(progressAnimationFrame);
        progressAnimationFrame = undefined;
    }

    const start = displayedProgress;
    const delta = clampedTarget - start;
    if (Math.abs(delta) < 0.2 || duration <= 0) {
        displayedProgress = clampedTarget;
        paintProgress(displayedProgress);
        return;
    }

    const startedAt = performance.now();

    function tick(now) {
        const elapsed = now - startedAt;
        const progress = Math.min(1, elapsed / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        displayedProgress = start + delta * eased;
        paintProgress(displayedProgress);
        if (progress < 1) {
            progressAnimationFrame = requestAnimationFrame(tick);
        } else {
            progressAnimationFrame = undefined;
            displayedProgress = clampedTarget;
            paintProgress(displayedProgress);
        }
    }

    progressAnimationFrame = requestAnimationFrame(tick);
}

function stopAutoProgress() {
    if (autoProgressTimer) {
        clearInterval(autoProgressTimer);
        autoProgressTimer = undefined;
    }
}

function startAutoProgress(maxProgress, step = 1.2, intervalMs = 140) {
    stopAutoProgress();
    const cap = clampProgress(maxProgress);
    autoProgressTimer = setInterval(() => {
        if (displayedProgress >= cap) {
            return;
        }
        animateProgressTo(Math.min(cap, displayedProgress + step), 220);
    }, intervalMs);
}

function setStatus(message, progress = 0, options = {}) {
    const clamped = clampProgress(progress);
    statusText.textContent = message;
    if (options.immediate) {
        displayedProgress = clamped;
        paintProgress(displayedProgress);
    } else {
        animateProgressTo(clamped, options.duration ?? 260);
    }
    status.classList.remove("hidden");
}

function clearError() {
    errorBox.textContent = "";
    errorBox.classList.add("hidden");
}

function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function revokeDownloads() {
    if (apfTextUrl) {
        URL.revokeObjectURL(apfTextUrl);
        apfTextUrl = undefined;
    }
    if (pngUrl) {
        URL.revokeObjectURL(pngUrl);
        pngUrl = undefined;
    }
}

async function loadRuntime() {
    setStatus("loading python runtime", 5, { immediate: true });
    startAutoProgress(88, 1.4, 130);
    pyodideInstance = await loadPyodide();
    setStatus("loading python runtime", 55, { duration: 300 });
    const runtimeSource = await fetch("./apf_runtime.py").then((response) => response.text());
    setStatus("loading python runtime", 75, { duration: 300 });
    await pyodideInstance.runPythonAsync(runtimeSource);
    stopAutoProgress();
    setStatus("python runtime ready", 100, { duration: 220 });
    uploadForm.classList.remove("hidden");
}

function createOriginalPreview(file) {
    const objectUrl = URL.createObjectURL(file);
    originalPreview.onload = () => URL.revokeObjectURL(objectUrl);
    originalPreview.src = objectUrl;
}

function fileBaseName(name) {
    const dotIndex = name.lastIndexOf(".");
    if (dotIndex === -1) {
        return name || "image";
    }
    return name.slice(0, dotIndex) || "image";
}

function ditherToBitmap(imageData) {
    const grayscale = new Float32Array(320 * 200);
    for (let index = 0; index < grayscale.length; index += 1) {
        const offset = index * 4;
        const red = imageData.data[offset];
        const green = imageData.data[offset + 1];
        const blue = imageData.data[offset + 2];
        grayscale[index] = red * 0.299 + green * 0.587 + blue * 0.114;
    }

    const output = new Array(320 * 200);
    for (let y = 0; y < 200; y += 1) {
        for (let x = 0; x < 320; x += 1) {
            const index = y * 320 + x;
            const oldPixel = grayscale[index];
            const newPixel = oldPixel >= 128 ? 255 : 0;
            const error = oldPixel - newPixel;
            output[index] = newPixel === 255 ? 1 : 0;

            if (x + 1 < 320) {
                grayscale[index + 1] += error * 7 / 16;
            }
            if (x > 0 && y + 1 < 200) {
                grayscale[index + 319] += error * 3 / 16;
            }
            if (y + 1 < 200) {
                grayscale[index + 320] += error * 5 / 16;
            }
            if (x + 1 < 320 && y + 1 < 200) {
                grayscale[index + 321] += error * 1 / 16;
            }
        }
    }
    return output;
}

async function fileToBitmap(file) {
    const imageBitmap = await createImageBitmap(file);
    hiddenContext.clearRect(0, 0, 320, 200);
    hiddenContext.imageSmoothingEnabled = true;
    hiddenContext.drawImage(imageBitmap, 0, 0, 320, 200);
    imageBitmap.close();
    return ditherToBitmap(hiddenContext.getImageData(0, 0, 320, 200));
}

function renderBitmap(flatBitmap) {
    const output = convertedContext.createImageData(320, 200);
    for (let index = 0; index < flatBitmap.length; index += 1) {
        const offset = index * 4;
        const value = flatBitmap[index] ? 255 : 0;
        output.data[offset] = value;
        output.data[offset + 1] = value;
        output.data[offset + 2] = value;
        output.data[offset + 3] = 255;
    }
    convertedContext.putImageData(output, 0, 0);
}

async function updateDownloads(baseName, apfText) {
    revokeDownloads();
    apfTextUrl = URL.createObjectURL(new Blob([apfText], { type: "text/plain;charset=utf-8" }));
    pngUrl = await new Promise((resolve) => {
        convertedCanvas.toBlob((blob) => {
            resolve(URL.createObjectURL(blob));
        }, "image/png");
    });
    downloadApf.href = apfTextUrl;
    downloadApf.download = `${baseName}.apf`;
    downloadPng.href = pngUrl;
    downloadPng.download = `${baseName}-converted.png`;
}

async function processFile(file) {
    if (!file) {
        return;
    }

    try {
        clearError();
        setStatus("converting image", 6, { immediate: true });
        startAutoProgress(94, 1.7, 120);
        createOriginalPreview(file);
        setStatus("converting image", 20, { duration: 220 });
        const flatBitmap = await fileToBitmap(file);
        setStatus("converting image", 42, { duration: 240 });
        const pyBitmap = pyodideInstance.toPy(flatBitmap);
        setStatus("converting image", 58, { duration: 240 });
        const encodeFlatBitmap = pyodideInstance.globals.get("encode_flat_bitmap");
        const decodeapfFlat = pyodideInstance.globals.get("decodeapf_flat");
        const apfText = encodeFlatBitmap(pyBitmap, 320, 200, 3, true);
        setStatus("converting image", 74, { duration: 240 });
        pyBitmap.destroy();
        const decodedProxy = decodeapfFlat(apfText);
        setStatus("converting image", 86, { duration: 200 });
        const decodedBitmap = decodedProxy.toJs();
        decodedProxy.destroy();
        renderBitmap(decodedBitmap);
        setStatus("converting image", 94, { duration: 180 });
        await updateDownloads(fileBaseName(file.name), apfText);
        result.classList.remove("hidden");
        stopAutoProgress();
        setStatus("conversion complete", 100, { duration: 220 });
    } catch (error) {
        stopAutoProgress();
        result.classList.add("hidden");
        showError(`conversion failed: ${error.message || error}`);
        setStatus("ready", 0, { duration: 220 });
    }
}

imageInput.addEventListener("change", async () => {
    const file = imageInput.files && imageInput.files[0] ? imageInput.files[0] : null;
    await processFile(file);
});

window.addEventListener("paste", async (event) => {
    const items = event.clipboardData && event.clipboardData.items ? event.clipboardData.items : [];
    for (const item of items) {
        if (item.type && item.type.startsWith("image/")) {
            const file = item.getAsFile();
            if (file) {
                event.preventDefault();
                await processFile(file);
                return;
            }
        }
    }
});

await loadRuntime();