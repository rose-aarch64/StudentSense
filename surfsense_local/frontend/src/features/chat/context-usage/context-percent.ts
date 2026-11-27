/** Whole percent of the budget spent, rounded down so 100 means it is reached
 * and the oldest messages are next to stop being sent. */
export function contextPercent(used: number, budget: number): number {
  return Math.min(100, Math.floor((used / budget) * 100))
}
