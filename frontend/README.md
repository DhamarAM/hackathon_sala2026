# Dragon Ocean Analyzer — Frontend

Marine bioacoustics research platform for the Galapagos Marine Reserve.

## Setup

```bash
npm install
npm run dev
```

Opens at `http://localhost:3000`

## Data Requirements

The dev server expects analysis data from two collaborator repositories at relative paths:

- `../GitHub/hackathon_sala2026-main(Colaborator2)/output/` — basic analysis
- `../GitHub/hackathon_sala2026-main(Colaborator2)/output2/` — cascade analysis
- `../GitHub/hackathon_sala2026-master(Colaborator1)/data/raw_data/` — audio WAV files

If your data is elsewhere, edit the paths in `vite.config.js`.

## Project Structure

```
src/
  main.jsx              Entry point
  App.jsx               Root component, routing, providers
  config.js             API paths, tier config, species map
  utils.js              Data loaders, formatters, CSV export
  styles.css            Global theme (dark + light)

  context/
    ThemeContext.jsx     Dark/light theme toggle

  pages/
    LandingPage.jsx     Hero, pipeline diagram, features
    SingleObservation.jsx   Single-file analysis view
    MultipleObservations.jsx   Batch report with table

  components/
    Navbar.jsx           Top navigation bar
    Sidebar.jsx          Slide-out menu
    PipelineDiagram.jsx  5-stage cascade flow diagram
    SpectrogramViewer.jsx   Zoomable spectrogram + audio player
    ReportTable.jsx      Sortable/filterable report table
    DetailModal.jsx      Per-file detail popup
    AnalysisPanel.jsx    Scores, classifiers, annotations
    TierBadge.jsx        Colored tier label
    Charts.jsx           All Chart.js visualizations
```

## Team Workflow

Three people can work independently on these areas:

### Person A — Pages & Layout
- `src/pages/*.jsx`
- `src/App.jsx`
- Navigation, routing, page structure

### Person B — Components & Visualizations
- `src/components/*.jsx`
- Charts, spectrogram interactions, data display
- `src/styles.css` (component styles)

### Person C — Data & Services
- `src/config.js` and `src/utils.js`
- `vite.config.js` (data serving)
- Backend integration, data transformations
- `src/context/*.jsx`

### Branch Strategy

```
main              <- stable, presentation-ready
  feature/pages   <- Person A
  feature/viz     <- Person B
  feature/data    <- Person C
```

Create feature branches from main, PR back with review.

## Build

```bash
npm run build     # Output to dist/
npm run preview   # Preview production build
```

## Tech Stack

- React 18 + React Router 6
- Vite 6
- Chart.js + react-chartjs-2
- Custom CSS with CSS Variables (dual theme)
