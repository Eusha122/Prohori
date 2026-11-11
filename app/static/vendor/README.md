# Third-party files

| File | Library | Version | License |
|---|---|---|---|
| `html2pdf.bundle.min.js` | [html2pdf.js](https://github.com/eKoopmans/html2pdf.js) by Erik Koopmans, bundling [jsPDF](https://github.com/parallax/jsPDF) and [html2canvas](https://github.com/niklasvh/html2canvas) | 0.10.1 | MIT (all three) |

Used by the investigator brief page to download the whole brief as a PDF in the visitor's browser. It is kept here
(not loaded from a CDN) so the site does not depend on another website. It is loaded only when the button is pressed.
