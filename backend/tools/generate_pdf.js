/**
 * Safe&Sound — Generador de PDF con Puppeteer
 * Crea un PDF visual idéntico a la interfaz de presentación (portada + comparativo + cierre)
 */

import puppeteer from "puppeteer";
import fs from "fs";
import path from "path";

async function generarPDF({
  url = "http://localhost:4321/presentacion",
  outputDir = "./backend/comparativos",
  nombreCliente = "Cliente",
  waitTime = 3000, // ms para cargar datos
} = {}) {
  console.log("🚀 Iniciando Puppeteer...");

  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const page = await browser.newPage();

  console.log(`🌐 Navegando a ${url} ...`);
  await page.goto(url, { waitUntil: "networkidle0" });

  console.log(`⏳ Esperando ${waitTime / 1000}s para carga de datos...`);
  await page.waitForTimeout(waitTime);

  // Ajustes de render para PDF
  await page.emulateMediaType("screen");

  // Nombre del archivo
  const safeName = nombreCliente.replace(/\s+/g, "_").toLowerCase();
  const outputPath = path.resolve(outputDir, `comparativo_${safeName}.pdf`);

  // Asegura carpeta de salida
  fs.mkdirSync(outputDir, { recursive: true });

  console.log("🖨️ Generando PDF...");
  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    margin: {
      top: "0mm",
      bottom: "0mm",
      left: "0mm",
      right: "0mm",
    },
  });

  await browser.close();
  console.log(`✅ PDF generado con éxito: ${outputPath}`);
}

// 🧠 Ejecutable directo (CLI)
if (import.meta.url === `file://${process.argv[1]}`) {
  const nombre = process.argv[2] || "SafeAndSound";
  generarPDF({ nombreCliente: nombre }).catch(console.error);
}

export default generarPDF;
