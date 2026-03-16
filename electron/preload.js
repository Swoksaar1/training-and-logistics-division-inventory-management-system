const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  appName: "CDRRMO Management System",
});