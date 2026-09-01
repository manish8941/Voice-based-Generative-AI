# UI/UX Design System & Aesthetics (design.md)

This document details the user experience principles, visual design tokens, component hierarchy, and audio visualization algorithms used in the **Voice-to-Insight** application.

---

## 1. Design Philosophy
- **Function-Driven Simplicity**: Every UI element directly supports one of three steps: **Capture $\to$ Ground $\to$ Generate**.
- **High-Contrast Dark Theme**: Tailored for developer environments, reducing eye fatigue during extended coding and architecture sessions.
- **Dynamic Feedback**: Real-time visual feedback during recording (waveform visualizer, recording clock, pulse indicators) ensures confidence that speech is being captured accurately.

---

## 2. Color Palette & Design Tokens

| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| **`bg-primary`** | `#14181E` | Deep slate window background |
| **`bg-surface`** | `#1A202C` | Card and panel container backgrounds |
| **`bg-hover`** | `#2D3748` | Interactive button and drop-zone hover states |
| **`accent-blue`** | `#3182CE` | Primary action buttons and focus rings |
| **`accent-green`**| `#276749` | Blueprint generation & success indicators |
| **`accent-red`**  | `#9B2C2C` | Active recording indicator & stop action |
| **`text-primary`**| `#E2E8F0` | High-legibility headers and editor text |
| **`text-muted`**  | `#718096` | Metadata labels, timestamps, and placeholders |

---

## 3. Component Hierarchy & 3-Pane Layout

```
+-----------------------------------------------------------------------------------------------+
| ⚡ Voice-to-Insight Blueprint Engine               [Engine: Groq Cloud v] [🔑 Set API Key]     |
+-----------------------------------------------------------------------------------------------+
| [1. Audio Input]            | [2. Transcript & RAG]           | [3. Generated Blueprints]     |
|                             |                                 |                               |
| [ |||||||||||||||||||||| ]  | Recognized Speech:              | [🚀 Generate All] [📄 Active]  |
| 00:14.2                     | "We need to build a modular     | +---------------------------+ |
| [🎙️ Record] [⏸️ Pause]      | voice-to-insight system..."     | | PRD | Arch | Flow | Tasks | |
|                             |                                 | +---------------------------+ |
| [ Drop Audio File Here ]    | Words: 48 | Latency: 0.32s      | # Project Requirements Doc    |
| [📂 Browse File...]         |                                 | ## 1. Executive Summary...    |
|                             | [x] Enable Local RAG            |                               |
| STT Model: [whisper-v3-t v] | [📁 Index Codebase] 12 chunks   |                               |
| [⚡ Transcribe Audio]       |                                 | [💾 Export Repo] [📑 PDF]     |
+-----------------------------------------------------------------------------------------------+
| Ready.                                                             [======== Progress Bar ==] |
+-----------------------------------------------------------------------------------------------+
```

---

## 4. Audio Visualizer Mathematical Model
The multi-bar waveform visualizer maps real-time RMS audio power into a dynamic frequency spectrum display:
1. **RMS Power Calculation**:
   $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^N x[i]^2}, \quad L_{\text{norm}} = \min(1.0, \text{RMS} \times 10.0)$$
2. **Spatial Bell-Curve Weighting**: Bars near the center receive higher weight to simulate human vocal resonance:
   $$W(i) = \max\left(0.2, 1.0 - 0.7 \cdot \frac{|i - c|}{c}\right), \quad \text{where } c = \frac{N_{\text{bars}}}{2}$$
3. **Decay Physics**: When speech pauses, each bar falls exponentially at rate $\Delta L = -0.05$ every 30ms for natural fluid motion.
