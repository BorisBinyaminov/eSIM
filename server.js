const express = require("express");
const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = process.env.PORT || 5000;

// Serve the React build files
app.use(express.static(path.join(__dirname, "build")));

// Function to log update timestamp
const logUpdateTime = () => {
  const timestamp = new Date().toLocaleString();
  console.log(`✅ Packages updated at: ${timestamp}`);
  fs.writeFileSync("public/lastUpdate.txt", `Last package update: ${timestamp}`);
};

// Function to periodically fetch package data
const fetchPackagesPeriodically = () => {
  console.log("⏳ Fetching package data...");
  exec("node fetchPackages.js", (error, stdout, stderr) => {
    if (error) {
      console.error(`❌ Error fetching packages: ${error.message}`);
      return;
    }
    if (stderr) {
      console.error(`⚠️ Fetch warning: ${stderr}`);
      return;
    }
    console.log(`✅ Packages updated successfully:\n${stdout}`);
    logUpdateTime();
  });
};

// Run fetchPackages.js every hour
setInterval(fetchPackagesPeriodically, 60 * 60 * 1000);

// Serve the frontend React app
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "build", "index.html"));
});

// Start the server
app.listen(PORT, () => {
  console.log(`✅ Server is running on port ${PORT}`);
  fetchPackagesPeriodically();
});
