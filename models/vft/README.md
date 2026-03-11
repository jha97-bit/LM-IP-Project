# Value-Focused Thinking (VFT) Application

This is a Streamlit application for Value-Focused Thinking (VFT) analysis. It allows users to define objectives (attributes) and alternatives, configure value functions and weights, and analyze the results using various visualizations.

## Features

1.  **Setup**: Manage Objectives/Attributes and Alternatives.
2.  **Scaling**: Configure Value Functions (Linear or Custom) with interactive graphs.
3.  **Weighting**: Adjust Swing Weights using sliders, visualized with Pie and Bar charts.
4.  **Scoring & Analysis**: Input raw scores and view detailed analysis including Rankings and Contribution Charts.
5.  **Comparison**: Compare alternatives side-by-side using Radar Charts.
6.  **Sensitivity Analysis**: Analyze how variations in attribute weights affect overall scores and rankings.
7.  **Persistence**: Save and Load models to/from JSON files.

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the application using Streamlit:

```bash
streamlit run app.py
```

## Structure

-   `app.py`: Main entry point.
-   `src/model.py`: Core data model and logic.
-   `src/ui/`: UI components for different tabs.
-   `tests/`: Unit tests.

## Workflow

1.  **Setup**: Add Attributes (e.g., Cost, Performance) and Alternatives (e.g., Option A, Option B).
2.  **Scaling**: Define how raw scores map to value scores (0-1) for each attribute.
3.  **Weighting**: Assign importance to each attribute using swing weights.
4.  **Scoring**: Enter raw scores for each alternative.
5.  **Analysis/Comparison**: View rankings and compare alternatives to make a decision.
6.  **Sensitivity Analysis**: Visualize and understand the impact of attribute weights on the final outcome.
