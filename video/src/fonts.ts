// Onest — жергілікті woff2 (fontsource), қазақ әріптері cyrillic + cyrillic-ext ішінде
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

const RANGES: Record<string, string> = {
  latin: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
  cyrillic: "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116",
  "cyrillic-ext": "U+0460-052F,U+1C80-1C8A,U+20B4,U+2DE0-2DFF,U+A640-A69F,U+FE2E-FE2F",
};
export const FONT = "Onest";
export const fontsReady = Promise.all(
  ["400", "500", "600", "700"].flatMap((w) =>
    Object.entries(RANGES).map(([sub, range]) =>
      loadFont({ family: FONT, url: staticFile(`fonts/onest-${sub}-${w}-normal.woff2`), weight: w, unicodeRange: range }),
    ),
  ),
);
