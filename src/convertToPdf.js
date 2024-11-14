const puppeteer = require('puppeteer');
const path = require('path');
const sharp = require('sharp');
const fs = require('fs');

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function exampleFunction() {
    console.log("Before sleep");
    await sleep(2000);  // Pauses for 2000 milliseconds (2 seconds)
    console.log("After sleep");
}


async function convertHtmlToPng(htmlFilePath, pdfFilePath) {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    await page.setViewport({ width: 3840, height: 2160 });  // Sets the size of the screen of the virtual browser

    // Load the HTML file into Puppeteer
    const fileUrl = 'file://' + path.resolve(htmlFilePath);
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });

    // wait for the selector appear on the page
    await page.screenshot({
        "type": "png", // can also be "jpeg" or "webp" (recommended)
        "path": pdfFilePath,  // where to save it
        "fullPage": true,  // will scroll down to capture everything if true
    });

    await browser.close();
    console.log('png generated: ' + pdfFilePath);
}

function cropImage(inputPath, outputPath) {
    // Define the crop area
    const cropOptions = {
        left: 0,   // X offset
        top: 0,    // Y offset
        width: 1400,  // Width of the crop area
        height: 788  // Height of the crop area
    };

    sharp(inputPath)
        .extract(cropOptions)  // Crop the image
        .toFile(outputPath)    // Save the cropped image
        .then(() => {
            console.log('Image cropped and saved successfully!');
        })
        .catch(err => {
            console.error('Error cropping the image:', err);
        });
}

async function convertPngToPdf(pngPath, pdfPath) {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    // Load the image file as data URI
    const imageData = fs.readFileSync(pngPath, 'base64');
    const imageURI = `data:image/png;base64,${imageData}`;

    // Set HTML content with the image
    const htmlContent = `<html><body style="margin:0;">
    <img src="${imageURI}" style="width:100%;height:auto;">
    </body></html>`;

    await page.setContent(htmlContent);
    // Set viewport and PDF size to 1400x788
    await page.setViewport({ width: 1400, height: 788 });
    await page.pdf({
        path: pdfPath,
        width: '1400px',
        height: '788px',
        printBackground: true
    });
    await browser.close();
}

async function processFilesSequentially() {
    let dirPath = "../"

    // Count signatures and get the name without extension
    let filenames = Array.from(fs.readdirSync(dirPath + "certs/")).map(filename => {
        let parsed = path.parse(filename);
        return parsed.name;
    });

    for (let i = 0; i < filenames.length; i++) {
        if (filenames.at(i).includes(".gitignore")) {
            console.log("igorint gitignore")
            continue;
        }

        if (filenames.at(i).includes("template_files")) {
            console.log("igorint template")
            continue;
        }

        console.log("process" + filenames.at(i))

        try {
            const inputPath = '../certs/' + filenames.at(i) + '.html';
            const pngPath = '../pngs/' + filenames.at(i) + '.png';
            const croppedPngPath = '../pngs_cropped/' + filenames.at(i) + '.png';
            const pdfPath = '../pdfs/' + filenames.at(i) + '.pdf';

            // Convert HTML to PNG
            await convertHtmlToPng(inputPath, pngPath);
            console.log("Conversion from HTML to PNG for " + filenames.at(i) + " completed!");

            // Crop the image
            await cropImage(pngPath, croppedPngPath);

            // Convert PNG to PDF
            await convertPngToPdf(croppedPngPath, pdfPath);
            console.log("PDF created successfully!");
        } catch (error) {
            console.error('Error processing file:', error);
        }
    }
}



// Call the async function
processFilesSequentially();