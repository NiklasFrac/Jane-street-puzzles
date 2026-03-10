# Jane Street Puzzle — Hooks 11 (Sep 2025)

This repo contains my solution setup and final state for Jane Street's **Hooks 11** puzzle ([September 2025](https://www.janestreet.com/puzzles/hooks-11-index/)).

I solved it with a small Python GUI that I wrote for editing the grid, marking cells, and saving/loading states.  
For the actual solving, I combined manual deductions with trial and error.


## What is in this repo?

- `hooks11_editor_gui.py` — the GUI/editor I used while solving
- `hooks11_solution_state.json` — the final solved state saved from the GUI
- `README.md` — short notes on the approach
- `final_grid.png` — screenshot of the solved grid

## How I approached it

1. Build a GUI so I could work with the grid faster than by hand.
2. Use the GUI to test ideas, mark progress, and save intermediate states.
3. Solve easy parts directly, then trial and error.
4. Check that the final state is consistent and record the result.

## Result

Final answer: **1620**
![Final Grid](final_grid.PNG)

## Note

Published after the official Jane Street solution was available.
Jane Street lists my submission among the correct solutions for Hooks 11.