# Jane Street Puzzle (February 2026) — Solution Notes

This folder contains my solution artifacts for the Jane Street monthly puzzle from [February 2026](https://www.janestreet.com/puzzles/subtiles-2-index/).

## Approach

The solution process had four main steps:

1. Find a parameter combination `(a, b, c)` such that every equation in the puzzle admits a positive integer solution.  
   A direct search procedure led to the valid parameter setting  
   `a = 1/4`, `b = -3`, `c = 1/2`.

2. Replace the original equation image with the corresponding evaluated version under this parameter choice.  
   ![Substituted values](jspuzzle_solved_final.png)

3. Build a small GUI to support interactive placement and consistency checking while solving the resulting puzzle instance.  
   ![Final coloured solution](jspuzzle_solved_colour.PNG)

4. Compute the row sums of the final configuration and take the product of the minimum and maximum values.

   Row sums:  
   `[56, 64, 135, 162, 93, 133, 115, 129, 138, 120, 139, 89, 123]`

   Final answer:  
   `56 * 162 = 9072`
