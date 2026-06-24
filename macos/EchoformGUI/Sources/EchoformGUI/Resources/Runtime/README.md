# Echoform Runtime Placeholder

This folder is reserved for a bundled Python runtime in the packaged macOS app.

Development builds can use the app-managed runtime created at:

```text
<engine-root>/.echoform-runtime/venv/bin/python
```

Release builds should copy a prepared runtime here so the app can run without asking the user to install Python packages.
