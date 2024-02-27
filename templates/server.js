const express = require('express');
const bodyParser = require('body-parser');
const puppeteer = require('puppeteer');

const app = express();
const port = 3000;

app.use(bodyParser.urlencoded({ extended: true }));

app.post('/convert', async (req, res) => {
    const { url } = req.body;

    try {
        const browser = await puppeteer.launch({ headless: true });
        const page = await browser.newPage();

        await page.goto('https://mathexact.com/tools/free-slideshare-downloader', { waitUntil: 'networkidle2' });

        await page.waitForSelector('input[name="url"]');
        await page.type('input[name="url"]', url);
        await page.click('button[type="submit"]');

        await page.waitForTimeout(5000); // Wait for PDF generation (adjust timeout as needed)

        const pdfBuffer = await page.pdf({ format: 'A4' });
        
        await browser.close();

        res.setHeader('Content-Type', 'application/pdf');
        res.send(pdfBuffer);
    } catch (error) {
        console.error('Error:', error);
        res.status(500).send({ error: 'Failed to convert Slideshare link.' });
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
