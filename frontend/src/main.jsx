// main.jsx — React Application Entry Point
//
// This is the very first JavaScript file that runs when the app loads.
// It takes our root App component and mounts it into the HTML page
// at the <div id="root"> element.

import React from "react";                    // React core library
import ReactDOM from "react-dom/client";      // React DOM renderer for the browser
import App from "./App.jsx";                  // Our main application component

// Find the <div id="root"> element in index.html and mount React into it
// StrictMode enables extra development warnings to help catch bugs early
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
