// vite.config.js — Vite Build Tool Configuration
//
// Vite is the build tool that bundles our React code for the browser.
// This config file tells Vite how to process our files.

import { defineConfig } from "vite";         // Vite's config helper
import react from "@vitejs/plugin-react";     // Plugin that enables JSX and React Fast Refresh

export default defineConfig({
  // Register the React plugin so Vite understands JSX syntax
  plugins: [react()],

  // Development server settings
  server: {
    port: 5173,     // The port our frontend runs on during development
    open: true,     // Automatically open the browser when the dev server starts
  },
});
