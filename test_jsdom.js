const { JSDOM } = require("jsdom");
const fs = require("fs");

const vmmcSelectCode = fs.readFileSync("static/js/vmmc-select.js", "utf8");

const dom = new JSDOM(`
    <!DOCTYPE html>
    <html><body><div id="sel"></div></body></html>
`, { runScripts: "outside-only" });

dom.window.eval(vmmcSelectCode);

// Mock fetch
dom.window.fetch = async () => ({
    ok: true,
    json: async () => [{id: 1, name: "Leanne Graham"}]
});

dom.window.eval(`
    const sel = new VMMCSearchSelect('#sel', {
        url: '/test',
        processResults: data => data,
        renderMain: item => item.name,
        onSelect: item => console.log('SELECTED:', item.name)
    });
`);

const window = dom.window;
const document = window.document;
const input = document.querySelector(".vss-input");

// Simulate focus
input.dispatchEvent(new window.Event("focus"));

// Wait a bit
setTimeout(() => {
    input.value = "Lea";
    input.dispatchEvent(new window.Event("input"));
    
    setTimeout(() => {
        const item = document.querySelector(".vss-item");
        if (item) {
            console.log("Item found:", item.textContent);
            
            // simulate mousedown, mouseup, click
            item.dispatchEvent(new window.MouseEvent("mousedown"));
            item.dispatchEvent(new window.MouseEvent("mouseup"));
            item.dispatchEvent(new window.MouseEvent("click"));
            
            console.log("Input value:", input.value);
        } else {
            console.log("No item found");
        }
    }, 500);
}, 100);
