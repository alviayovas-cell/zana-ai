# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.

---

## 🎙️ Phase 3: Voice Assistant

Zana now features a fully integrated **Voice Assistant Input Layer** that allows you to control music playback and interact with the chatbot hands-free using your voice.

### How It Works:
1. Click the glowing microphone icon (**🎤**) next to the text input box.
2. Grant microphone permissions when prompted by your browser.
3. The input box will transition into a red pulsing **Listening** state (🔴 *Listening...*).
4. Speak a command clearly (e.g., *"Play Starboy"*, *"Pause"*, *"Resume"*, or *"Next song"*).
5. The Speech-to-Text engine will convert your speech to text and automatically send it into Zana's existing chat and control pipeline.

### Supported Commands:
- **Play track**: *"Play Starboy"*, *"Play Calm Lofi"*
- **Pause**: *"Pause"*, *"Stop music"*
- **Resume**: *"Resume"*, *"Unpause"*
- **Next song**: *"Next song"*, *"Skip"*
- **Volume control**: *"Set volume to 80"*, *"Volume 50"*

### Browser Compatibility:
- Supported in Google Chrome, Microsoft Edge, and modern Chromium-based browsers using standard Web Speech APIs (`SpeechRecognition` / `webkitSpeechRecognition`).
- If voice input is not supported in the active browser, a fallback warning is displayed, and standard keyboard typing remains fully active.

