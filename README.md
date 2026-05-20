# glue-edf

A [Glue](http://glueviz.org) plugin for viewing EDF (European Data Format) EEG and biosignal recordings.

## Installation

```bash
pip install -e .
```

Glue will discover the plugin automatically via the entry point — no further configuration needed.

## Usage

Launch Glue and drag an `.edf` file into the data collection, or use **File → Open Data**.  With the dataset selected, choose **EEG / EDF Viewer** from the viewer menu.

The viewer shows all signal channels stacked vertically with a shared time axis.  Use the scrollbar at the bottom to move through the recording, and adjust the visible window duration in the **Options** panel on the left.

## Regions of Interest

### From an external service

Call `add_roi_annotations` on the viewer object, passing a list of time ranges (in seconds from recording start):

```python
viewer.add_roi_annotations([
    (10.5, 14.2, 'Spike cluster', '#e74c3c'),
    (45.0, 48.5, 'Artefact',      '#f39c12'),
    (120.0, 121.3),                            # label and colour are optional
])
```

Each entry may be:

| Form | Fields |
|------|--------|
| `(t_start, t_end)` | timestamps only |
| `(t_start, t_end, label)` | with a display label |
| `(t_start, t_end, label, color)` | with a hex colour string |

### Interacting with regions

Regions appear as coloured spans on the plot and as entries in the **Regions of Interest** panel on the right.  From the panel you can:

- **Double-click** an entry (or select it and press **Go To**) to centre the time window on that region.
- **Remove** selected entries, or **Clear All** to remove everything.
