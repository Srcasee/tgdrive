import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import https from "node:https";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const base = "https://raw.githubusercontent.com/imwangfan/SnowAdmin/main/src/assets";
const assets = [
  "img/Abbey Road.jpg",
  "img/The Dark Side of The Moon.jpg",
  "img/bgc.jpg",
  "img/logo.jpg",
  "img/my-image.jpg",
  "img/official-account.png",
  "img/other-image.jpg",
  "img/tom.jpg",
  "fonts/AlimamaFangYuanTiVF-Thin.ttf"
];

function download(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, response => {
        if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
          response.resume();
          return download(response.headers.location).then(resolve, reject);
        }
        if (response.statusCode !== 200) {
          response.resume();
          reject(new Error(`HTTP ${response.statusCode} for ${url}`));
          return;
        }
        const chunks = [];
        response.on("data", chunk => chunks.push(chunk));
        response.on("end", () => resolve(Buffer.concat(chunks)));
        response.on("error", reject);
      })
      .on("error", reject);
  });
}

for (const relativePath of assets) {
  const target = join(root, "src", "assets", relativePath);
  await mkdir(dirname(target), { recursive: true });
  const content = await download(`${base}/${relativePath.split(" ").map(encodeURIComponent).join(" ")}`);
  await writeFile(target, content);
  console.log(`fetched SnowAdmin asset: ${relativePath}`);
}
