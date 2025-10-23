// src/lib/utils.js

/**
 * A simple utility to merge Tailwind + conditional classNames.
 * Example:
 * cn("p-4", condition && "bg-purple-500")
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}
