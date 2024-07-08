const puppeteer = require('puppeteer');
const path = require('path');

async function convertHtmlToPdf(htmlFilePath, pdfFilePath) {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();

    // Adjust viewport height to cut off the bottom part of the page
    await page.setViewport({ width: 800, height: 300 }); // Adjust as needed

    // Load the HTML file into Puppeteer
    const fileUrl = 'file://' + path.resolve(htmlFilePath);
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });

    // wait for the selector appear on the page
    await page.screenshot({
        "type": "png", // can also be "jpeg" or "webp" (recommended)
        "path": "output.png",  // where to save it
        "fullPage": true,  // will scroll down to capture everything if true
    });

    // alternatively we can capture just a specific element:
    //const element = await page.$("root");
    //wait element.screenshot({"path": "just-the-root.png", "type": "png"});

    await browser.close();
    console.log(`PDF generated: ${pdfFilePath}`);
}

// Replace 'input.html' with your HTML file path and 'output.pdf' with desired PDF file path
convertHtmlToPdf('../templates/template.html', 'output.pdf');