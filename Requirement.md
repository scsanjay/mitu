# MITU — Manage Investment Terminal Utility

Build an application called **MITU (Manage Investment Terminal Utility)**.

## Core Requirements

- Use **uv** to manage the Python package and dependencies.
- Build the frontend with **Streamlit**.
- Allow the user to enter a **list of stock tickers**.
- When the user clicks **Analyze**, the system should begin processing and generate output.

## Analysis Logic

- Refer to the **`Research/`** folder for guidance on **how to analyze**.
- That folder contains scripts and instructions from multiple experts.
- Consolidate all of the guidance into one approach.
- If there are conflicts between sources, make the best judgment and choose the most appropriate method.

## Stock Classification

Each stock must be classified into one of these labels:

- **Hold**
- **Warning**
- **Sell**

## UI Requirements

- Show the **important details** for each stock in a **thin panel**.
- Display at least:
  - stock name
  - classification label
- Each stock should have a **dropdown** or **Show More** control that expands to reveal all details.
- Sort the stocks by **severity**.

## Data / API Requirements

- Minimize calls to **Yahoo Finance** as much as possible.
- If a stock is not found, **ignore it gracefully**.
- Show a **warning on the frontend** for any missing or invalid stock.
- Include proper **exception handling**.

## Goal

Create a clean, efficient, and user-friendly stock analysis app that follows the research guidance and presents results clearly.