const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");

let mainWindow = null;
let backendProcess = null;

const isDev = !app.isPackaged;
const APP_TITLE = "CDRRMO Inventory Management System";
const FRONTEND_DEV_URL = "http://localhost:3000";
const BACKEND_URL = "http://127.0.0.1:8000";
const BACKEND_HEALTHCHECK = `${BACKEND_URL}/api/auth/me`;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function checkServer(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      resolve(Boolean(res.statusCode && res.statusCode < 500));
      res.resume();
    });

    req.on("error", () => resolve(false));

    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend(url, retries = 40, delay = 1000) {
  for (let i = 0; i < retries; i += 1) {
    const ok = await checkServer(url);
    if (ok) return true;
    await wait(delay);
  }
  return false;
}

function ensureLogDir() {
  const logDir = path.join(app.getPath("userData"), "logs");
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  return logDir;
}

function writeBackendLog(message) {
  try {
    const logDir = ensureLogDir();
    const logFile = path.join(logDir, "backend.log");
    const line = `[${new Date().toISOString()}] ${message}\n`;
    fs.appendFileSync(logFile, line, "utf8");
  } catch (error) {
    console.error("Failed writing backend log:", error);
  }
}

function getWindowIconPath() {
  return path.join(__dirname, "icon.ico");
}

function getFrontendBuildPath() {
  return path.join(app.getAppPath(), "frontend", "build", "index.html");
}

function getBackendExePath() {
  if (isDev) return null;

  return path.join(
    process.resourcesPath,
    "backend",
    "inventory_backend",
    "inventory_backend.exe"
  );
}

function getBackendWorkingDir() {
  if (isDev) {
    return path.join(__dirname, "..");
  }

  return path.join(
    process.resourcesPath,
    "backend",
    "inventory_backend"
  );
}

function getPythonExecutable() {
  const projectRoot = path.join(__dirname, "..");
  const venvPython = path.join(projectRoot, "venv", "Scripts", "python.exe");

  if (fs.existsSync(venvPython)) {
    return venvPython;
  }

  return "python";
}

function attachBackendLogs(proc) {
  if (!proc) return;

  if (proc.stdout) {
    proc.stdout.on("data", (data) => {
      const msg = data.toString();
      console.log(`[BACKEND] ${msg}`);
      writeBackendLog(`[STDOUT] ${msg}`);
    });
  }

  if (proc.stderr) {
    proc.stderr.on("data", (data) => {
      const msg = data.toString();
      console.error(`[BACKEND ERROR] ${msg}`);
      writeBackendLog(`[STDERR] ${msg}`);
    });
  }

  proc.on("close", (code) => {
    console.log(`Backend process exited with code ${code}`);
    writeBackendLog(`Process exited with code ${code}`);
    backendProcess = null;
  });

  proc.on("error", (error) => {
    console.error("Failed to start backend process:", error);
    writeBackendLog(`Failed to start backend process: ${error.message}`);
    backendProcess = null;
  });
}

function startBackend() {
  if (backendProcess) return;

  const cwd = getBackendWorkingDir();

  writeBackendLog(`isDev=${isDev}`);
  writeBackendLog(`Backend cwd: ${cwd}`);

  if (isDev) {
    const pythonExe = getPythonExecutable();
    const managePyPath = path.join(cwd, "manage.py");

    writeBackendLog(`Dev python path: ${pythonExe}`);
    writeBackendLog(`Dev manage.py path: ${managePyPath}`);

    if (!fs.existsSync(managePyPath)) {
      const msg = `manage.py not found: ${managePyPath}`;
      console.error(msg);
      writeBackendLog(msg);
      return;
    }

    if (pythonExe !== "python" && !fs.existsSync(pythonExe)) {
      const msg = `Python executable not found: ${pythonExe}`;
      console.error(msg);
      writeBackendLog(msg);
      return;
    }

    backendProcess = spawn(
      pythonExe,
      [managePyPath, "runserver", "127.0.0.1:8000", "--noreload", "--nothreading"],
      {
        cwd,
        shell: false,
        windowsHide: true,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
        },
      }
    );

    attachBackendLogs(backendProcess);
    return;
  }

  const exePath = getBackendExePath();
  writeBackendLog(`Backend exe path: ${exePath}`);

  if (!fs.existsSync(exePath)) {
    const msg = `Backend executable not found: ${exePath}`;
    console.error(msg);
    writeBackendLog(msg);
    return;
  }

  backendProcess = spawn(exePath, [], {
    cwd,
    shell: false,
    windowsHide: true,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
    },
  });

  attachBackendLogs(backendProcess);
}

function stopBackend() {
  if (!backendProcess) return;

  try {
    if (process.platform === "win32" && backendProcess.pid) {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], {
        shell: false,
        windowsHide: true,
      });
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch (error) {
    console.error("Failed to stop backend:", error);
    writeBackendLog(`Failed to stop backend: ${error.message}`);
  }

  backendProcess = null;
}

function attachElectronDebugLogs(win) {
  if (!win) return;

  win.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL) => {
      console.error("did-fail-load:", {
        errorCode,
        errorDescription,
        validatedURL,
      });
    }
  );

  win.webContents.on(
    "console-message",
    (_event, level, message, line, sourceId) => {
      console.log(`[RENDERER:${level}] ${message} (${sourceId}:${line})`);
    }
  );

  win.webContents.on("did-finish-load", () => {
    console.log("Window finished loading:", win.webContents.getURL());
    win.setTitle(APP_TITLE);
  });

  win.on("page-title-updated", (event) => {
    event.preventDefault();
    win.setTitle(APP_TITLE);
  });
}

async function createWindow() {
  startBackend();

  const backendReady = await waitForBackend(BACKEND_HEALTHCHECK, 40, 1000);
  console.log(`Backend ready: ${backendReady}`);
  writeBackendLog(`Backend ready: ${backendReady}`);

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    title: APP_TITLE,
    icon: getWindowIconPath(),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.removeMenu();
  attachElectronDebugLogs(mainWindow);

  mainWindow.once("ready-to-show", () => {
    mainWindow.setTitle(APP_TITLE);
    mainWindow.show();

    if (isDev) {
      mainWindow.webContents.openDevTools({ mode: "right" });
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  if (isDev) {
    await mainWindow.loadURL(FRONTEND_DEV_URL);
  } else {
    const frontendPath = getFrontendBuildPath();
    writeBackendLog(`Frontend path: ${frontendPath}`);

    if (!fs.existsSync(frontendPath)) {
      throw new Error(`Frontend build not found: ${frontendPath}`);
    }

    await mainWindow.loadFile(frontendPath);
  }
}

app.whenReady().then(async () => {
  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("before-quit", () => {
  stopBackend();
});

app.on("window-all-closed", () => {
  stopBackend();

  if (process.platform !== "darwin") {
    app.quit();
  }
});