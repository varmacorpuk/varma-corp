const { app, BrowserWindow } = require("electron");
const path = require("path");

function create() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "Varma Corp. — Board Member control room",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(create);
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
