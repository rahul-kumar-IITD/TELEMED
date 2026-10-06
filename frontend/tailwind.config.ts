import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f6f1e7",
        card: "#fffdf8",
        ink: "#14302f",
        ink2: "#41605d",
        line: "#d9cfba",
        teal: { DEFAULT: "#0f5c58", dark: "#0b4643" },
        clay: "#b4472b",
        gold: "#e7b53c",
        err: "#8f2a14",
        errbg: "#f9ddd4",
        okc: "#1f6b3a",
        okbg: "#dcefe0",
        infoc: "#1d4e7a",
        infobg: "#dbe8f5",
      },
      fontFamily: {
        display: ['"Iowan Old Style"', '"Palatino Linotype"', "Palatino", "Georgia", "serif"],
      },
    },
  },
} satisfies Config;
